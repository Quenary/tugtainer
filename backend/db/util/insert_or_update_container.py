from datetime import datetime
from backend.db.models import ContainersModel
from typing import TypedDict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.containers_model import ContainersModel


class ContainerInsertOrUpdateData(TypedDict, total=False):
    """Dict of optional container fields in db"""

    check_enabled: bool
    update_enabled: bool
    update_available: bool
    checked_at: datetime
    updated_at: datetime
    local_digests: list[str]
    remote_digests: list[str]


async def insert_or_update_container(
    session: AsyncSession,
    host_id: int,
    c_name: str,
    c_data: ContainerInsertOrUpdateData,
) -> ContainersModel:
    stmt = (
        select(ContainersModel)
        .where(
            and_(
                ContainersModel.host_id == host_id,
                ContainersModel.name == c_name,
            )
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    container = result.scalar_one_or_none()
    if container:
        for key, value in c_data.items():
            if (
                hasattr(container, key)
                and getattr(container, key) != value
            ):
                setattr(container, key, value)
        await session.commit()
        await session.refresh(container)
        return container
    else:
        new_container = ContainersModel(
            **c_data, host_id=host_id, name=c_name
        )
        session.add(new_container)
        await session.commit()
        await session.refresh(new_container)
        return new_container
