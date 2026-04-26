from datetime import UTC, datetime


def now() -> datetime:
    """Get current utc time without tz (naive)"""
    return datetime.now(UTC).replace(tzinfo=None)
