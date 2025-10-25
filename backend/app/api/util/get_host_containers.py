from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ContainersModel


async def get_host_containers(
    session: AsyncSession, host_id: int
) -> list[ContainersModel]:
    result = await session.execute(
        select(ContainersModel).where(
            ContainersModel.host_id == host_id
        )
    )
    return list(result.scalars().all())
