import logging
from zoneinfo import ZoneInfo, available_timezones
import aiocron
from typing import Callable, Dict, cast
from sqlalchemy import select
from backend.enums import ESettingKey, ECronJob
from backend.core.containers_core import check_all
from backend.db.session import async_session_maker
from backend.db.models import SettingModel


VALID_TIMEZONES = available_timezones()


async def schedule_check_on_init():
    """
    Schedule container check and update on app init
    """
    async with async_session_maker() as session:
        stmt = (
            select(SettingModel)
            .where(SettingModel.key == ESettingKey.CRONTAB_EXPR)
            .limit(1)
        )
        result = await session.execute(stmt)
        crontab_expr = result.scalar_one_or_none()

        if not crontab_expr:
            return

        stmt = (
            select(SettingModel)
            .where(SettingModel.key == ESettingKey.TIMEZONE)
            .limit(1)
        )
        result = await session.execute(stmt)
        tz = result.scalar_one_or_none()

        CronManager.schedule_job(
            ECronJob.CHECK_CONTAINERS,
            str(crontab_expr.value),
            tz.value if tz else None,
            lambda: check_all(True),
        )


class CronManager:
    _instance = None
    _jobs: Dict[str, aiocron.Cron] = {}

    def __new__(cls, *args, **kwargs):
        # Singleton
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def schedule_job(
        cls,
        name: str,
        cron_expr: str,
        tz: str | None,
        func: Callable,
        *args,
        **kwargs,
    ):
        """
        Create or recreate cron job.
        :param name: unique name
        :param cron_expr: crontab str e.g. '*/5 * * * *'
        :param func: coroutine
        """
        cls.cancel_job(name)
        _tz = ZoneInfo(tz) if tz in VALID_TIMEZONES else None
        cls._jobs[name] = aiocron.crontab(
            cron_expr, func=func, args=args, kwargs=kwargs, tz=_tz
        )
        logging.info(
            f"[CronManager] Job '{name}' scheduled with '{cron_expr}'"
        )

    @classmethod
    def cancel_job(cls, name: str):
        """Cancel job by name"""
        if name in cls._jobs:
            cls._jobs[name].stop()
            del cls._jobs[name]
            logging.info(f"[CronManager] Job '{name}' canceled.")

    @classmethod
    def cancel_all(cls):
        """Cancel all jobs"""
        for job in list(cls._jobs.keys()):
            cls._jobs[job].stop()
        cls._jobs.clear()
        logging.info("[CronManager] All jobs canceled.")

    @classmethod
    def get_jobs(cls):
        """Get registered jobs."""
        return list(cls._jobs.keys())
