from datetime import datetime
from cronsim import CronSim, CronSimError
from zoneinfo import available_timezones


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
        )
    return expr


def validate_timezone(tz: str) -> str:
    if tz in VALID_TIMEZONES:
        return tz
    raise ValueError(f"Invalid timezone: {tz}")
