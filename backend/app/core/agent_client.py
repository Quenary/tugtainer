from inspect import signature
from typing import Any, Literal, cast
from pydantic import TypeAdapter
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
import requests
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
    CreateContainerRequestBodySchema,
)
from backend.app.db.models import HostsModel
from backend.app.schemas.hosts_schema import HostInfo
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from shared.util.signature import get_signature_headers


class AgentClient:
    def __init__(
        self, id: int, url: str, agent_secret: str | None = None
    ):
        self._id = id
        self._url = url
        self._agent_secret = agent_secret
        self.public = AgentClientPublic(self)
        self.container = AgentClientContainer(self)
        self.image = AgentClientImage(self)
        self.command = AgentClientCommand(self)

    def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        body: Any = None,
    ) -> Any | None:
        url = f"{self._url.rstrip('/')}/{path.lstrip('/')}"
        headers = get_signature_headers(
            self._agent_secret, method, url, body
        )
        resp = requests.request(method, url, json=body, timeout=5)
        resp.raise_for_status()
        return resp.json() if resp.content else None


class AgentClientPublic:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    def health(self):
        return self._agent_client._request(
            "GET", "/api/public/health"
        )

    def access(self):
        return self._agent_client._request(
            "GET", "/api/public/access"
        )


class AgentClientContainer:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    def list(
        self, body: GetContainerListBodySchema
    ) -> list[ContainerInspectResult]:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/container/list", _body
        )
        return TypeAdapter(
            list[ContainerInspectResult]
        ).validate_python(data or [])

    def exists(self, name_or_id: str) -> bool:
        data = self._agent_client._request(
            "GET", f"/api/container/exists/{name_or_id}"
        )
        return bool(data)

    def inspect(self, name_or_id: str) -> ContainerInspectResult:
        data = self._agent_client._request(
            "GET", f"/api/container/inspect/{name_or_id}"
        )
        return ContainerInspectResult.model_validate(data)

    def create(
        self, body: CreateContainerRequestBodySchema
    ) -> ContainerInspectResult:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/container/create", _body
        )
        return ContainerInspectResult.model_validate(data)

    def start(self, name_or_id: str) -> str:
        data = self._agent_client._request(
            "POST", f"/api/container/start/{name_or_id}"
        )
        return str(data)

    def stop(self, name_or_id: str) -> str:
        data = self._agent_client._request(
            "POST", f"/api/container/stop/{name_or_id}"
        )
        return str(data)

    def remove(self, name_or_id: str) -> str:
        data = self._agent_client._request(
            "POST", f"/api/container/remove/{name_or_id}"
        )
        return str(data)


class AgentClientImage:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    def inspect(
        self, body: InspectImageRequestBodySchema
    ) -> ImageInspectResult:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "GET", f"/api/image/inspect", _body
        )
        return ImageInspectResult.model_validate(data)

    def list(
        self, body: GetImageListBodySchema
    ) -> list[ImageInspectResult]:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/image/list", _body
        )
        return TypeAdapter(list[ImageInspectResult]).validate_python(
            data or []
        )

    def prune(self, body: PruneImagesRequestBodySchema) -> str:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/image/prune", _body
        )
        return str(data)

    def pull(
        self, body: PullImageRequestBodySchema
    ) -> ImageInspectResult:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/image/pull", _body
        )
        return ImageInspectResult.model_validate(data)

    def tag(self, body: TagImageRequestBodySchema):
        _body = body.model_dump(exclude_unset=True)
        return self._agent_client._request(
            "POST", f"/api/image/tag", _body
        )


class AgentClientCommand:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    def run(
        self, body: RunCommandRequestBodySchema
    ) -> tuple[str, str]:
        _body = body.model_dump(exclude_unset=True)
        data = self._agent_client._request(
            "POST", f"/api/command/run", _body
        )
        return TypeAdapter(tuple[str, str]).validate_python(data)


class AgentClientManager:
    """Class for managing multiple agents"""

    _INSTANCE = None
    _HOST_CLIENTS: dict[int, AgentClient] = {}

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    @classmethod
    def set_client(cls, host: HostsModel):
        cls.remove_client(host.id)
        cls._HOST_CLIENTS[host.id] = cls._create_client(host)

    @classmethod
    def get_host_client(cls, host: HostsModel) -> AgentClient:
        if host.id in cls._HOST_CLIENTS:
            return cls._HOST_CLIENTS[host.id]
        client = cls._create_client(host)
        cls._HOST_CLIENTS[host.id] = cls._create_client(host)
        return client

    @classmethod
    def _create_client(cls, host: HostsModel) -> AgentClient:
        info = HostInfo.model_validate(host)
        allowed_keys = signature(AgentClient.__init__).parameters
        filtered = {
            k: v
            for k, v in info.model_dump(exclude_unset=True).items()
            if k in allowed_keys and v
        }
        return AgentClient(**filtered)

    @classmethod
    def get_all(cls) -> list[tuple[int, AgentClient]]:
        """
        Get all registered host clients.
        :returns: list of tuple(host_id, client)
        """
        return list[tuple[int, AgentClient]](
            cls._HOST_CLIENTS.items()
        )

    @classmethod
    def remove_client(cls, id: int):
        cls._HOST_CLIENTS.pop(id, None)
