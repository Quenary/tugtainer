import logging
from datetime import timedelta
from typing import Final

from sqlalchemy import delete

from backend.const import DEFAULT_HEALTH_MONITOR_HISTORY_DAYS
from backend.db.session import async_session_maker
from backend.modules.health.health_model import ContainerHealthHistory
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.now import now

logger: Final = logging.getLogger("rotate_health_history")


async def rotate_health_history() -> None:
    """
    Delete old health history records based on HEALTH_MONITOR_HISTORY_DAYS.
    """
    days = int(
        SettingsStorage.get(ESettingKey.HEALTH_MONITOR_HISTORY_DAYS)
        or DEFAULT_HEALTH_MONITOR_HISTORY_DAYS
    )
    if days <= 0:
        return

    cutoff_date = now() - timedelta(days=days)

    try:
        async with async_session_maker() as session:
            stmt = delete(ContainerHealthHistory).where(
                ContainerHealthHistory.created_at < cutoff_date
            )
            result = await session.execute(stmt)
            await session.commit()
            rowcount = getattr(result, "rowcount", 0)
            if rowcount and rowcount > 0:
                logger.info(f"Deleted {rowcount} old health history records")
    except Exception:
        logger.exception("Failed to rotate health history")
