from dataclasses import dataclass, field
from typing import Literal
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)


@dataclass
class CheckContainerUpdateAvailableResult:
    available: bool = False
    image_spec: str | None = None
    old_image: ImageInspectResult | None = None
    new_image: ImageInspectResult | None = None


ContainerCheckResultType = Literal[
    "not_available",
    "available",
    "available(notified)",
    "updated",
    "rolled_back",
    "failed",
    None,
]


@dataclass
class ContainerCheckResult:
    container: ContainerInspectResult
    old_image: ImageInspectResult | None
    new_image: ImageInspectResult | None
    result: ContainerCheckResultType


@dataclass
class GroupCheckResult:
    host_id: int
    host_name: str
    items: list[ContainerCheckResult] = field(default_factory=list)


@dataclass
class HostCheckResult(GroupCheckResult):
    prune_res: str | None = None
