import logging
from typing import Final

from sqlalchemy import select

from backend.core.jobs.jobs_cache import JobStateCache
from backend.core.jobs.jobs_coordinator import host_job_coordinator
from backend.core.jobs.jobs_results import job_to_notification_result
from backend.core.jobs.jobs_schemas import AllHostsState, Job
from backend.core.jobs.jobs_util import ALL_HOSTS_CACHE_KEY, is_allowed_start
from backend.core.notifications_core import send_job_notification
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel


async def update_all_hosts():
    """
    Main func for scheduled/manual update of all containers
    marked for it, for all specified docker hosts.
    Should not raises errors, only logging.
    """
    logger: Final = logging.getLogger("update_all_hosts")
    cache: Final = JobStateCache[AllHostsState](ALL_HOSTS_CACHE_KEY)
    state: Final = cache.get()

    if not is_allowed_start(state):
        logger.warning("Update process is already running.")
        return

    try:
        cache.set({"status": EJobStatus.PREPARING})
        logger.info("Start updating of all containers for all hosts")

        async with async_session_maker() as session:
            hosts: Final = (
                (
                    await session.execute(
                        select(HostsModel).where(HostsModel.enabled)
                    )
                )
                .scalars()
                .all()
            )

        cache.update({"status": EJobStatus.UPDATING})
        finished: dict[int, Job] = {}
        for host in hosts:
            try:
                runtime = await host_job_coordinator.submit(
                    host,
                    "update",
                    names=None,
                    manual=False,
                    wait=True,
                )
                if runtime.job:
                    finished[host.id] = runtime.job
            except Exception:
                logger.exception(f"Failed to update containers of {host.name}")

        cache.update({"status": EJobStatus.DONE, "hosts": finished})
        try:
            await send_job_notification(
                [job_to_notification_result(job) for job in finished.values()]
            )
        except Exception:
            logger.exception("Failed to send notification after update")

    except Exception:
        cache.update({"status": EJobStatus.ERROR})
        logger.exception("Error while updating of all containers for all hosts")
