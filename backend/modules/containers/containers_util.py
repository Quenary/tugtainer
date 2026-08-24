from datetime import datetime
from typing import TypedDict

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .containers_model import ContainersModel


async def get_host_containers(
    session: AsyncSession, host_id: int
) -> list[ContainersModel]:
    result = await session.execute(
        select(ContainersModel).where(ContainersModel.host_id == host_id)
    )
    return list(result.scalars().all())


class ContainerInsertOrUpdateData(TypedDict, total=False):
    """Dict of optional container fields in db"""

    check_enabled: bool
    update_enabled: bool
    update_available: bool
    checked_at: datetime
    updated_at: datetime
    remote_digests_changed_at: datetime | None
    delay_update_for: int | None
    local_digests: list[str]
    remote_digests: list[str]
    image_id: str
    previous_image_digests: list[str] | None
    previous_image_tags: list[str] | None
    previous_image_version: str | None
    hooks: dict[str, list[str]]


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
            if hasattr(container, key) and getattr(container, key) != value:
                setattr(container, key, value)
        await session.commit()
        await session.refresh(container)
        return container
    else:
        new_container = ContainersModel(**c_data, host_id=host_id, name=c_name)
        session.add(new_container)
        await session.commit()
        await session.refresh(new_container)
        return new_container
