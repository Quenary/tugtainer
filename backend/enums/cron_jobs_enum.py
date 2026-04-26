from enum import StrEnum


class ECronJob(StrEnum):
    """Enum of crontab jobs keys"""

    CHECK_CONTAINERS = "CHECK_CONTAINERS"
    UPDATE_CONTAINERS = "UPDATE_CONTAINERS"