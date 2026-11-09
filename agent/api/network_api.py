from fastapi import APIRouter, Depends

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.runtime.endpoint_settings import endpoint_config_from_connect
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
    api_version = None
    if body.gateway_priority is not None:
        if not RUNTIME_CLIENT._negotiated_api_prefix:
            await RUNTIME_CLIENT.get_version()
        api_version = RUNTIME_CLIENT._negotiated_api_prefix.removeprefix("/v")
    await RUNTIME_CLIENT.network_connect(
        network_id=body.network,
        container_id=body.container,
        endpoint_config=endpoint_config_from_connect(body, api_version),
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
