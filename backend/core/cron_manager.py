import logging
from zoneinfo import ZoneInfo, available_timezones
import aiocron
from typing import Callable, Dict
from backend.core.check_actions.check_all_containers import check_all_containers
from backend.core.update_actions.update_all_containers import update_all_containers
from backend.modules.settings.settings_enum import ESettingKey
from backend.enums.cron_jobs_enum import ECronJob
from backend.db.session import async_session_maker
from backend.modules.settings.settings_storage import SettingsStorage


VALID_TIMEZONES = available_timezones()


async def schedule_actions_on_init():
    """
    Schedule container check and update on app init
    """
    async with async_session_maker() as session:
        tz = SettingsStorage.get(ESettingKey.TIMEZONE)
        check_crontab = SettingsStorage.get(
            ESettingKey.CHECK_CRONTAB_EXPR
        )
        update_crontab = SettingsStorage.get(
            ESettingKey.UPDATE_CRONTAB_EXPR
        )

        if check_crontab:
            CronManager.schedule_job(
                ECronJob.CHECK_CONTAINERS,
                check_crontab,
                tz,
                check_all_containers,
            )
        if update_crontab:
            CronManager.schedule_job(
                ECronJob.UPDATE_CONTAINERS,
                update_crontab,
                tz,
                update_all_containers,
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
