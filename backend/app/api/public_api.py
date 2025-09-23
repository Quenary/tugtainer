from fastapi import APIRouter, Depends, HTTPException
import os
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from app.db.session import get_async_session
from app.schemas.version_schema import VersionResponseBody
from app.helpers import get_setting_typed_value


router = APIRouter(tags=["public"], prefix="/public")


@router.get("/version", response_model=VersionResponseBody)
def get_version():
    image_version = os.getenv("VERSION") or None
    return {"image_version": image_version}


@router.get("/health")
async def health(session: AsyncSession = Depends(get_async_session)):
    try:
        await session.execute(text("SELECT 1"))
        return "OK"
    except Exception:
        raise HTTPException(503, "db_error")
