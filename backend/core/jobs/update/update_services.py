import logging
from collections.abc import Sequence
from typing import Final

from backend.core.agent_client import AgentClient
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.core.jobs.jobs_util import stale_swarm_error
from backend.core.jobs.update.update_service import run_update_service_job
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.exception import TugAgentClientError
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.services.services_model import SwarmServicesModel
from backend.modules.services.services_util import get_host_services
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.now import now


def _delay_elapsed(row: SwarmServicesModel, global_delay: int) -> bool:
    changed_at = row.remote_digests_changed_at
    if global_delay <= 0 or changed_at is None:
        return True
    return (now() - changed_at).total_seconds() >= global_delay


async def run_update_services_job(
    host: HostsModel,
    client: AgentClient,
    manual: bool = False,
    names: Sequence[str] | None = None,
    tracker: HostJobTracker | None = None,
    require_available: bool = False,
) -> bool:
    tracker = tracker or HostJobTracker(host)
    logger: Final = logging.getLogger(f"run_update_services_job.{host.id}.{host.name}")

    try:
        logger.info("Starting update swarm services job")
        services = await client.service.list()
        async with async_session_maker() as session:
            services_db = await get_host_services(session, host.id)
            services_db_map = {item.name: item for item in services_db}

        if names is not None:
            name_set = set(names)
            services = [s for s in services if s.name in name_set]
        elif not manual:
            global_delay = SettingsStorage.get(ESettingKey.DELAY_UPDATE_FOR)
            services = [
                s
                for s in services
                if (row := services_db_map.get(s.name))
                and row.update_enabled
                and row.update_available
                and _delay_elapsed(row, global_delay)
            ]
        elif require_available:
            services = [
                s
                for s in services
                if (row := services_db_map.get(s.name)) and row.update_available
            ]

        if not services:
            return True

        tracker.set_status(EJobStatus.UPDATING)
        for s in services:
            await run_update_service_job(
                client,
                host,
                s,
                tracker=tracker,
            )

        return True
    except TugAgentClientError as e:
        if stale_swarm_error(e):
            logger.warning(
                "Host %s is not a Swarm manager; skipping service update",
                host.name,
            )
            return True
        logger.exception("Failed to update swarm services")
        return False
    except Exception:
        logger.exception("Failed to update swarm services")
        return False
