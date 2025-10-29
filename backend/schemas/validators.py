import re
from datetime import datetime
from cronsim import CronSim, CronSimError
from zoneinfo import available_timezones


VALID_TIMEZONES = available_timezones()


def password_validator(value: str) -> str:
    """Validate password string"""
    if not re.search(r"[A-Z]", value):
        raise ValueError(
            "The password must contain at least one uppercase letter."
        )
    if not re.search(r"[a-z]", value):
        raise ValueError(
            "The password must contain at least one lowercase letter."
        )
    if not re.search(r"\d", value):
        raise ValueError(
            "The password must contain at least one number."
        )
    return value


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
