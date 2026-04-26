
from fastapi import APIRouter, Depends

from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
from shared.schemas.network_schemas import NetworkDisconnectBodySchema

router = APIRouter(
    prefix="/network",
    tags=["network"],
    dependencies=[Depends(verify_signature)],
)

@router.post(
    "/disconnect",
    description="Disconnect container from network",
)
async def disconnect(
    body: NetworkDisconnectBodySchema,
):
    await asyncall(
        lambda: DOCKER.network.disconnect(
            **body.model_dump(exclude_unset=True)
        )
    )