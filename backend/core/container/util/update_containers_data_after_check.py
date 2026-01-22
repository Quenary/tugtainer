from sqlalchemy import select
from backend.db.models.containers_model import ContainersModel
from backend.core.container.schemas.check_result import (
    ContainerCheckResultType,
    GroupCheckResult,
)
from backend.helpers.now import now
from backend.db.session import async_session_maker


async def update_containers_data_after_check(
    result: GroupCheckResult | None,
) -> None:
    """Update containers in db after check/update process"""
    if not result:
        return
    valid_items = [item for item in result.items if item.result]
    if not valid_items:
        return
    _now = now()
    in_available: list[ContainerCheckResultType] = [
        "available",
        "available(notified)",
    ]

    async with async_session_maker() as session:
        container_names = [
            item.container.name for item in valid_items
        ]
        containers = await session.scalars(
            select(ContainersModel).where(
                ContainersModel.host_id == result.host_id,
                ContainersModel.name.in_(container_names),
            )
        )

        containers_map = {c.name: c for c in containers}

        for item in valid_items:
            if container := containers_map.get(
                str(item.container.name), None
            ):
                container.update_available = (
                    item.result in in_available
                )
                if item.result == "updated":
                    container.updated_at = _now
                    container.local_digests = item.remote_digests

        await session.commit()
