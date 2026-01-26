from dataclasses import dataclass, field
from typing import Literal
from python_on_whales.components.buildx.imagetools.models import (
    ImageVariantManifest,
)
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)


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
class CheckContainerUpdateAvailableResult:
    result: ContainerCheckResultType = None
    image_spec: str | None = None
    local_image: ImageInspectResult | None = None
    local_digests: list[str] = field(
        default_factory=list
    )
    remote_digests: list[str] = field(
        default_factory=list
    )


@dataclass
class ContainerCheckResult:
    container: ContainerInspectResult
    local_image: ImageInspectResult | None
    remote_image: ImageInspectResult | None
    local_digests: list[str]
    remote_digests: list[str]
    result: ContainerCheckResultType


@dataclass
class GroupCheckResult:
    host_id: int
    host_name: str
    items: list[ContainerCheckResult] = field(default_factory=list)


@dataclass
class HostCheckResult(GroupCheckResult):
    prune_result: str | None = None
