from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import HostManager
from python_on_whales import DockerClient
from app.db import HostModel


async def get_host(host_id: int, session: AsyncSession) -> HostModel:
    stmt = select(HostModel).where(HostModel.id == host_id).limit(1)
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Docker host not found in database")
    return host
