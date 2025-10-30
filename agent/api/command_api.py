from fastapi import APIRouter, Depends
from python_on_whales.utils import run as docker_run_cmd
from agent.auth import verify_signature
from agent.docker_client import DOCKER
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from agent.unil.asyncall import asyncall

router = APIRouter(
    prefix="/command",
    tags=["command"],
    dependencies=[Depends(verify_signature)],
)


@router.post(
    "/run",
    description="Run arbitrary docker command",
    response_model=tuple[str, str],
)
async def run(body: RunCommandRequestBodySchema) -> tuple[str, str]:
    _command = DOCKER.config.docker_cmd + body.command
    return await asyncall(
        lambda: docker_run_cmd(_command),
        asyncall_timeout=600,
    )
