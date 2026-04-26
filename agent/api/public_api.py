import logging

from fastapi import APIRouter, Depends, HTTPException, status
from python_on_whales import DockerException

from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/health", description="Get health status of the agent")
async def health():
    try:
        _ = await asyncall(DOCKER.info)
        return "OK"
    except DockerException as e:
        message = "Failed to get docker cli info"
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
