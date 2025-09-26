from _asyncio import Future
from datetime import datetime
from docker.models.containers import Container
from docker.models.images import Image
from docker.models.containers import Container
from docker.models.containers import Container
import logging
from docker.models.containers import Container
from typing import Any, Callable, NotRequired, TypedDict
from docker.models.containers import Container
from docker.models.images import Image
from docker.models.containers import Container
from docker import client
from sqlalchemy import and_, select
import time
import asyncio
import concurrent.futures
from cachetools import TTLCache
from app.db import (
    ContainersModel,
    async_session_maker,
    insert_or_update_container,
)
from app.core.registries import (
    choose_registry_client,
    BaseRegistryClient,
)
from app.core.notifications_core import send_notification
from app.enums.check_status_enum import ECheckStatus
from app.helpers import is_self_container, now
import traceback


_client = client.from_env()
ROLLBACK_TIMEOUT = 61

STATUS_CACHE = TTLCache(maxsize=10, ttl=600)
ALL_CONTAINERS_STATUS_KEY = "check_and_update_all_containers"


class CheckStatusDict(TypedDict):
    status: NotRequired[ECheckStatus]  # status code
    available: NotRequired[
        int
    ]  # Count of not updated containers (check only)
    updated: NotRequired[int]  # count of updated containers
    rolledback: NotRequired[int]  # count of rolled-back after fail
    failed: NotRequired[int]  # count of failed updates


def _set_check_status(key: str, value: CheckStatusDict):
    STATUS_CACHE[key] = value


def _update_check_status(key: str, value: CheckStatusDict):
    current = STATUS_CACHE.get(key) or {}
    STATUS_CACHE[key] = {
        **current,
        **value,
    }


def get_check_status(key: str) -> CheckStatusDict | None:
    return STATUS_CACHE.get(key)


def get_local_digest(image: Image) -> str | None:
    repo_digests = image.attrs.get("RepoDigests", [])
    if repo_digests:
        return repo_digests[0].split("@")[1]
    return None


async def db_update_container(name: str, data: dict):
    """
    Helper for updating container data in db
    """
    async with async_session_maker() as session:
        await insert_or_update_container(session, name, data)


async def filter_containers_for_check(
    containers: list[Container],
) -> list[Container]:
    """Filter containers marked for check only"""
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == False,
            )
        )
        result = await session.execute(stmt)
        names = result.scalars().all()
        return [c for c in containers if c.name in names]


async def filter_containers_for_update(
    containers: list[Container],
) -> list[Container]:
    """Filter containers marked for check and auto update"""
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == True,
            )
        )
        result = await session.execute(stmt)
        names = result.scalars().all()
        return [c for c in containers if c.name in names]


def get_service_name(container: Container) -> str:
    """Extract service name from labels"""
    labels = container.labels or {}
    return labels.get("com.docker.compose.service", container.name)


def get_dependencies(container: Container) -> list[str]:
    """Get list of dependencies (container names)"""
    labels: dict[str, str] = container.labels or {}

    # E.g. "service1:condition:value,service2:condition:value"
    depends_on_label: str = labels.get(
        "com.docker.compose.depends_on", ""
    )

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.split(":")
        if parts:  # Берем только имя сервиса (первую часть)
            dependencies.append(parts[0])

    return dependencies


def _sort_containers_by_dependencies(
    containers: list[Container],
) -> list[Container]:
    """
    Sort containers so that those on which others depend come first.
    Use the com.docker.compose.depends_on label, if present.
    """
    # Создаем словарь зависимостей: сервис -> список зависимостей
    container_map: dict[str, Container] = {}
    dependencies: dict[str, list[str]] = {}

    for container in containers:
        service_name = get_service_name(container)
        container_map[service_name] = container
        dependencies[service_name] = get_dependencies(container)

    visited: set[str] = set()
    result: list[Container] = []

    def visit(service) -> None:
        if service in visited:
            return
        visited.add(service)

        # Check all dependencies first
        for dep in dependencies[service]:
            if dep in container_map:
                visit(dep)

        # Then add current service
        if service in container_map:
            result.append(container_map[service])

    for service in container_map:
        visit(service)

    return result


def _get_container_image(c: Container) -> str:
    return c.attrs.get("Config", {}).get("Image", "")


def get_container_config(
    container: Container,
) -> tuple[dict[str, Any], list[Any], bool]:
    """
    Get container config ready to be used for recreation.
    :returns 0: container config dict
    :returns 1: additional networks to connect after creation
    :returns 2: should the container be started after creation
    """
    attrs: dict[str, Any] = container.attrs
    config: dict[str, Any] = attrs["Config"]
    host_config: dict[str, Any] = attrs["HostConfig"]
    networking_config: dict[str, Any] = attrs.get(
        "NetworkSettings", {}
    )

    # Ports
    ports = {}
    if networking_config.get("Ports"):
        for container_port, bindings in networking_config[
            "Ports"
        ].items():
            if bindings:
                host_ports = [
                    int(b["HostPort"])
                    for b in bindings
                    if b.get("HostPort")
                ]
                if host_ports:
                    # There may be several different ports binded
                    # But also there may be two same ports (for imv4 and ipv6)
                    host_ports = list(set(host_ports))
                    ports[container_port] = (
                        host_ports
                        if len(host_ports) > 1
                        else host_ports[0]
                    )

    # Volumes
    volumes = {}
    for mount in attrs.get("Mounts", []):
        bind = {
            "bind": mount["Destination"],
            "mode": mount.get("Mode", "rw"),
        }
        if mount["Type"] == "volume":
            volumes[mount["Name"]] = bind
        elif mount["Type"] == "bind":
            volumes[mount["Source"]] = bind

    # Env
    environment = {}
    for env in config.get("Env", []):
        if "=" in env:
            k, v = env.split("=", 1)
            environment[k] = v

    # Networks
    networks = list(networking_config.get("Networks", {}).keys())
    network_mode = host_config.get("NetworkMode")
    network_mode = (
        network_mode
        if network_mode and network_mode != "default"
        else None
    )

    return (
        {
            "name": container.name,
            "detach": True,
            "environment": environment or None,
            "ports": ports or None,
            "volumes": volumes or None,
            "entrypoint": config.get("Entrypoint"),
            "command": config.get("Cmd"),
            "restart_policy": host_config.get("RestartPolicy"),
            "network": network_mode
            or (networks[0] if networks else None),
            "hostname": config.get("Hostname"),
            "domainname": config.get("Domainname"),
            "user": config.get("User"),
            "working_dir": config.get("WorkingDir"),
            "labels": config.get("Labels"),
            "privileged": host_config.get("Privileged", False),
            "cap_add": host_config.get("CapAdd"),
            "cap_drop": host_config.get("CapDrop"),
            "dns": host_config.get("Dns"),
            "extra_hosts": host_config.get("ExtraHosts"),
        },
        networks[1:],
        container.attrs.get("State", {}).get("Status", "")
        == "running",
    )


async def _wait_for_container_healthy(
    container: Container, timeout: int = ROLLBACK_TIMEOUT
) -> bool:
    """Wait for container healthy status or timeout"""
    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        health = container.health
        if health == "healthy":
            return True
        await asyncio.sleep(5)
    container.reload()
    health = container.health
    status = container.attrs.get("State", {}).get("Status", "")
    # On last attempt assume unknown is also healthy
    if status == "running" and health in ["healthy", "unknown"]:
        return True
    return False


def _connect_to_networks(
    container: Container, networks_to_connect: list[Any]
) -> None:
    """Connects container to several networks"""
    for net in networks_to_connect:
        logging.info(
            f"Connecting container {container.name} to several networks..."
        )
        try:
            _client.networks.get(net).connect(container)
        except Exception as e:
            logging.warning(
                f"Failed to connect container {container.name} to network {net}"
            )


async def _recreate_container(
    container: Container,
    new_image: str,
) -> tuple[Container, bool]:
    """
    Recreate container with new image.
    :returns 0: Container object (new or rolled-back)
    :returns 1: Updated flag (that is, not rolled-back)
    Could raise an exception if recreate and rallback fails.
    """

    old_image = container.attrs["Config"]["Image"]
    cfg, networks_to_connect, should_start = get_container_config(
        container
    )
    name = cfg["name"]

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=1
    ) as executor:
        try:
            logging.info(f"Stopping container {name}...")
            await loop.run_in_executor(executor, container.stop)

            logging.info(f"Removing container {name}...")
            await loop.run_in_executor(executor, container.remove)

            logging.info(f"Pulling new image {new_image}...")
            await loop.run_in_executor(
                executor, lambda: _client.images.pull(new_image)
            )

            logging.info(f"Creating new container {name}...")
            new_container = await loop.run_in_executor(
                executor,
                lambda: _client.containers.create(new_image, **cfg),
            )

            _connect_to_networks(new_container, networks_to_connect)

            if not should_start:
                logging.info(
                    f"Container {name} was not running before update, so leave it as is..."
                )
                return (new_container, True)

            logging.info(f"Starting new container {name}...")
            await loop.run_in_executor(executor, new_container.start)

            logging.info(f"Waiting for healthchecks of {name}")
            if await _wait_for_container_healthy(new_container):
                logging.info(
                    f"Container {name} is healthy. Update successful."
                )
                return (new_container, True)

            logging.warning(
                f"Container {name} failed healthcheck. Rolling back..."
            )
            await loop.run_in_executor(executor, container.stop)
            await loop.run_in_executor(executor, container.remove)
            raise RuntimeError("Healthcheck failed")
        except Exception as e:
            logging.warning(e)
            logging.warning(
                f"Rollback: recreating {name} with old image {old_image}"
            )
            await loop.run_in_executor(
                executor, lambda: _client.images.pull(old_image)
            )
            rolled_back = await loop.run_in_executor(
                executor,
                lambda: _client.containers.run(old_image, **cfg),
            )
            _connect_to_networks(rolled_back, networks_to_connect)
            logging.info(f"Rollback complete for {name}.")
            return (rolled_back, False)


async def _is_container_update_available(c: Container) -> bool:
    """
    Compare digests and define is there new image
    """
    image_spec = c.attrs["Config"]["Image"]
    registry: BaseRegistryClient = choose_registry_client(image_spec)
    local_image: Image = _client.images.get(image_spec)
    local_digest: str | None = get_local_digest(local_image)
    remote_digest: str | None = await registry.get_remote_digest()
    return bool(remote_digest and local_digest != remote_digest)


async def check_container(
    name: str, update: bool = False
) -> tuple[Container | None, bool, bool, Exception | None]:
    """
    Check and update one container.
    Should not raises errors, only logging.
    :param name: name or id
    :param update: wether to update container (only check if false)
    :returns 0: Container if there is new one (updated or rolled-back after fail)
    :returns 1: Available flag (new image, but not updated)
    :returns 2: Updated flag (that is, not rolled-back)
    :returns 3: Exception if there was any
    """
    status = get_check_status(name)
    allow_statuses = [ECheckStatus.DONE, ECheckStatus.ERROR]
    if status and status.get("status") not in allow_statuses:
        logging.warning(
            f"Check and update of container {name} is already running"
        )
        return (None, False, False, None)

    _set_check_status(name, {"status": ECheckStatus.PREPARING})

    container = _client.containers.get(name)
    if not container:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.warning(
            f"While checking for update, container '{name}' not found"
        )
        return (None, False, False, None)

    image = container.attrs["Config"]["Image"]
    _update_check_status(name, {"status": ECheckStatus.CHECKING})
    logging.info(
        f"Start checking for updates of container '{name}' with image '{image}'"
    )
    update_available: bool = await _is_container_update_available(
        container
    )
    await db_update_container(
        str(name),
        {
            "update_available": update_available,
            "checked_at": now(),
        },
    )

    if not update_available:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.info(
            f"No new image was found for the container '{name}'"
        )
        return (None, False, False, None)

    is_self = is_self_container(container)
    if is_self:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.warning(
            f"Update is available, but self container cannot be updated with that func"
        )
        return (None, True, False, None)

    if not update:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.info(f"Check of container '{name}' complete")
        return (None, True, False, None)

    _update_check_status(name, {"status": ECheckStatus.UPDATING})
    logging.info(f"New image '{image}' found for container '{name}'")

    try:
        container, updated = await _recreate_container(
            container,
            image,
        )
        if updated:
            await db_update_container(
                str(name),
                {
                    "update_available": False,
                    "updated_at": now(),
                },
            )
        _update_check_status(name, {"status": ECheckStatus.DONE})
        return (container, False, updated, None)
    except Exception as e:
        logging.error(f"Failed to update container {name}")
        _update_check_status(name, {"status": ECheckStatus.ERROR})
        return (None, True, False, e)


async def check_and_update_all_containers():
    """
    Main func for check and update containers.
    Should not raises errors, only logging.
    """
    status = get_check_status(ALL_CONTAINERS_STATUS_KEY)
    allow_statuses = [ECheckStatus.DONE, ECheckStatus.ERROR]
    if status and status.get("status") not in allow_statuses:
        logging.warning(
            "Check and update process is already running."
        )
        return

    _set_check_status(
        ALL_CONTAINERS_STATUS_KEY,
        {"status": ECheckStatus.PREPARING},
    )
    logging.info("Start checking for updates of all containers")
    containers: list[Container] = _client.containers.list(all=True)
    for_check = await filter_containers_for_check(containers)
    for_update = await filter_containers_for_update(containers)
    for_update = _sort_containers_by_dependencies(for_update)

    _update_check_status(
        ALL_CONTAINERS_STATUS_KEY,
        {"status": ECheckStatus.CHECKING},
    )

    available: list[Container] = []
    updated: list[Container] = []
    rolledback: list[Container] = []
    failed: list[Container] = []
    errors: list[Exception] = []

    for item in for_check:
        _cont, _available, _updated, _exp = await check_container(
            str(item.name), False
        )
        if _available:
            available.append(item)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    _update_check_status(
        ALL_CONTAINERS_STATUS_KEY,
        {
            "status": ECheckStatus.UPDATING,
            "available": len(available),
        },
    )

    for item in for_update:
        _cont, _available, _updated, _exp = await check_container(
            str(item.name), True
        )
        if _cont:
            if _updated:
                updated.append(_cont)
            else:
                rolledback.append(_cont)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    _update_check_status(
        ALL_CONTAINERS_STATUS_KEY,
        {
            "status": ECheckStatus.DONE,
            "updated": len(updated),
            "failed": len(failed),
            "rolledback": len(rolledback),
        },
    )

    # Notification
    try:
        title: str = f"Dockobserver {datetime.now()}"
        body: str = ""
        if updated:
            body += "Updated:\n"
            for c in updated:
                body += f"{c.name} {_get_container_image(c)}\n"
            body += "\n"
        if available:
            body += "Update available for:\n"
            for c in available:
                body += f"{c.name} {_get_container_image(c)}\n"
            body += "\n"
        if rolledback:
            body += "Rolled-back after fail:\n"
            for c in rolledback:
                body += f"{c.name} {_get_container_image(c)}\n"
        if failed:
            body += f"Failed and not rolled-back:\n"
            for c in failed:
                body += f"{c.name} {_get_container_image(c)}\n\n"
        if errors:
            body += f"Several errors occured:\n"
            for e in errors:
                tb_lines = traceback.format_exception(
                    type(e), e, e.__traceback__
                )
                last_lines = tb_lines[-3:]
                body += "".join(last_lines) + "\n"
        if body:
            await send_notification(title, body)
    except Exception as e:
        logging.error(f"Error while sending notification: {e}")
