from fastapi import APIRouter, Depends
from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
from shared.schemas.docker_version_scheme import DockerVersionScheme


router = APIRouter(
    prefix="/common",
    tags=["common"],
    dependencies=[Depends(verify_signature)],
)


@router.get(
    "/version",
    description="Get docker version",
    response_model=DockerVersionScheme,
)
async def get_version():
    return await asyncall(lambda: DOCKER.version())
