from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core import schedule_check_on_init, load_hosts_on_init
from app.api import (
    auth_router,
    containers_router,
    public_router,
    settings_router,
    images_router,
    host_router,
)
from app.config import Config
import logging

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format="%(levelname)s %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    await load_hosts_on_init()
    await schedule_check_on_init()
    yield  # App
    # Code to run on shutdown


app = FastAPI(root_path="/api", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(containers_router)
app.include_router(public_router)
app.include_router(settings_router)
app.include_router(images_router)
app.include_router(host_router)
