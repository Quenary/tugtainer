from datetime import datetime
from typing import TypedDict

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.container_util.get_container_health_status_str import (
    get_container_health_status_str,
)
from backend.core.container_util.is_protected_container import (
    is_protected_container,
)

from .containers_model import ContainersModel
from .containers_schemas import ContainersListItem


async def get_host_containers(
    session: AsyncSession, host_id: int
) -> list[ContainersModel]:
    result = await session.execute(
        select(ContainersModel).where(ContainersModel.host_id == host_id)
    )
    return list(result.scalars().all())


def map_container_schema(
    host_id: int,
    d_cont: ContainerInspectResult,
    db_cont: ContainersModel | None,
) -> ContainersListItem:
    """
    Map docker container data and db container data
    to api response schema
    """
    _item = ContainersListItem(
        name=d_cont.name if d_cont.name else "",
        image=(d_cont.config.image if d_cont.config and d_cont.config.image else None),
        container_id=d_cont.id if d_cont.id else "",
        ports=(d_cont.host_config.port_bindings if d_cont.host_config else None),
        status=d_cont.state.status if d_cont.state else None,
        exit_code=d_cont.state.exit_code if d_cont.state else None,
        health=get_container_health_status_str(d_cont),
        protected=is_protected_container(d_cont),
        host_id=host_id,
    )
    if db_cont:
        _item.id = db_cont.id
        _item.check_enabled = db_cont.check_enabled
        _item.update_enabled = db_cont.update_enabled
        _item.update_available = db_cont.update_available
        _item.checked_at = db_cont.checked_at
        _item.updated_at = db_cont.updated_at
        _item.created_at = db_cont.created_at
        _item.modified_at = db_cont.modified_at

    return _item


class ContainerInsertOrUpdateData(TypedDict, total=False):
    """Dict of optional container fields in db"""

    check_enabled: bool
    update_enabled: bool
    update_available: bool
    checked_at: datetime
    updated_at: datetime
    local_digests: list[str]
    remote_digests: list[str]
    image_id: str


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
