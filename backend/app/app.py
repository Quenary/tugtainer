import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from python_on_whales import DockerException
from app.core import schedule_check_on_init, load_hosts_on_init
from app.api import (
    auth_router,
    containers_router,
    public_router,
    settings_router,
    images_router,
    hosts_router,
)
from app.config import Config
import logging
from app.helpers.settings_storage import SettingsStorage

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class EndpointFilter(logging.Filter):
    def __init__(self):
        self.excluded_endpoints = [
            "/api/containers/progress",
            "/health",
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(
            endpoint in message
            for endpoint in self.excluded_endpoints
        )


uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(Config.LOG_LEVEL)
uvicorn_logger.addFilter(EndpointFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    await load_hosts_on_init()
    await schedule_check_on_init()
    await SettingsStorage.load_all()
    yield  # App
    # Code to run on shutdown


app = FastAPI(root_path="/api", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(containers_router)
app.include_router(public_router)
app.include_router(settings_router)
app.include_router(images_router)
app.include_router(hosts_router)


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
    raise HTTPException(424, exc.stdout)
