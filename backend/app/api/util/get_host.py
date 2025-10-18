from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import HostsModel


async def get_host(host_id: int, session: AsyncSession) -> HostsModel:
    """Get host info from db. Raise 404 if no host found."""
    stmt = select(HostsModel).where(HostsModel.id == host_id).limit(1)
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Docker host not found in database")
    return host
