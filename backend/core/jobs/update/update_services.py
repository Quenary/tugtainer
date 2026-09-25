import logging
from collections.abc import Sequence
from typing import Final

from backend.core.agent_client import AgentClient
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.core.jobs.update.update_service import run_update_service_job
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.services.services_util import get_host_services


async def run_update_services_job(
    host: HostsModel,
    client: AgentClient,
    manual: bool = False,
    names: Sequence[str] | None = None,
    tracker: HostJobTracker | None = None,
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
            services = [
                s
                for s in services
                if services_db_map.get(s.name)
                and services_db_map[s.name].update_enabled
                and services_db_map[s.name].update_available
            ]

        tracker.set_status(EJobStatus.UPDATING)
        for s in services:
            await run_update_service_job(
                client,
                host,
                s,
                tracker=tracker,
            )

        return True
    except Exception:
        logger.exception("Failed to update swarm services")
        return False
