from inspect import signature
from typing import Any, Literal
from aiohttp.typedefs import Query
from pydantic import BaseModel, TypeAdapter
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.exception import TugAgentClientError
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
    CreateContainerRequestBodySchema,
    GetContainerLogsRequestBody,
)
from backend.db.models import HostsModel
from backend.schemas.hosts_schema import HostInfo
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from shared.schemas.manifest_schema import ManifestInspectSchema
from shared.util.custom_json_dumps import custom_json_dumps
from shared.util.signature import get_signature_headers
import aiohttp
import logging


class AgentClient:
    def __init__(
        self,
        id: int,
        url: str,
        secret: str | None = None,
        timeout: int = 5,
        ssl: bool = True,
    ):
        self._id = id
        self._url = url
        self._secret = secret
        self._timeout = timeout
        self._long_timeout = (
            600  # timeout for potentially long requests
        )
        self._ssl = ssl
        self.public = AgentClientPublic(self)
        self.container = AgentClientContainer(self)
        self.image = AgentClientImage(self)
        self.command = AgentClientCommand(self)
        self.manifest = AgentClientManifest(self)

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        body: dict | BaseModel | None = None,
        params: Query | None = None,
        timeout: int | None = None,
    ) -> Any | None:
        if not timeout:
            timeout = self._timeout
        url = f"{self._url.rstrip('/')}/{path.lstrip('/')}"
        if isinstance(body, BaseModel):
            _body = body.model_dump(exclude_unset=True)
        else:
            _body = body
        headers = get_signature_headers(
            secret_key=self._secret,
            method=method,
            path=path,
            body=_body,
            params=params,
        )
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout),
            json_serialize=custom_json_dumps,
        ) as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=_body,
                params=params,
                ssl=self._ssl,
            ) as resp:
                # Parse error manually to get detail
                if resp.status >= 400:
                    try:
                        error_body = await resp.json()
                    except:
                        error_body = await resp.text()
                    logging.error(
                        f"Agent error:\n{resp.status}\n{error_body}"
                    )
                    raise TugAgentClientError(
                        f"Agent error {resp.status}",
                        resp.status,
                        error_body,
                    )
                # Raise other errors
                resp.raise_for_status()
                # Json response body
                if resp.content_length and resp.content_length > 0:
                    return await resp.json()
                # Chunked responses without content_length
                if resp.headers.get("Transfer-Encoding") == "chunked":
                    text = await resp.text()
                    return await resp.json() if text else None
                # Empty response body
                return None


class AgentClientPublic:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def health(self):
        return await self._agent_client._request(
            "GET", "/api/public/health"
        )

    async def access(self):
        return await self._agent_client._request(
            "GET", "/api/public/access"
        )


class AgentClientManifest:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def inspect(
        self, spec_or_digest: str
    ) -> ManifestInspectSchema:
        data = await self._agent_client._request(
            "GET",
            f"/api/manifest/inspect",
            params={"spec_or_digest": spec_or_digest},
            timeout=self._agent_client._long_timeout,
        )
        return ManifestInspectSchema.model_validate(data)


class AgentClientContainer:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def list(
        self, body: GetContainerListBodySchema
    ) -> list[ContainerInspectResult]:
        data = await self._agent_client._request(
            "POST", f"/api/container/list", body
        )
        return TypeAdapter(
            list[ContainerInspectResult]
        ).validate_python(data or [])

    async def exists(self, name_or_id: str) -> bool:
        data = await self._agent_client._request(
            "GET", f"/api/container/exists/{name_or_id}"
        )
        return bool(data)

    async def inspect(
        self, name_or_id: str
    ) -> ContainerInspectResult:
        data = await self._agent_client._request(
            "GET", f"/api/container/inspect/{name_or_id}"
        )
        return ContainerInspectResult.model_validate(data)

    async def create(
        self, body: CreateContainerRequestBodySchema
    ) -> ContainerInspectResult:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/create",
            body,
            timeout=self._agent_client._long_timeout,
        )
        return ContainerInspectResult.model_validate(data)

    async def start(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/start/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def stop(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/stop/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def restart(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/restart/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def kill(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/kill/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def pause(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/pause/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def unpause(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/unpause/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def remove(self, name_or_id: str) -> str:
        data = await self._agent_client._request(
            "DELETE",
            f"/api/container/remove/{name_or_id}",
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def logs(
        self,
        name_or_id: str,
        body: GetContainerLogsRequestBody,
    ) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/container/logs/{name_or_id}",
            body=body,
            timeout=self._agent_client._long_timeout,
        )
        return str(data)


class AgentClientImage:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def inspect(
        self, body: InspectImageRequestBodySchema
    ) -> ImageInspectResult:
        data = await self._agent_client._request(
            "GET", f"/api/image/inspect", body
        )
        return ImageInspectResult.model_validate(data)

    async def list(
        self, body: GetImageListBodySchema
    ) -> list[ImageInspectResult]:
        data = await self._agent_client._request(
            "POST", f"/api/image/list", body
        )
        return TypeAdapter(list[ImageInspectResult]).validate_python(
            data or []
        )

    async def prune(self, body: PruneImagesRequestBodySchema) -> str:
        data = await self._agent_client._request(
            "POST",
            f"/api/image/prune",
            body,
            timeout=self._agent_client._long_timeout,
        )
        return str(data)

    async def pull(
        self, body: PullImageRequestBodySchema
    ) -> ImageInspectResult:
        data = await self._agent_client._request(
            "POST",
            f"/api/image/pull",
            body,
            timeout=self._agent_client._long_timeout,
        )
        return ImageInspectResult.model_validate(data)

    async def tag(self, body: TagImageRequestBodySchema):
        return await self._agent_client._request(
            "POST", f"/api/image/tag", body
        )


class AgentClientCommand:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def run(
        self, body: RunCommandRequestBodySchema
    ) -> tuple[str, str]:
        data = await self._agent_client._request(
            "POST",
            f"/api/command/run",
            body,
            timeout=self._agent_client._long_timeout,
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
