from datetime import datetime
from zoneinfo import available_timezones

from cronsim import CronSim, CronSimError

VALID_TIMEZONES = available_timezones()


def validate_cron_expr(expr: str) -> str:
    """
    Validate crontab expr.
    Return valid or raises value error
    """
    try:
        CronSim(expr, datetime.now())
    except CronSimError as e:
        raise ValueError(
            f"Invalid cron expression: {expr}. Details: {e}"
        ) from None
    return expr


def validate_timezone(tz: str) -> str:
    if tz in VALID_TIMEZONES:
        return tz
    raise ValueError(f"Invalid timezone: {tz}")
