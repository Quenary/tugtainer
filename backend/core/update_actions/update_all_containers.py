import logging
from sqlalchemy import select
from backend.db.session import async_session_maker
from backend.modules.hosts.hosts_model import HostsModel
from backend.core.action_result import (
    HostActionResult,
)
from backend.core.agent_client import AgentClientManager
from backend.core.notifications_core import send_check_notification
from backend.enums.action_status_enum import EActionStatus
from backend.core.progress.progress_schemas import (
    AllActionProgress,
)
from backend.core.progress.progress_util import (
    ALL_CONTAINERS_STATUS_KEY,
    is_allowed_start_cache,
)
from backend.core.progress.progress_cache import ProgressCache
from .update_host_containers import update_host_containers


async def update_all_containers():
    """
    Main func for scheduled/manual update of all containers
    marked for it, for all specified docker hosts.
    Should not raises errors, only logging.
    """
    CACHE = ProgressCache[AllActionProgress](
        ALL_CONTAINERS_STATUS_KEY
    )
    try:
        STATE = CACHE.get()
        if not is_allowed_start_cache(STATE):
            logging.warning(
                "General update process is already running."
            )
            return

        CACHE.set(
            {"status": EActionStatus.PREPARING},
        )
        logging.info("Start updating of all containers for all hosts")

        async with async_session_maker() as session:
            result = await session.execute(
                select(HostsModel).where(HostsModel.enabled == True)
            )
            hosts = result.scalars().all()

        CACHE.update({"status": EActionStatus.UPDATING})
        results: list[HostActionResult] = []
        for host in hosts:
            client = AgentClientManager.get_host_client(host)
            result = await update_host_containers(
                host,
                client,
            )
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
            "Error while updating of all containers for all hosts"
        )
