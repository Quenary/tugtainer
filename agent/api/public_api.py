import logging

from fastapi import APIRouter, Depends, HTTPException, status

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.agent_protocol import AGENT_PROTOCOL, AgentProtocol, read_installed_version
from shared.runtime import RuntimeEngineError

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/health", description="Get health status of the agent")
async def health():
    try:
        ok = await RUNTIME_CLIENT.ping()
        if not ok:
            raise RuntimeEngineError("Runtime ping returned false")
        return "OK"
    except Exception as e:
        message = "Failed to connect to container runtime"
        logging.exception(message)
        raise HTTPException(
            status.HTTP_424_FAILED_DEPENDENCY,
            message,
        ) from e


@router.get(
    "/access",
    description="Get signature verification. Raises exception on falsy signature.",
)
async def access(_=Depends(verify_signature)):
    return "OK"


@router.get(
    "/version",
    description="Agent build version and API protocol major.",
    response_model=AgentProtocol,
)
async def version(_=Depends(verify_signature)) -> AgentProtocol:
    return AgentProtocol(
        version=read_installed_version(),
        protocol=AGENT_PROTOCOL,
    )
