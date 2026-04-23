from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.modules.containers.containers_model import ContainersModel
from .hosts_model import HostsModel


async def get_host(host_id: int, session: AsyncSession) -> HostsModel:
    """Get host info from db. Raise 404 if no host found."""
    stmt = select(HostsModel).where(HostsModel.id == host_id).limit(1)
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Docker host not found in database")
    return host


async def annotate_available_updates_count(
    hosts: list[HostsModel], session: AsyncSession
) -> None:
    """Populate each host's ``available_updates_count`` ad-hoc attribute.

    The count reflects containers on that host with ``update_available = True``.
    Safe to call with an empty list.
    """
    if not hosts:
        return
    host_ids = [h.id for h in hosts]
    stmt = (
        select(
            ContainersModel.host_id,
            func.count(ContainersModel.id),
        )
        .where(
            ContainersModel.host_id.in_(host_ids),
            ContainersModel.update_available.is_(True),
        )
        .group_by(ContainersModel.host_id)
    )
    result = await session.execute(stmt)
    counts = {host_id: cnt for host_id, cnt in result.all()}
    for host in hosts:
        host.available_updates_count = counts.get(host.id, 0)
