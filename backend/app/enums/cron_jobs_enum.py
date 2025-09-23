from enum import Enum


class ECronJob(str, Enum):
    """Enum of crontab jobs keys"""

    CHECK_CONTAINERS = "CHECK_CONTAINERS"
