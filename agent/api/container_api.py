from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from agent.auth import verify_signature
from agent.docker_client import DOCKER
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
    CreateContainerRequestBodySchema,
)
from agent.unil.asyncall import asyncall

router = APIRouter(
    prefix="/container",
    tags=["container"],
    dependencies=[Depends(verify_signature)],
)


async def is_exists(name_or_id: str) -> Literal[True]:
    exists = await asyncall(
        lambda: DOCKER.container.exists(name_or_id)
    )
    if not exists:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Container not found"
        )
    return True


@router.post(
    "/list",
    description="Get list of all containers",
    response_model=list[ContainerInspectResult],
)
async def list(body: GetContainerListBodySchema):
    args = body.model_dump(exclude_unset=True)
    return await asyncall(lambda: DOCKER.container.list(**args))


@router.get(
    "/exists/{name_or_id}",
    description="Check if a container exists on the host",
    response_model=bool,
)
async def exists(name_or_id: str) -> bool:
    return await asyncall(lambda: DOCKER.container.exists(name_or_id))


@router.get(
    "/inspect/{name_or_id}",
    description="Get container inspect data",
    response_model=ContainerInspectResult,
)
async def inspect(name_or_id: str, _=Depends(is_exists)):
    return await asyncall(
        lambda: DOCKER.container.inspect(name_or_id)
    )


@router.post(
    "/create",
    description="Create container",
    response_model=ContainerInspectResult,
)
async def create(body: CreateContainerRequestBodySchema):
    args = body.model_dump(exclude_unset=True)
    return await asyncall(
        lambda: DOCKER.container.create(**args), asyncall_timeout=600
    )


@router.post(
    "/start/{name_or_id}",
    description="Start container",
    response_model=str,
)
async def start(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.start(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id


@router.post(
    "/stop/{name_or_id}",
    description="Stop container",
    response_model=str,
)
async def stop(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.stop(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id

@router.post(
    "/restart/{name_or_id}",
    description="Restart container",
    response_model=str,
)
async def restart(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.restart(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id


@router.post(
    "/kill/{name_or_id}",
    description="Kill container",
    response_model=str,
)
async def kill(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.kill(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id

@router.post(
    "/pause/{name_or_id}",
    description="Pause container",
    response_model=str,
)
async def pause(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.pause(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id


@router.post(
    "/unpause/{name_or_id}",
    description="Unpause container",
    response_model=str,
)
async def unpause(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.unpause(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id


@router.delete(
    "/remove/{name_or_id}",
    description="Remove container",
    response_model=str,
)
async def remove(name_or_id: str, _=Depends(is_exists)) -> str:
    __ = await asyncall(
        lambda: DOCKER.container.remove(name_or_id),
        asyncall_timeout=600,
    )
    return name_or_id
