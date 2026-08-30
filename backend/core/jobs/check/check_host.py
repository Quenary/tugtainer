import logging
from collections.abc import Sequence
from typing import Final

from backend.core.agent_client import AgentClient
from backend.core.jobs.check.check_container import run_check_container_job
from backend.core.jobs.check.check_util import (
    filter_containers_by_check_enabled,
    sort_containers_by_checked_at,
)
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.containers.containers_util import (
    get_host_containers,
)
from backend.modules.hosts.hosts_model import HostsModel
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)


async def run_check_host_job(
    host: HostsModel,
    client: AgentClient,
    manual: bool = False,
    names: Sequence[str] | None = None,
    tracker: HostJobTracker | None = None,
) -> bool:
    """
    Check host containers.
    :param host: host info
    :param client: host agent client
    :param manual: manual check includes all containers (when names is not set)
    :param names: if set, only these containers are checked (manual selection)
    :param tracker: unified per-host job tracker
    """
    tracker = tracker or HostJobTracker(host)
    logger: Final = logging.getLogger(f"run_check_host_job.{host.id}.{host.name}")

    try:
        logger.info("Starting check job")
        containers = await client.container.list(GetContainerListBodySchema(all=True))
        async with async_session_maker() as session:
            containers_db: Final = await get_host_containers(
                session,
                host.id,
            )
            containers_db_map: Final = {item.name: item for item in containers_db}

        if names is not None:
            name_set = set(names)
            containers = [c for c in containers if c.name in name_set]
        elif not manual:
            containers = filter_containers_by_check_enabled(
                containers, containers_db_map
            )
        containers = sort_containers_by_checked_at(containers, containers_db_map)

        tracker.set_status(EJobStatus.CHECKING)
        for c in containers:
            await run_check_container_job(
                client,
                host,
                c,
                tracker=tracker,
            )

        return True
    except Exception:
        logger.exception("Failed to check host")
        return True
