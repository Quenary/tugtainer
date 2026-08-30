from enum import StrEnum


class EJobStatus(StrEnum):
    """Statuses of a check/update job."""

    PREPARING = "PREPARING"
    CHECKING = "CHECKING"
    UPDATING = "UPDATING"
    PRUNING = "PRUNING"
    DONE = "DONE"
    ERROR = "ERROR"
