from enum import Enum


class ECheckStatus(str, Enum):
    """
    Enum of available check process statuses
    """

    COLLECTING = "COLLECTING"
    CHECKING = "CHECKING"
    UPDATING = "UPDATING"
    DONE = "DONE"
