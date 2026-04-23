from dataclasses import dataclass, field
from typing import Final, cast
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.core.action_result import ContainerCheckResultType
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)


@dataclass
class UpdatePlan:
    to_update: set[str]
    affected: set[str]
    order: list[str]


@dataclass
class UpdatePlanItem:
    """
    Internal state of the update plan executor item
    :param container: container object
    :param image_spec: image spec e.g. quenary/tugtainer:latest
    :param config: kwargs for create/run
    :param commands: list of commands to be executed after container starts
    :param local_image: current image
    :param remote_image: new pulled image
    :param result: result of the action
    """

    container: ContainerInspectResult
    image_spec: Final[str | None]
    was_running: Final[bool]
    config: CreateContainerRequestBodySchema | None = None
    commands: list[list[str]] = field(default_factory=list)
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None
    result: ContainerCheckResultType | None = None
    errors: list[Exception] = field(default_factory=list)

    @property
    def name(self) -> str:
        """
        Get name with proper typing.
        Name of the container cannot be None
        """
        return cast(str, self.container.name)
