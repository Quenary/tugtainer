import logging

from fastapi import APIRouter, Depends, HTTPException, status

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.runtime import RuntimeError

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/health", description="Get health status of the agent")
async def health():
    try:
        ok = await RUNTIME_CLIENT.ping()
        if not ok:
            raise RuntimeError("Runtime ping returned false")
        return "OK"
    except (RuntimeError, Exception) as e:
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
