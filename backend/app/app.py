from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager
from .api import auth_router
from .config import Config

app = FastAPI(root_path="/api")
app.include_router(auth_router)
