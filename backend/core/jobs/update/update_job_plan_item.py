from dataclasses import dataclass, field
from typing import Final, cast

from backend.core.jobs.jobs_results import ContainerJobOutcome
from shared.runtime.runtime_models import (
    ContainerInspectResult,
    ImageInspectResult,
)
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from shared.schemas.network_schemas import NetworkConnectBodySchema


@dataclass
class UpdateJobPlanItem:
    """
    Internal state of the update plan executor item
    :param container: container object
    :param image_spec: image spec e.g. quenary/tugtainer:latest
    :param config: kwargs for create/run
    :param network_connects: list of secondary NetworkConnectBodySchema items to connect
    :param local_image: current image
    :param remote_image: new pulled image
    :param result: result of the action
    """

    container: ContainerInspectResult
    image_spec: Final[str | None] = None
    was_running: Final[bool | None] = None
    config: CreateContainerRequestBodySchema | None = None
    network_connects: list[NetworkConnectBodySchema] = field(default_factory=list)
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None
    result: ContainerJobOutcome | None = None
    errors: list[Exception] = field(default_factory=list)

    @property
    def name(self) -> str:
        """
        Get name with proper typing.
        Name of the container cannot be None
        """
        return cast(str, self.container.name)
