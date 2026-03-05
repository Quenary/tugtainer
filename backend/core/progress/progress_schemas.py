from typing import Optional, TypedDict
from backend.core.action_result import (
    ContainerActionResult,
    GroupActionResult,
    HostActionResult,
)
from backend.enums.action_status_enum import EActionStatus


class ActionProgress(TypedDict, total=False):
    status: EActionStatus


class ContainerActionProgress(ActionProgress, total=False):
    """Data of container check progress"""

    result: Optional[ContainerActionResult]


class GroupActionProgress(ActionProgress, total=False):
    """Data of group update progress"""

    result: Optional[
        GroupActionResult
    ]  # Data wil be available only in the end


class HostActionProgress(ActionProgress, total=False):
    """Data of host check/update progress"""

    result: Optional[
        HostActionResult
    ]  # Data will be available only in the end


class AllActionProgress(ActionProgress, total=False):
    """Data of all hosts check/update progress"""

    result: Optional[
        dict[int, HostActionResult]
    ]  # Data will be available only in the end
