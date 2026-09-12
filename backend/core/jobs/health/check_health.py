import asyncio
import logging
from collections.abc import Coroutine
from typing import Final, TypedDict, cast

from jinja2.sandbox import SandboxedEnvironment
from python_on_whales.components.container.models import ContainerInspectResult
from sqlalchemy import select

from backend.const import (
    DEFAULT_HEALTH_MONITOR_N_TO_NTFY,
    DEFAULT_HEALTH_MONITOR_N_TO_RESTART,
    DEFAULT_HEALTH_MONITOR_RESTART_ATTEMPTS,
)
from backend.core.agent_client import AgentClientManager
from backend.core.container_util.get_container_health_status_str import (
    get_container_health_status_str,
)
from backend.core.container_util.wait_for_container_healthy import (
    wait_for_container_healthy,
)
from backend.core.jobs.update.update_util import get_container_healthcheck_timeout
from backend.core.notifications_core import send_notification
from backend.db.session import async_session_maker
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.containers.containers_util import insert_or_update_container
from backend.modules.health.health_model import (
    ContainerHealthHistory,
    ContainerHealthState,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from shared.schemas.container_schemas import GetContainerListBodySchema

logger: Final = logging.getLogger("check_health")

_host_running_locks: set[int] = set()


class HealthMonitorNotificationBatchItem(TypedDict):
    container: ContainerInspectResult
    status: str


async def check_all_containers_health() -> None:
    """
    Check health of all containers, skipping hosts that are already running this check.
    """
    async with async_session_maker() as session:
        hosts: Final = (
            (await session.execute(select(HostsModel).where(HostsModel.enabled)))
            .scalars()
            .all()
        )

    tasks: list[Coroutine[object, object, None]] = []
    for host in hosts:
        if host.id in _host_running_locks:
            logger.info(
                f"Skipping health check for host {host.id} because it is already running"
            )
            continue
        tasks.append(_check_host_health(host.id))

    if tasks:
        _ = await asyncio.gather(*tasks)


async def _check_host_health(host_id: int) -> None:
    _host_running_locks.add(host_id)
    try:
        await _do_check_host_health(host_id)
    except Exception:
        logger.exception(f"Error checking health for host {host_id}")
    finally:
        _host_running_locks.discard(host_id)


async def _do_check_host_health(host_id: int) -> None:
    # Retrieve host
    async with async_session_maker() as session:
        host: Final = await session.get(HostsModel, host_id)
        if not host or not host.enabled:
            return

        # Load all DB containers for this host mapped by name
        db_containers: Final = (
            (
                await session.execute(
                    select(ContainersModel).where(ContainersModel.host_id == host_id)
                )
            )
            .scalars()
            .all()
        )
        db_container_map: Final = {c.name: c for c in db_containers}

    client: Final = AgentClientManager.get_host_client(host)
    try:
        # Get all containers from agent
        agent_containers: Final = await client.container.list(
            GetContainerListBodySchema(all=True)
        )
    except Exception:
        logger.exception(f"Failed to fetch containers from host {host_id}")
        return

    n_to_restart = int(
        SettingsStorage.get(ESettingKey.HEALTH_MONITOR_N_TO_RESTART)
        or DEFAULT_HEALTH_MONITOR_N_TO_RESTART
    )
    n_to_ntfy = int(
        SettingsStorage.get(ESettingKey.HEALTH_MONITOR_N_TO_NTFY)
        or DEFAULT_HEALTH_MONITOR_N_TO_NTFY
    )
    max_restarts = int(
        SettingsStorage.get(ESettingKey.HEALTH_MONITOR_RESTART_ATTEMPTS)
        or DEFAULT_HEALTH_MONITOR_RESTART_ATTEMPTS
    )

    notifications_batch: list[HealthMonitorNotificationBatchItem] = []

    for cont in agent_containers:
        # Skip containers that don't have healthcheck
        if not cont.state or not cont.state.health:
            logger.debug(f"Container {cont.name} has no healthcheck, skipping")
            continue

        # Get matching DB container
        db_c = db_container_map.get(cast(str, cont.name))
        if not db_c:
            async with async_session_maker() as session:
                db_c = await insert_or_update_container(
                    session=session,
                    host_id=host_id,
                    c_name=cont.name or "",
                    c_data={},
                )

        status = get_container_health_status_str(cont)

        async with async_session_maker() as session:
            # Fetch state
            state: ContainerHealthState | None = (
                await session.execute(
                    select(ContainerHealthState).where(
                        ContainerHealthState.container_id == db_c.id
                    )
                )
            ).scalar_one_or_none()
            if not state:
                state = ContainerHealthState(
                    host_id=host_id,
                    container_id=db_c.id,
                    consecutive_failures=0,
                    restart_attempts=0,
                    is_notified=False,
                )
                session.add(state)

            restarted = False
            notified = False

            if status == "healthy":
                if state.is_notified:
                    notifications_batch.append(
                        {
                            "container": cont,
                            "status": "healthy",
                        }
                    )
                    notified = True

                state.consecutive_failures = 0
                state.restart_attempts = 0
                state.is_notified = False
            elif status == "unhealthy":
                state.consecutive_failures += 1

                # Restart Logic
                if (
                    n_to_restart > 0
                    and state.consecutive_failures
                    >= (state.restart_attempts + 1) * n_to_restart
                    and state.restart_attempts < max_restarts
                ):
                    try:
                        logger.info(
                            f"Restarting unhealthy container {cont.name} on host {host_id}"
                        )
                        _ = await client.container.restart(cast(str, cont.id))

                        # Wait for it to become healthy
                        timeout = get_container_healthcheck_timeout(host, db_c)
                        _ = await wait_for_container_healthy(client, cont, timeout)

                        state.restart_attempts += 1
                        restarted = True
                    except Exception:
                        logger.exception(f"Failed to restart container {cont.name}")

                # Notification Logic
                if (
                    n_to_ntfy > 0
                    and state.consecutive_failures >= n_to_ntfy
                    and not state.is_notified
                ):
                    notifications_batch.append(
                        {
                            "container": cont,
                            "status": "unhealthy",
                        }
                    )
                    state.is_notified = True
                    notified = True

            # Save history
            history = ContainerHealthHistory(
                host_id=host_id,
                container_id=db_c.id,
                status=status,
                restarted=restarted,
                notified=notified,
            )
            session.add(history)

            await session.commit()

    if notifications_batch:
        await _send_health_notifications(host.name, notifications_batch)


async def _send_health_notifications(
    host_name: str, batch: list[HealthMonitorNotificationBatchItem]
) -> None:
    template_str = SettingsStorage.get(ESettingKey.HEALTH_MONITOR_NTFY_BODY_TMPL)
    if not template_str:
        return

    try:
        jinja2_env: Final = SandboxedEnvironment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )
        _template = jinja2_env.from_string(template_str)
        body: str = str(_template.render(groups={host_name: batch}))
        urls = SettingsStorage.get(ESettingKey.NOTIFICATION_URLS)
        if urls:
            urls_list = [
                line.strip() for line in str(urls).splitlines() if line.strip()
            ]
            if urls_list:
                await send_notification("Health Monitor Alert", body, urls=urls_list)
    except Exception:
        logger.exception("Failed to render and send health notification")
