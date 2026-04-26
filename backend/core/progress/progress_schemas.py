from typing import TypedDict

from backend.core.action_result import (
    ContainerActionResult,
    HostActionResult,
    UpdatePlanResult,
)
from backend.enums.action_status_enum import EActionStatus


class ActionProgress(TypedDict, total=False):
    status: EActionStatus


class ContainerActionProgress(ActionProgress, total=False):
    """Data of container check progress"""

    result: ContainerActionResult | None


class UpdatePlanProgress(ActionProgress, total=False):
    """Data of update plan execution progress"""

    result: UpdatePlanResult | None


class HostActionProgress(ActionProgress, total=False):
    """Data of host check/update progress"""

    result: HostActionResult | None  # Data will be available only in the end


class AllActionProgress(ActionProgress, total=False):
    """Data of all hosts check/update progress"""

    result: dict[int, HostActionResult] | None  # Data will be available only in the end
