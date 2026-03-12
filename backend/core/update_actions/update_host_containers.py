from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
import logging
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
from backend.core.container_group.container_group import (
    get_containers_groups,
)
from backend.core.agent_client import AgentClient
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import PruneImagesRequestBodySchema
from .update_group_containers import update_group_containers


async def update_host_containers(
    host: HostsModel,
    client: AgentClient,
) -> HostActionResult | None:
    """
    Update containers of specified host.
    :param host: host info from db
    :param client: host's docker client
    """
    result = HostActionResult(host_id=host.id, host_name=host.name)
    STATUS_KEY = get_host_cache_key(host)
    CACHE = ProgressCache[HostActionProgress](STATUS_KEY)
    try:
        STATE = CACHE.get()
        if not is_allowed_start_cache(STATE):
            logging.warning(
                f"Update process for {STATUS_KEY} is already running."
            )
            return None

        CACHE.set(
            {"status": EActionStatus.PREPARING},
        )
        logging.info(f"Starting update for host '{host.name}'")

        containers: list[ContainerInspectResult] = (
            await client.container.list(
                GetContainerListBodySchema(all=True)
            )
        )
        async with async_session_maker() as session:
            containers_db = await get_host_containers(
                session,
                host.id,
            )
        groups = get_containers_groups(containers, containers_db)
        CACHE.update(
            {"status": EActionStatus.UPDATING},
        )

        for group in groups.values():
            res = await update_group_containers(client, host, group)
            if res:
                result.items.extend(res.items)

        if host.prune:
            CACHE.update({"status": EActionStatus.PRUNING})
            logging.info(f"Pruning images on host '{host.name}'")
            try:
                result.prune_result = await client.image.prune(
                    PruneImagesRequestBodySchema(all=host.prune_all)
                )
            except Exception as e:
                logging.exception(e)
                logging.error(
                    f"Failed to prune images on host '{host.name}'"
                )

        CACHE.update({"status": EActionStatus.DONE, "result": result})
        return result
    except Exception as e:
        CACHE.update(
            {"status": EActionStatus.ERROR},
        )
        logging.exception(e)
        logging.error(f"Failed to update host {host.name}")
        return None
