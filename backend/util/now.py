from datetime import datetime, timezone


def now() -> datetime:
    """Get current utc time without tz (naive)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
