from fastapi import APIRouter, Depends
from pydantic import TypeAdapter
from python_on_whales.utils import run as docker_run_cmd

from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
from shared.schemas.command_schemas import RunCommandRequestBodySchema

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
    res = await asyncall(
        lambda: docker_run_cmd(_command),
        asyncall_timeout=600,
    )
    # although typing says that res should be a tuple,
    # it might not be (success network connect returns empty string)
    if not res:
        return ("", "")
    if isinstance(res, str):
        return (res, "")
    try:
        return TypeAdapter(tuple[str, str]).validate_python(res)
    except Exception:
        return (str(res), "")
