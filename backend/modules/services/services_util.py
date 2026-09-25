from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.services.services_model import SwarmServicesModel
from backend.modules.services.services_schemas import ServiceListItem
from shared.schemas.service_schemas import ServiceListItemSchema


async def get_host_services(
    session: AsyncSession, host_id: int
) -> Sequence[SwarmServicesModel]:
    stmt = select(SwarmServicesModel).where(SwarmServicesModel.host_id == host_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_or_create_service(
    session: AsyncSession,
    host_id: int,
    service_id: str,
    name: str,
    image: str,
) -> SwarmServicesModel:
    stmt = (
        select(SwarmServicesModel)
        .where(
            SwarmServicesModel.host_id == host_id,
            SwarmServicesModel.name == name,
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        item = SwarmServicesModel(
            host_id=host_id,
            service_id=service_id,
            name=name,
            image=image,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return item


def merge_service_items(
    agent_services: list[ServiceListItemSchema],
    db_services: Sequence[SwarmServicesModel],
) -> list[ServiceListItem]:
    db_map = {item.name: item for item in db_services}
    items: list[ServiceListItem] = []
    for svc in agent_services:
        db_item = db_map.get(svc.name)
        items.append(
            ServiceListItem(
                id=svc.id,
                name=svc.name,
                image=svc.image,
                mode=svc.mode,
                replicas_running=svc.replicas.running,
                replicas_desired=svc.replicas.desired,
                check_enabled=bool(db_item.check_enabled)
                if db_item and db_item.check_enabled is not None
                else False,
                update_enabled=bool(db_item.update_enabled)
                if db_item and db_item.update_enabled is not None
                else False,
                update_available=bool(db_item.update_available)
                if db_item and db_item.update_available is not None
                else False,
                checked_at=db_item.checked_at if db_item else None,
                updated_at=db_item.updated_at if db_item else None,
                update_status_state=svc.update_status_state,
                update_status_message=svc.update_status_message,
                labels=svc.labels,
            )
        )
    return items
