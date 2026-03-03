from enum import Enum


class EActionStatus(str, Enum):
    """
    Enum of available action (check, update) statuses
    """

    PREPARING = "PREPARING"
    CHECKING = "CHECKING"
    UPDATING = "UPDATING"
    PRUNING = "PRUNING"
    DONE = "DONE"
    ERROR = "ERROR"
