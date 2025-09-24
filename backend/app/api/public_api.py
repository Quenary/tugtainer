from fastapi import APIRouter, Depends, HTTPException
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from app.db.session import get_async_session
from app.schemas.version_schema import VersionResponseBody
from app.core.cron_manager import CronManager
from app.enums.cron_jobs_enum import ECronJob


router = APIRouter(tags=["public"], prefix="/public")


@router.get("/version", response_model=VersionResponseBody)
def get_version():
    image_version = os.getenv("VERSION") or None
    return {"image_version": image_version}


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
