from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.images.image_digest_model import ImageDigestModel
from backend.modules.images.image_digest_util import pending_image_digest
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
    cache: dict[str, ImageDigestModel] | None = None,
) -> list[ServiceListItem]:
    db_map = {item.name: item for item in db_services}
    digest_cache = cache or {}
    items: list[ServiceListItem] = []
    for svc in agent_services:
        db_item = db_map.get(svc.name)
        image_digest = pending_image_digest(
            bool(db_item.update_available) if db_item else False,
            db_item.remote_digests if db_item else None,
            digest_cache,
        )
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
                available_version=image_digest.version if image_digest else None,
                available_created=image_digest.created if image_digest else None,
                checked_at=db_item.checked_at if db_item else None,
                updated_at=db_item.updated_at if db_item else None,
                update_status_state=svc.update_status_state,
                update_status_message=svc.update_status_message,
                labels=svc.labels,
            )
        )
    return items
