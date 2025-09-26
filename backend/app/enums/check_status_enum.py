from enum import Enum


class ECheckStatus(str, Enum):
    """
    Enum of available check process statuses
    """

    PREPARING = "PREPARING"
    CHECKING = "CHECKING"
    UPDATING = "UPDATING"
    DONE = "DONE"
    ERROR = "ERROR"
