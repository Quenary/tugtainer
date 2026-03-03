import logging
from sqlalchemy import select

from .check_host_containers import check_host_containers
from backend.core.notifications_core import send_check_notification
from backend.db.session import async_session_maker
from backend.modules.hosts.hosts_model import HostsModel
from backend.core.action_result import (
    HostActionResult,
)
from backend.enums.action_status_enum import EActionStatus
from backend.core.progress.progress_schemas import (
    AllActionProgress,
)
from backend.core.progress.progress_util import (
    ALL_CONTAINERS_STATUS_KEY,
    is_allowed_start_cache,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.agent_client import AgentClientManager


async def check_all_containers():
    """
    Check all containers of all hosts
    """
    CACHE = ProgressCache[AllActionProgress](
        ALL_CONTAINERS_STATUS_KEY
    )
    try:
        STATE = CACHE.get()
        if not is_allowed_start_cache(STATE):
            logging.warning(
                "General check process is already running."
            )
            return
        CACHE.set(
            {"status": EActionStatus.PREPARING},
        )
        logging.info("Start checking of all containers for all hosts")

        async with async_session_maker() as session:
            result = await session.execute(
                select(HostsModel).where(HostsModel.enabled == True)
            )
            hosts = result.scalars().all()

        CACHE.update(
            {"status": EActionStatus.CHECKING},
        )
        results: list[HostActionResult] = []
        for host in hosts:
            client = AgentClientManager.get_host_client(host)
            result = await check_host_containers(host, client)
            if result:
                results += [result]

        CACHE.update(
            {
                "status": EActionStatus.DONE,
                "result": {
                    item.host_id: item for item in results if item
                },
            }
        )
        await send_check_notification(results)
    except Exception as e:
        CACHE.update({"status": EActionStatus.ERROR})
        logging.exception(e)
        logging.error(
            "Error while checking all containers for all hosts"
        )
