from enum import StrEnum


class EActionStatus(StrEnum):
    """
    Enum of available action (check, update) statuses
    """

    PREPARING = "PREPARING"
    CHECKING = "CHECKING"
    UPDATING = "UPDATING"
    PRUNING = "PRUNING"
    DONE = "DONE"
    ERROR = "ERROR"
