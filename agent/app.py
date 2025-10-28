import asyncio
import logging
from fastapi import FastAPI, HTTPException, Request, status
from python_on_whales import DockerException
from agent.api import (
    public_router,
    container_router,
    image_router,
    command_router,
)
from agent.config import Config
from shared.util.endpoint_logging_filter import EndpointLoggingFilter

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(Config.LOG_LEVEL)
uvicorn_logger.addFilter(EndpointLoggingFilter(["/public/health"]))

app = FastAPI(root_path="/api")
app.include_router(public_router)
app.include_router(container_router)
app.include_router(image_router)
app.include_router(command_router)


@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(
    request: Request, exc: asyncio.TimeoutError
):
    raise HTTPException(
        500,
        "Timeout error. The problem is most likely related to connecting to the docker host.",
    )


@app.exception_handler(DockerException)
async def docker_exception_handler(
    request: Request,
    exc: DockerException,
):
    detail = "Docker Exception"
    if exc.stdout:
        detail += f"\nstdout: {exc.stdout}"
    if exc.stderr:
        detail += f"\nstderr: {exc.stderr}"
    raise HTTPException(status.HTTP_424_FAILED_DEPENDENCY, detail)
