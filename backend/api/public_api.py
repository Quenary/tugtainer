from typing import Any
import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from packaging import version
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_async_session
from backend.schemas.is_update_available_schema import (
    IsUpdateAvailableResponseBodySchema,
)
from backend.schemas.version_schema import VersionResponseBody
from backend.core.cron_manager import CronManager
from backend.enums.cron_jobs_enum import ECronJob


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
    "/is_update_available",
    description="Is update of the Tugtainer available",
    response_model=IsUpdateAvailableResponseBodySchema,
)
async def is_update_available():
    url = "https://api.github.com/repos/quenary/tugtainer/releases/latest"
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(15)
    ) as session:
        async with session.request(
            "GET",
            url,
        ) as res:
            res.raise_for_status()
            data: dict[str, Any] = await res.json()
            remote_version = data.get("tag_name", "")
            release_url = data.get("html_url", "")
    with open("/app/version", "r") as file:
        local_version = file.readline()
    is_available = version.parse(remote_version) > version.parse(
        local_version
    )
    return {
        "is_available": is_available,
        "release_url": release_url,
    }
