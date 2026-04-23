import asyncio
from inspect import signature
import json
from typing import Any, Final, Literal
from aiohttp.typedefs import Query
from fastapi import status
from pydantic import BaseModel, TypeAdapter
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from sqlalchemy import select
from backend.db.session import async_session_maker
from backend.exception import TugAgentClientError
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
    CreateContainerRequestBodySchema,
    GetContainerLogsRequestBody,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_schemas import HostInfo
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from shared.schemas.manifest_schema import ManifestInspectSchema
from shared.schemas.network_schemas import NetworkDisconnectBodySchema
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
        self._ssl:Final = ssl
        self._session: aiohttp.ClientSession | None = None
        self._session_lock:Final = asyncio.Lock()
        self._logger:Final = logging.getLogger(self.__class__.__name__)
        self.public:Final = AgentClientPublic(self)
        self.container:Final = AgentClientContainer(self)
        self.image:Final = AgentClientImage(self)
        self.command:Final = AgentClientCommand(self)
        self.manifest:Final = AgentClientManifest(self)
        self.network:Final = AgentClientNetwork(self)
        self.common:Final = AgentClientCommon(self)

    async def close_session(self):
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get existing session or create a new one."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(
                    json_serialize=custom_json_dumps,
                    trust_env=True,
                )
            return self._session

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close_session()

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        path: str,
        body: dict | BaseModel | None = None,
        params: Query | None = None,
        timeout: int | float | None = None,
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
        session = await self._get_session()

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                json=_body,
                params=params,
                ssl=self._ssl,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    message = "Agent request error"
                    self._logger.exception(message)
                    try:
                        error_body = await resp.json()
                    except Exception:
                        error_body = await resp.text()
                    raise TugAgentClientError(
                        message,
                        url,
                        method,
                        resp.status,
                        error_body,
                    )

                text = await resp.text()
                if not text:
                    return None
                try:
                    return json.loads(text)
                except Exception:
                    return text
        except asyncio.TimeoutError as e:
            message = "Agent timeout error"
            self._logger.exception(message)
            raise TugAgentClientError(
                message,
                url,
                method,
                status.HTTP_408_REQUEST_TIMEOUT,
                "The problem is most likely related to the low Agent Timeout value, which you can increase in the host settings.",
            )
        except aiohttp.ClientError as e:
            message = "Agent connection error"
            self._logger.exception(message)
            await self.close_session()
            raise TugAgentClientError(
                message,
                url,
                method,
                status.HTTP_502_BAD_GATEWAY,
                str(e),
            )


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
            "POST",
            f"/api/image/list",
            body,
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
        if not data:
            return ("", "")
        if isinstance(data, str):
            return (data, "")
        try:
            return TypeAdapter(tuple[str, str]).validate_python(data)
        except Exception:
            return (str(data), "")


class AgentClientNetwork:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def disconnect(
        self,
        body: NetworkDisconnectBodySchema,
    ) -> None:
        await self._agent_client._request(
            "POST",
            "/api/network/disconnect",
            body,
        )


class AgentClientCommon:
    def __init__(self, agent_client: AgentClient):
        self._agent_client = agent_client

    async def version(self):
        data = await self._agent_client._request(
            "GET",
            "/api/common/version",
        )
        return DockerVersionScheme.model_validate(data)


async def load_agents_on_init():
    """Get hosts from db and init clients"""
    async with async_session_maker() as session:
        stmt = select(HostsModel).where(HostsModel.enabled == True)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        for h in hosts:
            try:
                await AgentClientManager.set_client(h)
                logging.info(f"{h.id}.{h.name}: agent client loaded")
            except Exception:
                logging.exception(
                    f"{h.name}: failed to load agent client"
                )


class AgentClientManager:
    """Manager of multiple agents"""

    _INSTANCE = None
    _HOST_CLIENTS: dict[int, AgentClient] = {}

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    @classmethod
    async def set_client(cls, host: HostsModel):
        await cls.remove_client(host.id)
        cls._HOST_CLIENTS[host.id] = cls._create_client(host)

    @classmethod
    def get_host_client(cls, host: HostsModel) -> AgentClient:
        if host.id in cls._HOST_CLIENTS:
            return cls._HOST_CLIENTS[host.id]
        client = cls._create_client(host)
        cls._HOST_CLIENTS[host.id] = client
        return client

    @classmethod
    def _create_client(cls, host: HostsModel) -> AgentClient:
        info = HostInfo.model_validate(host)
        allowed_keys = signature(AgentClient.__init__).parameters
        filtered = {
            k: v
            for k, v in info.model_dump(exclude_unset=True).items()
            if k in allowed_keys and v != None
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
    async def remove_client(cls, id: int):
        client = cls._HOST_CLIENTS.pop(id, None)
        if client:
            await client.close_session()

    @classmethod
    async def remove_all(cls):
        for client in cls._HOST_CLIENTS.values():
            await client.close_session()
        cls._HOST_CLIENTS.clear()
