from sqlalchemy import and_, select
from backend.app.db.models.containers_model import ContainersModel
from backend.app.core.container.schemas.check_result import (
    GroupCheckResult,
)
from backend.app.helpers.now import now
from backend.app.db.session import async_session_maker


async def update_containers_data_after_check(
    result: GroupCheckResult | None,
) -> None:
    """Update containers in db after check/update process"""
    if not result:
        return
    _now = now()

    async with async_session_maker() as session:

        async def get_cont(c_name: str) -> ContainersModel | None:
            res = await session.execute(
                select(ContainersModel)
                .where(
                    and_(
                        ContainersModel.host_id == result.host_id,
                        ContainersModel.name == c_name,
                    )
                )
                .limit(1)
            )
            return res.scalar_one_or_none()

        for c in result.not_available:
            c_db = await get_cont(c.name)
            if c_db:
                c_db.update_available = False
                c_db.checked_at = _now
        for c in result.available:
            c_db = await get_cont(c.name)
            if c_db:
                c_db.update_available = True
                c_db.checked_at = _now
        for c in result.updated:
            c_db = await get_cont(c.name)
            if c_db:
                c_db.update_available = False
                c_db.checked_at = _now
                c_db.updated_at = _now
        await session.commit()
