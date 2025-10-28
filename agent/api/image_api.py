from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from agent.auth import verify_signature
from agent.docker_client import DOCKER
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from agent.unil.asyncall import asyncall
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

router = APIRouter(
    prefix="/image",
    tags=["image"],
    dependencies=[Depends(verify_signature)],
)


async def is_exists(spec_or_id: str) -> Literal[True]:
    exists = await asyncall(lambda: DOCKER.image.exists(spec_or_id))
    if not exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Image not found"
        )
    return True


@router.get(
    "/inspect",
    description="Inspect image",
    response_model=ImageInspectResult,
)
async def inspect(body: InspectImageRequestBodySchema):
    _ = await is_exists(body.spec_or_id)
    return await asyncall(
        lambda: DOCKER.image.inspect(body.spec_or_id)
    )


@router.post(
    "/list",
    description="Get list of images",
    response_model=list[ImageInspectResult],
)
async def list(body: GetImageListBodySchema):
    args = body.model_dump(exclude_unset=True)
    return await asyncall(lambda: DOCKER.image.list(**args))


@router.post(
    "/prune",
    description="Prune volumes",
)
async def prune(body: PruneImagesRequestBodySchema) -> str:
    args = body.model_dump(exclude_unset=True)
    return await asyncall(lambda: DOCKER.image.prune(**args))


@router.post(
    "/pull",
    description="Pull the image",
    response_model=ImageInspectResult,
)
async def pull(body: PullImageRequestBodySchema):
    return await asyncall(lambda: DOCKER.image.pull(body.image))


@router.post(
    "/tag",
    description="Tag image",
)
async def tag(body: TagImageRequestBodySchema):
    _ = await is_exists(body.spec_or_id)
    return await asyncall(
        lambda: DOCKER.image.tag(body.spec_or_id, body.tag)
    )
