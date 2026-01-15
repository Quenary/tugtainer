from python_on_whales.components.buildx.imagetools.models import (
    Manifest,
)
from fastapi import APIRouter, Depends
from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
from shared.schemas.image_schemas import InspectImageRequestBodySchema

router = APIRouter(
    prefix="/buildx",
    tags=["buildx"],
    dependencies=[Depends(verify_signature)],
)


@router.get(
    path="/imagetools/inspect",
    description="Inspect remote image",
    response_model=Manifest,
)
async def imagetools_inspect(
    body: InspectImageRequestBodySchema,
) -> Manifest:
    return await asyncall(
        lambda: DOCKER.buildx.imagetools.inspect(body.spec_or_id)
    )
