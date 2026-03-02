from dataclasses import dataclass, field
from typing import Literal
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.core.container.schemas.check_result import (
    ContainerCheckResultType,
)
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)


@dataclass
class ContainerGroupItem:
    """
    Item of container group to be processed
    :param container: container object
    :param action: action to be performed (selection in db)
    :param available: is new image available
    :param image_spec: image spec e.g. quenary/tugtainer:latest
    :param config: kwargs for create/run
    :param commands: list of commands to be executed after container starts
    :param local_image: local image of the container (or old if updated)
    :param remote_image: remote image for the container (or current if updated)
    :param local_digests: local image digests (or old if updated)
    :param remote_digests: remote image digests (or current if updated)
    """

    container: ContainerInspectResult
    action: Literal["update", "check", None]
    protected: bool  # Whether container labeled with dev.quenary.tugtainer.protected=true, so it cannot be stopped and updated
    service_name: str | None  # docker compose service name
    compose_deps: list[str]  # docker compose dependencies
    tugtainer_deps: list[str]  # tugtainer dependencies
    temp_result: ContainerCheckResultType | None = None
    image_spec: str | None = None
    config: CreateContainerRequestBodySchema | None = None
    commands: list[list[str]] = field(default_factory=list)
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None
    local_digests: list[str] = field(default_factory=list)
    remote_digests: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        """
        This is helper to get name with proper typing.
        Name of the container cannot be None
        """
        return self.container.name or ""


@dataclass
class ContainerGroup:
    """
    Container group for further processing,
    where list is in order of dependency,
    first is most dependable and last is most dependant.
    :param name: name of the group
    :param containers: list of associated containers
    """

    name: str
    containers: list[ContainerGroupItem]
