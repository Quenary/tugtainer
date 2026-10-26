from typing import Protocol

from python_on_whales import DockerClient
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.utils import run as docker_run_cmd

from shared.schemas.container_schemas import CreateContainerRequestBodySchema


class SelfUpdateDocker(Protocol):
    """Plain docker operations used by the self-update helper."""

    def inspect(self, name_or_id: str) -> ContainerInspectResult: ...

    def exists(self, name_or_id: str) -> bool: ...

    def image_exists(self, image_id: str) -> bool: ...

    def rename(self, name_or_id: str, new_name: str) -> None: ...

    def create(self, body: CreateContainerRequestBodySchema) -> str: ...

    def start(self, name_or_id: str) -> None: ...

    def stop(self, name_or_id: str) -> None: ...

    def remove(self, name_or_id: str) -> None: ...

    def run(self, command: list[str]) -> None: ...


class WhalesSelfUpdateDocker:
    """
    SelfUpdateDocker backed by python_on_whales.
    Uses the docker CLI of the image and the DOCKER_HOST env or socket mount.
    """

    def __init__(self, client: DockerClient | None = None):
        self._client = client or DockerClient()

    def inspect(self, name_or_id: str) -> ContainerInspectResult:
        container = self._client.container.inspect(name_or_id)
        # Same shape as the agent returns: name without the leading slash
        return container._get_inspect_result().model_copy(
            update={"name": container.name}
        )

    def exists(self, name_or_id: str) -> bool:
        return self._client.container.exists(name_or_id)

    def image_exists(self, image_id: str) -> bool:
        return self._client.image.exists(image_id)

    def rename(self, name_or_id: str, new_name: str) -> None:
        self._client.container.rename(name_or_id, new_name)

    def create(self, body: CreateContainerRequestBodySchema) -> str:
        container = self._client.container.create(**body.model_dump(exclude_unset=True))
        return container.id

    def start(self, name_or_id: str) -> None:
        self._client.container.start(name_or_id)

    def stop(self, name_or_id: str) -> None:
        self._client.container.stop(name_or_id)

    def remove(self, name_or_id: str) -> None:
        self._client.container.remove(name_or_id, force=True)

    def run(self, command: list[str]) -> None:
        docker_run_cmd(self._client.client_config.docker_cmd + command)
