import logging
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.agent_client import AgentClientManager
from backend.db.session import async_session_maker
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.hosts.hosts_model import HostsModel
from shared.schemas.container_schemas import GetContainerListBodySchema

logger: Final = logging.getLogger("cleanup_containers")


async def cleanup_host_stale_containers(
    host: HostsModel,
    session: AsyncSession,
) -> None:
    """Clear update_available flag for containers that no longer exist on the host."""
    if not host.enabled:
        return

    client: Final = AgentClientManager.get_host_client(host)
    try:
        agent_containers: Final = await client.container.list(
            GetContainerListBodySchema(all=True)
        )
    except Exception:
        logger.exception(
            f"Failed to fetch containers from host {host.id} ({host.name}), skipping cleanup"
        )
        return

    active_names: Final[set[str]] = {c.name for c in agent_containers if c.name}

    db_containers: Final = (
        (
            await session.execute(
                select(ContainersModel).where(ContainersModel.host_id == host.id)
            )
        )
        .scalars()
        .all()
    )

    cleared_count = 0
    for container in db_containers:
        if container.name not in active_names:
            if container.update_available:
                container.update_available = False
                cleared_count += 1
                logger.info(
                    f"Cleared update_available for non-existing container "
                    f"'{container.name}' on host {host.id} ({host.name})"
                )

    if cleared_count > 0:
        await session.commit()
        logger.info(
            f"Cleared update_available for {cleared_count} stale container(s) on host {host.id} ({host.name})"
        )


async def cleanup_all_stale_containers() -> None:
    """Check all enabled hosts and clear update_available flag for containers

    that do not exist physically on the host.
    """
    logger.info("Starting cleanup of stale container statuses for all hosts")
    try:
        async with async_session_maker() as session:
            hosts: Final = (
                (await session.execute(select(HostsModel).where(HostsModel.enabled)))
                .scalars()
                .all()
            )

            for host in hosts:
                try:
                    await cleanup_host_stale_containers(host, session)
                except Exception:
                    logger.exception(
                        f"Error cleaning up stale containers for host {host.id} ({host.name})"
                    )
    except Exception:
        logger.exception("Error while running stale containers cleanup job")
