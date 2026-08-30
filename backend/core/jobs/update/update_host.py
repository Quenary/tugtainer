import logging
from collections.abc import Sequence
from typing import Final

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)

from backend.core.agent_client import AgentClient
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.core.jobs.update.update_job_executor import execute_update_job
from backend.core.jobs.update.update_job_plan_builder import build_update_job_plan
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import PruneImagesRequestBodySchema


async def run_update_host_job(
    host: HostsModel,
    client: AgentClient,
    manual: bool = False,
    names: Sequence[str] | None = None,
    tracker: HostJobTracker | None = None,
) -> bool:
    """
    Update containers of specified host.
    :param host: host info from db
    :param client: host's docker client
    :param manual: manual update includes all containers with available updates
    :param names: if set, only these containers are treated as manual_for
    :param tracker: unified per-host job tracker
    """
    tracker = tracker or HostJobTracker(host)
    logger: Final = logging.getLogger(f"run_update_host_job.{host.id}:{host.name}")

    try:
        logger.info("Starting update")

        try:
            docker_version = await client.common.version()
        except Exception:
            logger.exception("Failed to get docker version")
            docker_version = None

        containers: list[ContainerInspectResult] = await client.container.list(
            GetContainerListBodySchema(all=True)
        )
        if names is not None:
            name_set = set(names)
            manual_for = [c for c in containers if c.name in name_set]
        elif manual:
            manual_for = containers
        else:
            manual_for = []

        plan = await build_update_job_plan(host, containers, manual_for)

        tracker.set_status(EJobStatus.UPDATING)

        await execute_update_job(
            client, host, containers, plan, docker_version, tracker=tracker
        )

        if host.prune and names is None:
            tracker.set_status(EJobStatus.PRUNING)
            logger.info("Pruning images...")
            try:
                prune_result = await client.image.prune(
                    PruneImagesRequestBodySchema(all=host.prune_all)
                )
                tracker.set_prune_result(prune_result)
            except Exception:
                logger.exception("Failed to prune images")

        logger.info("Update completed")
        return True
    except Exception:
        logger.exception("Failed to update")
        return False
