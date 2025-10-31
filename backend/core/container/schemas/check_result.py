from dataclasses import dataclass, field
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


@dataclass
class ShrinkedContainer:
    """This class contains only necessary data of container"""

    name: str
    image_spec: str

    @classmethod
    def from_c(cls, c: ContainerInspectResult) -> "ShrinkedContainer":
        if not c.name or not c.config or not c.config.image:
            raise Exception(
                "Cannot create ShrinkedContainer, no data."
            )
        return ShrinkedContainer(
            name=c.name, image_spec=c.config.image
        )


@dataclass
class GroupCheckResult:
    host_id: int
    host_name: str
    not_available: list[ShrinkedContainer] = field(
        default_factory=list
    )
    available: list[ShrinkedContainer] = field(default_factory=list)
    updated: list[ShrinkedContainer] = field(default_factory=list)
    rolled_back: list[ShrinkedContainer] = field(default_factory=list)
    failed: list[ShrinkedContainer] = field(default_factory=list)


@dataclass
class HostCheckResult(GroupCheckResult):
    prune_res: str | None = None
