from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status

from agent.auth import verify_signature
from agent.config import Config
from agent.docker_client import RUNTIME_CLIENT
from shared.runtime.runtime_models import (
    ContainerInspectResult,
)
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
    ExecContainerRequestBodySchema,
    GetContainerListBodySchema,
    GetContainerLogsRequestBody,
)

router = APIRouter(
    prefix="/container",
    tags=["container"],
    dependencies=[Depends(verify_signature)],
)


async def is_exists(name_or_id: str) -> Literal[True]:
    exists = await RUNTIME_CLIENT.container_exists(name_or_id)
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Container not found")
    return True


@router.post(
    "/list",
    description="Get list of all containers",
    response_model=list[ContainerInspectResult],
)
async def list_containers(body: GetContainerListBodySchema):
    args = body.model_dump(exclude_unset=True)
    return await RUNTIME_CLIENT.container_list(**args)


@router.get(
    "/exists/{name_or_id}",
    description="Check if a container exists on the host",
    response_model=bool,
)
async def exists(name_or_id: str) -> bool:
    return await RUNTIME_CLIENT.container_exists(name_or_id)


@router.get(
    "/inspect/{name_or_id}",
    description="Get container inspect data",
    response_model=ContainerInspectResult,
)
async def inspect(name_or_id: str, _=Depends(is_exists)):
    return await RUNTIME_CLIENT.container_inspect(name_or_id)


@router.post(
    "/create",
    description="Create container",
    response_model=ContainerInspectResult,
)
async def create(body: CreateContainerRequestBodySchema):
    return await RUNTIME_CLIENT.container_create(body)


@router.post(
    "/start/{name_or_id}",
    description="Start container",
    response_model=str,
)
async def start(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_start(name_or_id)
    return name_or_id


@router.post(
    "/stop/{name_or_id}",
    description="Stop container",
    response_model=str,
)
async def stop(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_stop(name_or_id)
    return name_or_id


@router.post(
    "/restart/{name_or_id}",
    description="Restart container",
    response_model=str,
)
async def restart(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_restart(name_or_id)
    return name_or_id


@router.post(
    "/kill/{name_or_id}",
    description="Kill container",
    response_model=str,
)
async def kill(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_kill(name_or_id)
    return name_or_id


@router.post(
    "/pause/{name_or_id}",
    description="Pause container",
    response_model=str,
)
async def pause(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_pause(name_or_id)
    return name_or_id


@router.post(
    "/unpause/{name_or_id}",
    description="Unpause container",
    response_model=str,
)
async def unpause(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_unpause(name_or_id)
    return name_or_id


@router.post(
    "/rename/{name_or_id}",
    description="Rename container",
    response_model=str,
)
async def rename(name_or_id: str, new_name: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_rename(name_or_id, new_name)
    return new_name


@router.delete(
    "/remove/{name_or_id}",
    description="Remove container",
    response_model=str,
)
async def remove(name_or_id: str, _=Depends(is_exists)) -> str:
    await RUNTIME_CLIENT.container_remove(name_or_id, force=True)
    return name_or_id


@router.post(
    path="/logs/{name_or_id}",
    description="Get log of container",
    response_model=str,
)
async def logs(
    name_or_id: str,
    body: GetContainerLogsRequestBody,
    _=Depends(is_exists),
) -> str:
    return await RUNTIME_CLIENT.container_logs(
        name_or_id, **body.model_dump(exclude_unset=True)
    )


@router.post(
    "/exec/{name_or_id}",
    description="Execute a shell command inside a running container. "
    "Disabled unless ALLOW_EXEC=true on this agent.",
    response_model=str,
)
async def exec_command(
    name_or_id: str,
    body: ExecContainerRequestBodySchema,
    _=Depends(is_exists),
) -> str:
    if not Config.ALLOW_EXEC:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Command execution inside containers is disabled on this agent. "
            "Set ALLOW_EXEC=true to enable it.",
        )
    return await RUNTIME_CLIENT.container_exec(
        name_or_id,
        ["sh", "-c", body.command],
    )
