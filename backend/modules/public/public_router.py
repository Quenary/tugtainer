import asyncio
import logging
from typing import cast

from cachetools import TTLCache
from cachetools_async import cached as cached_async
from fastapi import APIRouter, Depends, HTTPException, Request
from packaging import version
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Config
from backend.core.agent_client import AgentClientManager
from backend.core.cron_manager import CronManager
from backend.db.session import get_async_session
from backend.enums.cron_jobs_enum import ECronJob
from backend.modules.auth.auth_util import is_authorized
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_schemas import HostSummary
from backend.modules.public.public_util import fetch_latest_release, get_host_summary
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)

from .public_schemas import (
    IsUpdateAvailableResponseBodySchema,
    TotalUpdateCountResponseBodySchema,
    VersionResponseBody,
)

public_router = APIRouter(tags=["public"], prefix="/public")


@public_router.get("/version", response_model=VersionResponseBody)
def get_version():
    try:
        with open("/app/version") as file:
            return {"image_version": file.readline()}
    except FileNotFoundError as e:
        raise HTTPException(404, "Version file not found") from e


@public_router.get("/health")
async def health(session: AsyncSession = Depends(get_async_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(503, f"Database error {e}") from e
    cron_jobs = CronManager.get_jobs()
    if ECronJob.CHECK_CONTAINERS not in cron_jobs:
        raise HTTPException(500, "Main cron job not running")
    return "OK"


@public_router.get(
    path="/summary",
    description="Get summary statistics for all hosts",
    response_model=list[HostSummary],
)
async def get_summary(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> list[HostSummary]:
    try:
        await is_authorized(request)
    except Exception:
        if not Config.ENABLE_PUBLIC_API:
            raise HTTPException(403, "Public api disabled") from None

    hosts = (await session.execute(select(HostsModel))).scalars().all()

    return await asyncio.gather(*(get_host_summary(host, session) for host in hosts))


@public_router.get(
    "/update_count",
    description="Get total number of containers with available updates",
    response_model=TotalUpdateCountResponseBodySchema,
)
async def get_update_count(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> TotalUpdateCountResponseBodySchema:
    try:
        await is_authorized(request)
    except Exception:
        if not Config.ENABLE_PUBLIC_API:
            raise HTTPException(403, "Public api disabled") from None

    stmt = select(HostsModel).where(HostsModel.enabled)
    result = await session.execute(stmt)
    hosts = result.scalars().all()

    total_updates = 0
    for host in hosts:
        client = AgentClientManager.get_host_client(host)
        containers = await client.container.list(GetContainerListBodySchema(all=True))
        db_result = await session.execute(
            select(ContainersModel).where(ContainersModel.host_id == host.id)
        )
        containers_db = db_result.scalars().all()
        containers_db_map = {item.name: item for item in containers_db}

        for container in containers:
            db_item = containers_db_map.get(cast(str, container.name))
            if db_item and db_item.update_available:
                total_updates += 1

    return TotalUpdateCountResponseBodySchema.model_validate(
        {"total_updates": total_updates}
    )


@public_router.get(
    "/is_update_available",
    description="Is update of the Tugtainer available",
    response_model=IsUpdateAvailableResponseBodySchema,
)
@cached_async(cache=TTLCache(maxsize=1, ttl=3600))
async def is_update_available():
    try:
        with open("/app/version") as file:
            local_version = file.readline()
    except FileNotFoundError as e:
        raise HTTPException(404, "Version file not found") from e
    try:
        data = await fetch_latest_release()
        remote_version = data.get("tag_name", "")
        release_url = data.get("html_url", "")
    except Exception as e:
        message = "Failed to fetch latest release"
        logging.exception(message)
        raise HTTPException(500, message) from e
    try:
        is_available = version.parse(remote_version) > version.parse(local_version)
    except version.InvalidVersion as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "is_available": is_available,
        "release_url": release_url,
    }
