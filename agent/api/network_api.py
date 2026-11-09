from typing import Any

from fastapi import APIRouter, Depends

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.schemas.network_schemas import (
    NetworkConnectBodySchema,
    NetworkDisconnectBodySchema,
)

router = APIRouter(
    prefix="/network",
    tags=["network"],
    dependencies=[Depends(verify_signature)],
)


@router.post(
    "/connect",
    description="Connect container to network",
)
async def connect(body: NetworkConnectBodySchema) -> None:
    endpoint_config: dict[str, Any] = {}
    ipam: dict[str, Any] = {}
    if body.ipv4_address:
        ipam["IPv4Address"] = body.ipv4_address
    if body.ipv6_address:
        ipam["IPv6Address"] = body.ipv6_address
    if ipam:
        endpoint_config["IPAMConfig"] = ipam
    if body.aliases:
        endpoint_config["Aliases"] = body.aliases
    if body.links:
        endpoint_config["Links"] = body.links
    if body.mac_address:
        endpoint_config["MacAddress"] = body.mac_address
    if body.gateway_priority is not None:
        endpoint_config["GatewayPriority"] = body.gateway_priority

    await RUNTIME_CLIENT.network_connect(
        network_id=body.network,
        container_id=body.container,
        endpoint_config=endpoint_config or None,
    )


@router.post(
    "/disconnect",
    description="Disconnect container from network",
)
async def disconnect(body: NetworkDisconnectBodySchema) -> None:
    await RUNTIME_CLIENT.network_disconnect(
        network_id=body.network,
        container_id=body.container,
        force=body.force or False,
    )
