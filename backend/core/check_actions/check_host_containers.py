import logging
from .check_one_container import check_one_container
from .check_actions_util import sort_containers_by_checked_at
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
) -> HostActionResult | None:
    """
    Check all host's containers.
    :param host: host info
    :param client: host agent client
    """
    logging.info(f"Starting check action for host: {host.name}")
    result = HostActionResult(host_id=host.id, host_name=host.name)
    CACHE_KEY = get_host_cache_key(host)
    CACHE = ProgressCache[HostActionProgress](CACHE_KEY)
    try:
        STATE = CACHE.get()
        if not is_allowed_start_cache(STATE):
            logging.warning(
                f"Check action for host: {host.name} is already running."
            )
            return None
        CACHE.set({"status": EActionStatus.PREPARING})
        containers = await client.container.list(
            GetContainerListBodySchema(all=True)
        )
        async with async_session_maker() as session:
            containers_db = await get_host_containers(
                session,
                host.id,
            )
        containers = sort_containers_by_checked_at(
            containers, containers_db
        )

        CACHE.update(
            {"status": EActionStatus.CHECKING},
        )
        for c in containers:
            res = await check_one_container(
                client,
                host,
                c,
            )
            result.items.append(res)

        CACHE.update({"status": EActionStatus.DONE, "result": result})
        return result
    except Exception as e:
        CACHE.update(
            {"status": EActionStatus.ERROR},
        )
        logging.exception(e)
        logging.error(f"Failed to check host {host.name}")
        return None
