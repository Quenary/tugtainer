import asyncio
import logging
import os
import posixpath
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from packaging import version
from python_on_whales.components.container.models import (
    ContainerInspectResult,
    Mount,
)
from sqlalchemy import select
from sqlalchemy.engine import make_url

from backend.config import Config
from backend.const import DATA_DIR, SELF_UPDATE_DIR, TUGTAINER_PROTECTED_LABEL
from backend.core.agent_client import AgentClient, AgentClientManager
from backend.core.container_util.container_config import (
    diff_container_config_with_image,
    get_container_config,
)
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.jobs.update.update_util import get_container_healthcheck_timeout
from backend.core.notifications_core import send_notification
from backend.db.session import async_session_maker
from backend.exception import TugSelfUpdateError
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.get_self_container_id import get_self_container_id
from backend.util.get_version_from_labels import get_version_from_labels
from shared.schemas.container_schemas import CreateContainerRequestBodySchema
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PullImageRequestBodySchema,
)
from shared.self_update.self_update_files import (
    read_state,
    write_private_file,
    write_state,
)
from shared.self_update.self_update_schemas import (
    SELF_UPDATE_HELPER_SUFFIX,
    SELF_UPDATE_OLD_SUFFIX,
    SELF_UPDATE_PLAN_FILE,
    SELF_UPDATE_PLAN_VERSION,
    SELF_UPDATE_STATE_FILE,
    ESelfUpdateStatus,
    SelfUpdatePlan,
    SelfUpdateState,
)
from shared.util.get_docker_client_api_version import get_docker_client_api_version

logger: Final = logging.getLogger("self_update")

DOCKER_SOCKET_PATHS: Final = frozenset({"/var/run/docker.sock", "/run/docker.sock"})
# Upper bound of waiting for the helper result.
# The helper waits for our healthcheck, which can be long.
RESULT_WAIT_TIMEOUT: Final = 3600
RESULT_POLL_INTERVAL: Final = 5


class SelfUpdateStorage:
    """In-memory part of the self-update state."""

    start_lock: Final = asyncio.Lock()
    # Result of the last self-update, kept after the state file was deleted
    last_result: SelfUpdateState | None = None
    # Strong reference to the background result watcher
    watch_task: asyncio.Task | None = None


def get_work_dir() -> Path:
    return Path(SELF_UPDATE_DIR)


def get_state_path() -> Path:
    return get_work_dir() / SELF_UPDATE_STATE_FILE


def read_app_version() -> str | None:
    try:
        with open("/app/version") as file:
            return file.readline().strip() or None
    except FileNotFoundError:
        return None


def get_current_state() -> SelfUpdateState | None:
    """State of a running self-update, or the last result."""
    try:
        state = read_state(get_state_path())
    except Exception:
        logger.exception("Failed to read self-update state")
        state = None
    return state or SelfUpdateStorage.last_result


async def find_self() -> tuple[HostsModel, AgentClient, ContainerInspectResult]:
    """
    Find the container of this app on one of the enabled hosts.
    :raises TugSelfUpdateError: if it is not found
    """
    self_id: Final = get_self_container_id()
    if not self_id:
        raise TugSelfUpdateError("Cannot detect the container of this app")
    async with async_session_maker() as session:
        result = await session.execute(select(HostsModel).where(HostsModel.enabled))
        hosts = result.scalars().all()
    for host in hosts:
        client = AgentClientManager.get_host_client(host)
        try:
            if not await client.container.exists(self_id):
                continue
            container = await client.container.inspect(self_id)
        except Exception:
            logger.warning(f"Failed to look up this app on host {host.name}")
            continue
        if container.id == self_id:
            return host, client, container
    raise TugSelfUpdateError(
        f"Container {self_id[:12]} of this app was not found on any enabled host"
    )


def get_data_mount(container: ContainerInspectResult) -> Mount:
    for mount in container.mounts or []:
        if mount.destination and posixpath.normpath(mount.destination) == DATA_DIR:
            return mount
    raise TugSelfUpdateError(
        f"{DATA_DIR} is not a volume or bind mount, the data would be lost"
    )


def get_sqlite_db_path() -> str | None:
    """
    Path of the SQLite database to snapshot, None for other databases.
    :raises TugSelfUpdateError: if it is outside the data volume
    """
    url = make_url(Config.DB_URL)
    if url.get_backend_name() != "sqlite":
        return None
    db_path = posixpath.normpath(url.database or "")
    if not db_path.startswith(f"{DATA_DIR}/"):
        raise TugSelfUpdateError(
            f"SQLite database {db_path} is outside of {DATA_DIR}, cannot snapshot it"
        )
    return db_path


def get_helper_networks(
    container: ContainerInspectResult,
    docker_version: DockerVersionScheme | None,
) -> list[str]:
    """
    Networks of the helper, so it reaches the same docker host (e.g. socket-proxy).
    Without addresses and aliases of the app.
    """
    host_config = container.host_config
    mode = host_config.network_mode if host_config else None
    if mode and (mode in ["host", "none"] or mode.startswith("container:")):
        return [mode]
    settings = container.network_settings
    networks = list(settings.networks.keys()) if settings and settings.networks else []
    if mode in networks:
        networks.remove(mode)
        networks.insert(0, mode)
    api_version = get_docker_client_api_version(docker_version)
    # Multiple --network flags need API 1.44
    if api_version and api_version < version.parse("1.44"):
        return networks[:1]
    return networks


def get_helper_config(
    container: ContainerInspectResult,
    data_mount: Mount,
    image_id: str,
    helper_name: str,
    plan_path: str,
    docker_version: DockerVersionScheme | None,
) -> CreateContainerRequestBodySchema:
    """
    One-shot helper from the new image.
    Gets only the docker access and the data volume.
    """
    volumes: list[tuple[str, str]] = [
        (str(data_mount.name or data_mount.source), DATA_DIR)
    ]
    docker_host: Final = os.environ.get("DOCKER_HOST")
    socket_paths = set(DOCKER_SOCKET_PATHS)
    if docker_host and docker_host.startswith("unix://"):
        socket_paths.add(docker_host.removeprefix("unix://"))
    for mount in container.mounts or []:
        if mount.source and mount.destination in socket_paths:
            volumes.append((mount.source, mount.destination))
    networks: Final = get_helper_networks(container, docker_version)

    return CreateContainerRequestBodySchema.model_validate(
        {
            "image": image_id,
            "name": helper_name,
            "entrypoint": "python",
            "command": ["-m", "shared.self_update", plan_path],
            "workdir": "/app",
            "volumes": volumes,
            **({"envs": {"DOCKER_HOST": docker_host}} if docker_host else {}),
            **({"networks": networks} if networks else {}),
            # The scheduled update must never touch the helper
            "labels": {TUGTAINER_PROTECTED_LABEL: "true"},
            # The image healthcheck probes the app, which the helper is not
            "healthcheck": False,
            "remove": True,
        }
    )


async def cleanup_stale_old_container(client: AgentClient, name: str) -> None:
    """
    Remove <name>-old left after a successful self-update,
    only if its id is recorded in the state journal.
    """
    state = get_current_state()
    old_name = f"{name}{SELF_UPDATE_OLD_SUFFIX}"
    if not state or state.status != ESelfUpdateStatus.SUCCEEDED:
        return
    if state.container_name != name or not await client.container.exists(old_name):
        return
    old = await client.container.inspect(old_name)
    if old.id != state.old_container_id:
        logger.warning(f"{old_name} is not recorded in the self-update state")
        return
    logger.info(f"Removing {old_name} left after self-update")
    await client.container.remove(old_name)


async def start_self_update() -> SelfUpdateState:
    """
    Pull the new image, write the plan and launch the helper.
    :raises TugSelfUpdateError: if the self-update cannot be started
    """
    if not Config.ALLOW_SELF_UPDATE:
        raise TugSelfUpdateError("Self-update is disabled, set ALLOW_SELF_UPDATE=true")
    if SelfUpdateStorage.start_lock.locked():
        raise TugSelfUpdateError("Self-update is already starting")
    async with SelfUpdateStorage.start_lock:
        current = read_state(get_state_path())
        if current and not current.is_final:
            raise TugSelfUpdateError("Self-update is already in progress")

        host, client, container = await find_self()
        name: Final = str(container.name)
        old_name: Final = f"{name}{SELF_UPDATE_OLD_SUFFIX}"
        helper_name: Final = f"{name}{SELF_UPDATE_HELPER_SUFFIX}"

        await cleanup_stale_old_container(client, name)
        for other in (old_name, helper_name):
            if await client.container.exists(other):
                raise TugSelfUpdateError(
                    f"Container {other} already exists, remove it first"
                )

        data_mount: Final = get_data_mount(container)
        db_path: Final = get_sqlite_db_path()
        image_spec: Final = get_container_image_spec(container)
        if not image_spec or not container.image:
            raise TugSelfUpdateError("Cannot get the image of this app")

        logger.info(f"Pulling {image_spec}")
        local_image = await client.image.inspect(
            InspectImageRequestBodySchema(spec_or_id=container.image)
        )
        remote_image = await client.image.pull(
            PullImageRequestBodySchema(image=image_spec)
        )
        if not remote_image.id or remote_image.id == container.image:
            raise TugSelfUpdateError(f"No newer image for {image_spec}")

        docker_version = await client.common.version()
        config, commands = get_container_config(container, local_image, docker_version)
        config = diff_container_config_with_image(config, remote_image)

        async with async_session_maker() as session:
            result = await session.execute(
                select(ContainersModel).where(
                    ContainersModel.host_id == host.id,
                    ContainersModel.name == name,
                )
            )
            db_container = result.scalars().first()

        old_version: Final = read_app_version()
        new_version: Final = get_version_from_labels(
            remote_image.config.labels if remote_image.config else None
        )
        plan = SelfUpdatePlan(
            version=SELF_UPDATE_PLAN_VERSION,
            container_id=str(container.id),
            container_name=name,
            old_image_id=container.image,
            new_image_id=remote_image.id,
            old_version=old_version,
            new_version=new_version,
            create=config,
            commands=commands,
            healthcheck_timeout=get_container_healthcheck_timeout(host, db_container),
            db_path=db_path,
        )
        state = SelfUpdateState(
            status=ESelfUpdateStatus.PENDING,
            container_name=name,
            old_container_id=str(container.id),
            helper_container_name=helper_name,
            old_image_id=container.image,
            new_image_id=remote_image.id,
            old_version=old_version,
            new_version=new_version,
        )
        plan_path: Final = get_work_dir() / SELF_UPDATE_PLAN_FILE
        write_private_file(plan_path, plan.model_dump_json(exclude_unset=True))
        write_state(get_state_path(), state)
        SelfUpdateStorage.last_result = None

        try:
            logger.info(f"Starting self-update helper {helper_name}")
            await client.container.create(
                get_helper_config(
                    container,
                    data_mount,
                    remote_image.id,
                    helper_name,
                    str(plan_path),
                    docker_version,
                )
            )
            await client.container.start(helper_name)
        except Exception:
            logger.exception("Failed to start self-update helper")
            plan_path.unlink(missing_ok=True)
            get_state_path().unlink(missing_ok=True)
            if await client.container.exists(helper_name):
                await client.container.remove(helper_name)
            raise
        start_self_update_watcher()
        return state


def _format_result(state: SelfUpdateState) -> tuple[str, str]:
    """Notification title and body."""
    old = state.old_version or state.old_image_id[:19]
    new = state.new_version or state.new_image_id[:19]
    titles: Final = {
        ESelfUpdateStatus.SUCCEEDED: "Tugtainer updated",
        ESelfUpdateStatus.ABORTED: "Tugtainer self-update aborted",
        ESelfUpdateStatus.ROLLED_BACK: "Tugtainer self-update rolled back",
        ESelfUpdateStatus.FAILED: "Tugtainer self-update failed",
        ESelfUpdateStatus.INTERRUPTED: "Tugtainer self-update interrupted",
    }
    title = titles.get(state.status, "Tugtainer self-update")
    lines = [f"{state.container_name}: {old} -> {new}"]
    if state.error:
        lines.append(f"Error: {state.error}")
    lines += [f"Warning: {w}" for w in state.warnings]
    if state.status in (ESelfUpdateStatus.FAILED, ESelfUpdateStatus.INTERRUPTED):
        lines.append(
            "Check the containers and the state journal, manual action may be required."
        )
    return title, "\n".join(lines)


async def _report_result(state: SelfUpdateState) -> None:
    title, body = _format_result(state)
    logger.info(f"{title}\n{body}")
    urls = SettingsStorage.get(ESettingKey.NOTIFICATION_URLS)
    _urls = [line.strip() for line in (urls or "").splitlines() if line.strip()]
    try:
        await send_notification(title, body, _urls)
    except Exception:
        logger.exception("Failed to send self-update notification")


async def _is_helper_running(state: SelfUpdateState) -> bool:
    try:
        _, client, _ = await find_self()
        return await client.container.exists(state.helper_container_name)
    except Exception:
        logger.exception("Failed to check the self-update helper")
        # Assume it is still running, the wait is bounded anyway
        return True


async def watch_self_update_result() -> None:
    """
    Report the result of a self-update once, after the app started.
    The helper may still be waiting for our healthcheck, so wait
    until it writes a final status, or mark it interrupted when it is gone.
    """
    state_path: Final = get_state_path()
    deadline: float | None = None
    while True:
        state = read_state(state_path)
        if not state:
            return
        if not state.is_final and not await _is_helper_running(state):
            # Re-read: the helper may have finished in the meantime
            state = read_state(state_path)
            if state and not state.is_final:
                state.status = ESelfUpdateStatus.INTERRUPTED
                state.error = state.error or "Self-update helper exited unexpectedly"
                state.finished_at = datetime.now(UTC)
                write_state(state_path, state)
        if not state:
            return
        if state.is_final:
            break
        if deadline is None:
            deadline = asyncio.get_running_loop().time() + RESULT_WAIT_TIMEOUT
            logger.info("Self-update is in progress, waiting for the result")
        elif asyncio.get_running_loop().time() > deadline:
            logger.warning("Self-update result not available yet, giving up")
            return
        await asyncio.sleep(RESULT_POLL_INTERVAL)

    SelfUpdateStorage.last_result = state
    await _report_result(state)
    state_path.unlink(missing_ok=True)
    if state.status == ESelfUpdateStatus.SUCCEEDED:
        try:
            _, client, _ = await find_self()
            await cleanup_stale_old_container(client, state.container_name)
        except Exception:
            logger.exception("Failed to clean up after self-update")


def start_self_update_watcher() -> None:
    """
    Run the result watcher in the background, not to block the startup.
    Started on startup (new or rolled back container), and after launching
    the helper (the result of an abort is reported by the running app).
    """
    task = SelfUpdateStorage.watch_task
    if task and not task.done():
        return
    SelfUpdateStorage.watch_task = asyncio.create_task(_watch_logged())


async def _watch_logged() -> None:
    try:
        await watch_self_update_result()
    except Exception:
        logger.exception("Failed to report the self-update result")
