import logging
from typing import Final, cast
from .check_one_container import check_one_container
from .check_actions_util import (
    filter_containers_by_check_enabled,
    sort_containers_by_checked_at,
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


async def check_host_containers(
    host: HostsModel,
    client: AgentClient,
    manual: bool = False,
) -> HostActionResult | None:
    """
    Check all host's containers.
    :param host: host info
    :param client: host agent client
    :param manual: manual check includes all containers
    """
    result: Final = HostActionResult(
        host_id=host.id, host_name=host.name
    )
    cache_key: Final = get_host_cache_key(host)
    cache: Final = ProgressCache[HostActionProgress](cache_key)
    state: Final = cache.get()
    logger: Final = logging.getLogger(
        f"check_host_containers.{host.id}.{host.name}"
    )

    if not is_allowed_start_cache(state):
        logger.warning("Check action is already running. Exiting.")
        return None

    try:
        logger.info("Starting check action")
        cache.set({"status": EActionStatus.PREPARING})
        containers = await client.container.list(
            GetContainerListBodySchema(all=True)
        )
        async with async_session_maker() as session:
            containers_db: Final = await get_host_containers(
                session,
                host.id,
            )
            containers_db_map: Final = {
                item.name: item for item in containers_db
            }

        containers = filter_containers_by_check_enabled(
            containers, containers_db_map, manual
        )
        containers = sort_containers_by_checked_at(
            containers, containers_db_map
        )

        cache.update(
            {"status": EActionStatus.CHECKING},
        )
        for c in containers:
            res = await check_one_container(
                client,
                host,
                c,
            )
            result.items.append(res)

        cache.update({"status": EActionStatus.DONE, "result": result})
        return result
    except:
        logger.exception("Failed to check host")
        cache.update(
            {"status": EActionStatus.ERROR},
        )
        return result
