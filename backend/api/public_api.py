from typing import Any
import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from packaging import version
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_async_session
from backend.schemas.is_update_available_schema import (
    IsUpdateAvailableResponseBodySchema,
)
from backend.schemas.version_schema import VersionResponseBody
from backend.core.cron_manager import CronManager
from backend.enums.cron_jobs_enum import ECronJob
from backend.schemas import HostSummary
from backend.db.models import HostsModel, ContainersModel
from backend.core import HostsManager
from backend.api.util import map_container_schema
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from backend.config import Config


router = APIRouter(tags=["public"], prefix="/public")


@router.get("/version", response_model=VersionResponseBody)
def get_version():
    try:
        with open("/app/version", "r") as file:
            return {"image_version": file.readline()}
    except FileNotFoundError:
        raise HTTPException(404, "Version file not found")


@router.get("/health")
async def health(session: AsyncSession = Depends(get_async_session)):
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(503, f"Database error {e}")
    cron_jobs = CronManager.get_jobs()
    if ECronJob.CHECK_CONTAINERS not in cron_jobs:
        raise HTTPException(500, "Main cron job not running")
    return "OK"


@router.get(
    path="/summary",
    description="Get summary statistics for all hosts",
    response_model=list[HostSummary],
)
async def get_summary(
    session: AsyncSession = Depends(get_async_session),
) -> list[HostSummary]:
    if not Config.ENABLE_PUBLIC_API:
        raise HTTPException(404, "Not Found")

    stmt = select(HostsModel)
    result = await session.execute(stmt)
    hosts = result.scalars().all()

    summaries = []
    for host in hosts:
        if not host.enabled:
            summaries.append(
                HostSummary(
                    host_id=host.id,
                    host_name=host.name,
                    total_containers=0,
                    by_status={},
                    by_health={},
                    by_protected={"true": 0, "false": 0},
                    by_check_enabled={"true": 0, "false": 0},
                    by_update_enabled={"true": 0, "false": 0},
                    by_update_available={"true": 0, "false": 0},
                )
            )
            continue

        client = HostsManager.get_host_client(host)
        containers = await client.container.list(
            GetContainerListBodySchema(all=True)
        )

        db_result = await session.execute(
            select(ContainersModel).where(
                ContainersModel.host_id == host.id
            )
        )
        containers_db = db_result.scalars().all()

        mapped_containers = []
        for c in containers:
            db_item = next(
                (
                    item
                    for item in containers_db
                    if item.name == c.name
                ),
                None,
            )
            mapped_containers.append(
                map_container_schema(host.id, c, db_item)
            )

        by_status = {
            "created": 0,
            "running": 0,
            "paused": 0,
            "restarting": 0,
            "removing": 0,
            "exited": 0,
            "dead": 0,
        }
        by_health = {
            "unknown": 0,
            "healthy": 0,
            "unhealthy": 0,
            "starting": 0,
        }
        by_protected = {"true": 0, "false": 0}
        by_check_enabled = {"true": 0, "false": 0}
        by_update_enabled = {"true": 0, "false": 0}
        by_update_available = {"true": 0, "false": 0}

        for container in mapped_containers:
            if container.status:
                by_status[container.status] = (
                    by_status.get(container.status, 0) + 1
                )

            health_key = container.health or "none"
            by_health[health_key] = by_health.get(health_key, 0) + 1

            protected_key = "true" if container.protected else "false"
            by_protected[protected_key] += 1

            if container.check_enabled is not None:
                check_key = (
                    "true" if container.check_enabled else "false"
                )
                by_check_enabled[check_key] += 1

            if container.update_enabled is not None:
                update_key = (
                    "true" if container.update_enabled else "false"
                )
                by_update_enabled[update_key] += 1

            if container.update_available is not None:
                avail_key = (
                    "true" if container.update_available else "false"
                )
                by_update_available[avail_key] += 1

        summaries.append(
            HostSummary(
                host_id=host.id,
                host_name=host.name,
                total_containers=len(mapped_containers),
                by_status=by_status,
                by_health=by_health,
                by_protected=by_protected,
                by_check_enabled=by_check_enabled,
                by_update_enabled=by_update_enabled,
                by_update_available=by_update_available,
            )
        )

    return summaries


@router.get(
    "/is_update_available",
    description="Is update of the Tugtainer available",
    response_model=IsUpdateAvailableResponseBodySchema,
)
async def is_update_available():
    try:
        with open("/app/version", "r") as file:
            local_version = file.readline()
    except FileNotFoundError:
        raise HTTPException(404, "Version file not found")
    url = "https://api.github.com/repos/quenary/tugtainer/releases/latest"
    headers: dict[str, str] = {}
    if Config.GH_TOKEN:
        headers["Authorization"] = f"Bearer {Config.GH_TOKEN}"
    async with aiohttp.ClientSession(
        headers=headers, timeout=aiohttp.ClientTimeout(15), trust_env=True
    ) as session:
        async with session.request(
            "GET",
            url,
        ) as res:
            res.raise_for_status()
            data: dict[str, Any] = await res.json()
            remote_version = data.get("tag_name", "")
            release_url = data.get("html_url", "")
    is_available = version.parse(remote_version) > version.parse(
        local_version
    )
    return {
        "is_available": is_available,
        "release_url": release_url,
    }
