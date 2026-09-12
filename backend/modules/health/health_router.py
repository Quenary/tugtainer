import logging
from typing import Final

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized_req
from backend.modules.health.health_model import ContainerHealthHistory
from backend.modules.health.health_schemas import (
    HealthHistoryFilterRequest,
    HealthHistoryPagedResponse,
    HealthHistoryResponseItem,
)

logger: Final = logging.getLogger("health_router")

health_router = APIRouter(
    prefix="/health",
    tags=["health"],
    dependencies=[Depends(is_authorized_req)],
)


@health_router.post("/history", response_model=HealthHistoryPagedResponse)
async def get_health_history(
    req: HealthHistoryFilterRequest,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(ContainerHealthHistory).where(
        ContainerHealthHistory.host_id == req.host_id
    )
    if req.container_id is not None:
        stmt = stmt.where(ContainerHealthHistory.container_id == req.container_id)
    if req.status:
        stmt = stmt.where(ContainerHealthHistory.status.in_(req.status))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0

    # Paginate
    offset = (req.page - 1) * req.limit
    stmt = (
        stmt.options(joinedload(ContainerHealthHistory.container))
        .order_by(ContainerHealthHistory.created_at.desc())
        .offset(offset)
        .limit(req.limit)
    )

    db_items = (await session.execute(stmt)).scalars().all()

    items: list[HealthHistoryResponseItem] = []
    for item in db_items:
        items.append(
            HealthHistoryResponseItem(
                id=item.id,
                host_id=item.host_id,
                container_id=item.container_id,
                container_name=item.container.name if item.container else "Unknown",
                status=item.status,
                restarted=item.restarted,
                notified=item.notified,
                created_at=item.created_at,
            )
        )

    return HealthHistoryPagedResponse(
        total=total,
        page=req.page,
        limit=req.limit,
        items=items,
    )
