import logging
import aiocron
from typing import Callable, Dict, cast
from sqlalchemy import select
from app.enums import ESettingKey, ECronJob
from app.core.containers_core import check_and_update_containers
from app.db.session import _async_session_maker
from app.db.models import SettingModel


async def schedule_check_on_init():
    """
    Schedule container check and update on app init
    """
    async with _async_session_maker() as session:
        stmt = (
            select(SettingModel)
            .where(SettingModel.key == ESettingKey.CRONTAB_EXPR)
            .limit(1)
        )
        result = await session.execute(stmt)
        crontab_expr = result.scalar_one_or_none()

        if not crontab_expr:
            return

        CronManager.schedule_job(
            ECronJob.CHECK_CONTAINERS,
            cast(str, crontab_expr.value),
            check_and_update_containers,
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
    def schedule_job(cls, name: str, cron_expr: str, func: Callable, *args, **kwargs):
        """
        Create or recreate cron job.
        :param name: unique name
        :param cron_expr: crontab str e.g. '*/5 * * * *'
        :param func: coroutine
        """
        cls.cancel_job(name)

        cls._jobs[name] = aiocron.crontab(
            cron_expr, func=func, args=args, kwargs=kwargs
        )
        logging.info(f"[CronManager] Job '{name}' scheduled with '{cron_expr}'")

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
