from typing import Any, Protocol

from shared.runtime.runtime_client import RuntimeClient
from shared.runtime.runtime_models import ContainerInspectResult
from shared.schemas.container_schemas import CreateContainerRequestBodySchema
from shared.schemas.network_schemas import NetworkConnectBodySchema


class SelfUpdateDocker(Protocol):
    """Plain runtime operations used by the self-update helper."""

    async def inspect(self, name_or_id: str) -> ContainerInspectResult: ...

    async def exists(self, name_or_id: str) -> bool: ...

    async def image_exists(self, image_id: str) -> bool: ...

    async def rename(self, name_or_id: str, new_name: str) -> None: ...

    async def create(self, body: CreateContainerRequestBodySchema) -> str: ...

    async def start(self, name_or_id: str) -> None: ...

    async def stop(self, name_or_id: str) -> None: ...

    async def remove(self, name_or_id: str) -> None: ...

    async def network_connect(
        self,
        network: str,
        container_id: str,
        connect_body: NetworkConnectBodySchema | None = None,
    ) -> None: ...

    async def close(self) -> None: ...


class HttpSelfUpdateDocker:
    """
    SelfUpdateDocker backed by direct async RuntimeClient over socket or TCP proxy.
    """

    def __init__(self, client: RuntimeClient | None = None):
        self._client = client or RuntimeClient()

    async def inspect(self, name_or_id: str) -> ContainerInspectResult:
        return await self._client.container_inspect(name_or_id)

    async def exists(self, name_or_id: str) -> bool:
        return await self._client.container_exists(name_or_id)

    async def image_exists(self, image_id: str) -> bool:
        return await self._client.image_exists(image_id)

    async def rename(self, name_or_id: str, new_name: str) -> None:
        await self._client.container_rename(name_or_id, new_name)

    async def create(self, body: CreateContainerRequestBodySchema) -> str:
        container = await self._client.container_create(
            payload=body,
            name=body.name,
        )
        return str(container.id or "")

    async def start(self, name_or_id: str) -> None:
        await self._client.container_start(name_or_id)

    async def stop(self, name_or_id: str) -> None:
        await self._client.container_stop(name_or_id)

    async def remove(self, name_or_id: str) -> None:
        await self._client.container_remove(name_or_id, force=True)

    async def network_connect(
        self,
        network: str,
        container_id: str,
        connect_body: NetworkConnectBodySchema | None = None,
    ) -> None:
        endpoint_config: dict[str, Any] = {}
        ipam: dict[str, Any] = {}
        if connect_body:
            if connect_body.ipv4_address:
                ipam["IPv4Address"] = connect_body.ipv4_address
            if connect_body.ipv6_address:
                ipam["IPv6Address"] = connect_body.ipv6_address
            if ipam:
                endpoint_config["IPAMConfig"] = ipam
            if connect_body.aliases:
                endpoint_config["Aliases"] = connect_body.aliases
            if connect_body.links:
                endpoint_config["Links"] = connect_body.links
            if connect_body.mac_address:
                endpoint_config["MacAddress"] = connect_body.mac_address
            if connect_body.gateway_priority is not None:
                endpoint_config["GatewayPriority"] = connect_body.gateway_priority

        await self._client.network_connect(
            network_id=network,
            container_id=container_id,
            endpoint_config=endpoint_config or None,
        )

    async def close(self) -> None:
        await self._client.close()
