from typing import Final
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
import logging
from backend.core.update_actions.update_actions_executor import (
    execute_update_plan,
)
from backend.core.update_actions.update_actions_plan import (
    build_update_plan,
)
from backend.db.session import async_session_maker
from backend.modules.hosts.hosts_model import HostsModel
from backend.core.action_result import (
    HostActionResult,
)
from backend.modules.containers.containers_util import (
    get_host_containers,
)
from backend.enums.action_status_enum import EActionStatus
from backend.core.progress.progress_schemas import (
    HostActionProgress,
)
from backend.core.progress.progress_util import (
    get_host_cache_key,
    is_allowed_start_cache,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.agent_client import AgentClient
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import PruneImagesRequestBodySchema


async def update_host_containers(
    host: HostsModel,
    client: AgentClient,
) -> HostActionResult | None:
    """
    Update containers of specified host.
    :param host: host info from db
    :param client: host's docker client
    """
    result: Final = HostActionResult(
        host_id=host.id, host_name=host.name
    )
    status_key: Final = get_host_cache_key(host)
    cache: Final = ProgressCache[HostActionProgress](status_key)
    state: Final = cache.get()
    logger: Final = logging.getLogger(
        f"update_host_containers.{host.id}:{host.name}"
    )

    if not is_allowed_start_cache(state):
        logger.warning(f"Update already running. Exiting.")
        return None

    try:
        cache.set(
            {"status": EActionStatus.PREPARING},
        )
        logger.info("Starting update")

        try:
            docker_version = await client.common.version()
        except Exception:
            logger.exception("Failed to get docker version")
            docker_version = None

        containers: list[ContainerInspectResult] = (
            await client.container.list(
                GetContainerListBodySchema(all=True)
            )
        )

        plan = await build_update_plan(host, containers)

        cache.update(
            {"status": EActionStatus.UPDATING},
        )

        plan_res = await execute_update_plan(
            client, host, containers, plan, docker_version
        )

        if plan_res:
            result.items.extend(plan_res.items)

        if host.prune:
            cache.update({"status": EActionStatus.PRUNING})
            logger.info("Pruning images...")
            try:
                result.prune_result = await client.image.prune(
                    PruneImagesRequestBodySchema(all=host.prune_all)
                )
            except Exception:
                logger.exception("Failed to prune images")

        cache.update({"status": EActionStatus.DONE, "result": result})
        logger.info("Update completed")
        return result
    except:
        logger.exception(f"Failed to update")
        cache.update(
            {"status": EActionStatus.ERROR},
        )
        return None
