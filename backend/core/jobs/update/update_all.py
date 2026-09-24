import asyncio
import logging
from typing import Final

from sqlalchemy import select

from backend.core.jobs.jobs_coordinator import host_job_coordinator
from backend.core.jobs.jobs_results import job_to_notification_result
from backend.core.jobs.jobs_schemas import Job
from backend.core.notifications_core import send_job_notification
from backend.db.session import async_session_maker
from backend.modules.hosts.hosts_model import HostsModel


async def update_all_hosts(
    manual: bool = False,
) -> None:
    """
    Main func for scheduled/manual update of all containers
    for all specified docker hosts.
    :param manual: manual update includes all containers with available updates
    """
    logger: Final = logging.getLogger("update_all_hosts")

    try:
        logger.info("Start updating of all containers for all hosts")

        async with async_session_maker() as session:
            hosts: Final = (
                (await session.execute(select(HostsModel).where(HostsModel.enabled)))
                .scalars()
                .all()
            )

        finished: dict[int, Job] = {}

        async def update_host(host: HostsModel) -> None:
            try:
                runtime = await host_job_coordinator.submit(
                    host,
                    "update",
                    names=None,
                    manual=manual,
                    wait=True,
                )
                if runtime.job:
                    finished[host.id] = runtime.job
            except Exception:
                logger.exception(f"Failed to update containers of {host.name}")

        _ = await asyncio.gather(*(update_host(host) for host in hosts))

        try:
            await send_job_notification(
                [job_to_notification_result(job) for job in finished.values()]
            )
        except Exception:
            logger.exception("Failed to send notification after update")

    except Exception:
        logger.exception("Error while updating of all containers for all hosts")
