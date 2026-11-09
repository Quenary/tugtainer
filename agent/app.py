import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status

from agent.api import (
    common_router,
    container_router,
    image_router,
    network_router,
    public_router,
    service_router,
)
from agent.config import Config
from agent.docker_client import RUNTIME_CLIENT
from shared.runtime import (
    RuntimeClientError,
    RuntimeConflictError,
    RuntimeError,
    RuntimeNotFoundError,
)
from shared.util.endpoint_logging_filter import EndpointLoggingFilter

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="AGENT - %(levelname)s - %(name)s: %(message)s",
    force=True,
)

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(Config.LOG_LEVEL)
uvicorn_logger.addFilter(EndpointLoggingFilter(["/public/health"]))


def warn_if_agent_secret_missing() -> None:
    """Warn when the agent will reject requests because no secret is configured."""
    if Config.AGENT_SECRET or Config.ALLOW_UNAUTHENTICATED_AGENT:
        return
    logging.warning(
        "AGENT_SECRET is not set. Requests to this agent will be rejected. "
        "Set AGENT_SECRET, or set ALLOW_UNAUTHENTICATED_AGENT=true for development."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_if_agent_secret_missing()
    try:
        yield
    finally:
        await RUNTIME_CLIENT.close()


app = FastAPI(root_path="/api", lifespan=lifespan)
app.include_router(public_router)
app.include_router(container_router)
app.include_router(image_router)
app.include_router(network_router)
app.include_router(common_router)
app.include_router(service_router)


@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    raise HTTPException(
        500,
        "Timeout error. The problem is most likely related to connecting to the docker host.",
    )


@app.exception_handler(RuntimeNotFoundError)
async def runtime_not_found_handler(
    request: Request,
    exc: RuntimeNotFoundError,
):
    raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@app.exception_handler(RuntimeConflictError)
async def runtime_conflict_handler(
    request: Request,
    exc: RuntimeConflictError,
):
    raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@app.exception_handler(RuntimeClientError)
@app.exception_handler(RuntimeError)
async def runtime_exception_handler(
    request: Request,
    exc: RuntimeError,
):
    raise HTTPException(status.HTTP_424_FAILED_DEPENDENCY, f"Runtime Exception: {exc}")
