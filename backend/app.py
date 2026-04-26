import logging
from contextlib import asynccontextmanager

from aiohttp.client_exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request, status

from backend.config import Config
from backend.core.agent_client import (
    AgentClientManager,
    load_agents_on_init,
)
from backend.core.cron_manager import schedule_actions_on_init
from backend.exception import TugAgentClientError
from backend.modules.auth.auth_router import (
    auth_router as auth_router,
)
from backend.modules.containers.containers_router import (
    containers_router as containers_router,
)
from backend.modules.hosts.hosts_router import (
    hosts_router as hosts_router,
)
from backend.modules.images.images_router import (
    images_router as images_router,
)
from backend.modules.public.public_router import (
    public_router as public_router,
)
from backend.modules.settings.settings_router import (
    settings_router as settings_router,
)
from backend.modules.settings.settings_storage import SettingsStorage
from shared.util.endpoint_logging_filter import EndpointLoggingFilter

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="BACKEND - %(levelname)s - %(name)s: %(message)s",
    force=True,
)

uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(Config.LOG_LEVEL)
uvicorn_logger.addFilter(
    EndpointLoggingFilter(
        [
            "/api/containers/progress",
            "/public/health",
        ]
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    await load_agents_on_init()
    await SettingsStorage.load_all()
    await schedule_actions_on_init()
    yield  # App
    # Code to run on shutdown
    await AgentClientManager.remove_all()


app = FastAPI(root_path="/api", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(containers_router)
app.include_router(public_router)
app.include_router(settings_router)
app.include_router(images_router)
app.include_router(hosts_router)


@app.exception_handler(ClientError)
async def aiohttp_exception_handler(request: Request, exc: ClientError):
    message = "Unknown aiohttp error"
    logging.exception(message)
    raise HTTPException(
        status.HTTP_424_FAILED_DEPENDENCY,
        f"{message}\n{str(exc)}",
    )


@app.exception_handler(TugAgentClientError)
async def agent_client_exception_handler(request: Request, exc: TugAgentClientError):
    raise HTTPException(status.HTTP_424_FAILED_DEPENDENCY, str(exc))
