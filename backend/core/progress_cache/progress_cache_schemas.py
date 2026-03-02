from typing import Optional, TypedDict
from backend.core.container.schemas.check_result import (
    GroupCheckResult,
    HostCheckResult,
)
from backend.enums.check_status_enum import ECheckStatus


class GroupCheckProgressCache(TypedDict, total=False):
    """Data of containers group check/update progress"""

    status: ECheckStatus  # Status of progress
    result: Optional[
        GroupCheckResult
    ]  # Data wil be available only in the end


class HostCheckProgressCache(TypedDict, total=False):
    """Data of host container's check/update progress"""

    status: ECheckStatus  # Status of progress
    result: Optional[
        HostCheckResult
    ]  # Data will be available only in the end


class AllCheckProgressCache(TypedDict, total=False):
    """Data of all host's container's check/update progress"""

    status: ECheckStatus  # Status of progress
    result: Optional[
        dict[int, HostCheckResult]
    ]  # Data will be available only in the end
