import asyncio
import logging
from typing import Final

from sqlalchemy import select

from backend.core.jobs.jobs_coordinator import HostJobRuntime, host_job_coordinator
from backend.core.jobs.jobs_results import (
    job_to_notification_result,
    merge_notification_results,
)
from backend.core.jobs.jobs_schemas import Job
from backend.core.jobs.jobs_util import stale_swarm_error
from backend.core.notifications_core import send_job_notification
from backend.db.session import async_session_maker
from backend.exception import TugAgentClientError
from backend.modules.hosts.hosts_model import HostsModel


async def check_all_hosts(
    manual: bool = False,
) -> None:
    """
    Check all containers of all hosts
    :param manual: manual check includes all containers
    """
    logger: Final = logging.getLogger("check_all_hosts")

    try:
        logger.info("Start checking of all containers for all hosts")

        async with async_session_maker() as session:
            hosts: Final = (
                (await session.execute(select(HostsModel).where(HostsModel.enabled)))
                .scalars()
                .all()
            )

        finished: list[Job] = []

        async def collect_job(
            host: HostsModel,
            runtime: HostJobRuntime,
            failure: str,
            stale: str | None = None,
        ) -> None:
            try:
                await runtime.done.wait()
                if runtime.error:
                    raise runtime.error
                if runtime.job:
                    finished.append(runtime.job)
            except TugAgentClientError as e:
                if stale and stale_swarm_error(e):
                    logger.warning(stale, host.name)
                else:
                    logger.exception(failure)
            except Exception:
                logger.exception(failure)

        async def check_host(host: HostsModel) -> None:
            try:
                container_runtime = await host_job_coordinator.submit(
                    host,
                    "check",
                    names=None,
                    manual=manual,
                    wait=False,
                )
            except Exception:
                logger.exception(f"Failed to check host {host.name}")
                return
            service_runtime = None
            if host.is_swarm:
                try:
                    # Queue services before the container job finishes so the
                    # host stays busy across both phases.
                    service_runtime = await host_job_coordinator.submit(
                        host,
                        "check_services",
                        names=None,
                        manual=manual,
                        wait=False,
                    )
                except TugAgentClientError as e:
                    if stale_swarm_error(e):
                        logger.warning(
                            "Host %s is not a Swarm manager; skipping service check",
                            host.name,
                        )
                    else:
                        logger.exception(f"Failed to check services of {host.name}")
                except Exception:
                    logger.exception(f"Failed to check services of {host.name}")
            await collect_job(
                host,
                container_runtime,
                f"Failed to check host {host.name}",
            )
            if service_runtime is not None:
                await collect_job(
                    host,
                    service_runtime,
                    f"Failed to check services of {host.name}",
                    "Host %s is not a Swarm manager; skipping service check",
                )

        _ = await asyncio.gather(*(check_host(host) for host in hosts))
        try:
            await send_job_notification(
                merge_notification_results(
                    [job_to_notification_result(job) for job in finished]
                )
            )
        except Exception:
            logger.exception("Failed to send notification")

    except Exception:
        logger.exception("Error while checking all containers for all hosts")
