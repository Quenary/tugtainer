from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_session
from backend.app.schemas.version_schema import VersionResponseBody
from backend.app.core.cron_manager import CronManager
from backend.app.enums.cron_jobs_enum import ECronJob


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
