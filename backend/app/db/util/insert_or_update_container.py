from datetime import datetime
from app.db.models import ContainersModel
from typing import TypedDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.containers_model import ContainersModel


class ContainerInsertOrUpdateData(TypedDict, total=False):
    """Dict of optional container fields in db"""
    check_enabled: bool
    update_enabled: bool
    update_available: bool
    checked_at: datetime
    updated_at: datetime


async def insert_or_update_container(
    session: AsyncSession,
    c_name: str,
    c_data: ContainerInsertOrUpdateData,
) -> ContainersModel:
    stmt = (
        select(ContainersModel)
        .where(ContainersModel.name == c_name)
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
        new_container = ContainersModel(**c_data, name=c_name)
        session.add(new_container)
        await session.commit()
        await session.refresh(new_container)
        return new_container
