from zoneinfo import available_timezones
from apprise.exception import AppriseException
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config import Config
from backend.core.auth_core import is_authorized
from backend.db.session import get_async_session
from backend.db.models import SettingModel
from backend.db.util import get_setting_typed_value
from backend.schemas.settings_schema import (
    SettingsGetResponseItem,
    SettingsPatchRequestItem,
    TestNotificationRequestBody,
)
from app.core.auth_core import fetch_oidc_discovery
from app.core.notifications_core import send_notification
from app.core.cron_manager import CronManager
from app.enums.settings_enum import ESettingKey
from app.enums.cron_jobs_enum import ECronJob
from app.core.containers_core import check_all
from app.exception import TugException

VALID_TIMEZONES = available_timezones()

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(is_authorized)],
)


@router.get("/list", response_model=list[SettingsGetResponseItem])
async def get_settings(
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(SettingModel)
    result = await session.execute(stmt)
    settings = result.scalars()
    res: list[SettingsGetResponseItem] = []
    for s in settings:
        val = get_setting_typed_value(s.value, s.value_type)
        item = SettingsGetResponseItem(
            key=s.key,
            value=val,
            value_type=s.value_type,
            modified_at=s.modified_at,
        )
        res.append(item)

    return res


@router.patch("/change")
async def change_system_settings(
    data: list[SettingsPatchRequestItem],
    session: AsyncSession = Depends(get_async_session),
):
    for s in data:
        stmt = (
            select(SettingModel)
            .where(SettingModel.key == s.key)
            .limit(1)
        )
        result = await session.execute(stmt)
        setting = result.scalar_one_or_none()
        if not setting:
            raise HTTPException(
                status_code=404, detail=f"Setting '{s.key}' not found"
            )
        if setting.value_type != type(s.value).__name__:
            raise HTTPException(
                400,
                f"Invalid type of '{s.key}', expected '{setting.value_type}'",
            )

        setting.value = str(s.value)

    await session.commit()

    # Only reschedule cron job if CRONTAB_EXPR or TIMEZONE were updated
    cron_expr_items = [
        item for item in data if item.key == ESettingKey.CRONTAB_EXPR
    ]
    timezone_items = [
        item for item in data if item.key == ESettingKey.TIMEZONE
    ]

    if cron_expr_items or timezone_items:
        cron_expr = cron_expr_items[0] if cron_expr_items else None
        timezone = timezone_items[0] if timezone_items else None
        
        # Get current values if not provided in the update
        if not cron_expr:
            stmt = select(SettingModel).where(SettingModel.key == ESettingKey.CRONTAB_EXPR).limit(1)
            result = await session.execute(stmt)
            cron_setting = result.scalar_one_or_none()
            if cron_setting:
                cron_expr = type('obj', (object,), {'value': cron_setting.value})()
        
        if not timezone:
            stmt = select(SettingModel).where(SettingModel.key == ESettingKey.TIMEZONE).limit(1)
            result = await session.execute(stmt)
            timezone_setting = result.scalar_one_or_none()
            if timezone_setting:
                timezone = type('obj', (object,), {'value': timezone_setting.value})()
        
        if cron_expr and timezone:
            CronManager.schedule_job(
                ECronJob.CHECK_CONTAINERS,
                str(cron_expr.value),
                str(timezone.value),
                lambda: check_all(True),
            )

    return {"status": "updated", "count": len(data)}


@router.post(
    "/test_notification",
    status_code=200,
    description="Send test notification to specified url",
)
async def test_notification(data: TestNotificationRequestBody):
    try:
        await send_notification(
            body=f"""
# Tugtainer ({Config.HOSTNAME})

This is test notification
            """,
            url=data.url,
        )
        return {}
    except (TugException, AppriseException) as e:
        raise HTTPException(500, str(e))


@router.get(
    "/available_timezones",
    status_code=200,
    description="Get available timezones list",
    response_model=set[str],
)
def get_available_timezones() -> set[str]:
    return VALID_TIMEZONES


@router.post(
    "/test_oidc",
    status_code=200,
    description="Test OIDC well-known URL connectivity",
)
async def test_oidc_connection(data: dict):
    """Test if the OIDC well-known URL is accessible and returns valid configuration"""
    well_known_url = data.get("well_known_url")
    if not well_known_url:
        raise HTTPException(400, "well_known_url is required")
    
    try:
        discovery_doc = await fetch_oidc_discovery(well_known_url)
        
        # Check if required endpoints exist
        required_endpoints = ["authorization_endpoint", "token_endpoint"]
        missing_endpoints = [ep for ep in required_endpoints if ep not in discovery_doc]
        
        if missing_endpoints:
            raise HTTPException(
                400, 
                f"OIDC discovery document is missing required endpoints: {missing_endpoints}"
            )
        
        return {
            "status": "success",
            "message": "OIDC configuration is valid",
            "endpoints": {
                "authorization_endpoint": discovery_doc.get("authorization_endpoint"),
                "token_endpoint": discovery_doc.get("token_endpoint"),
                "userinfo_endpoint": discovery_doc.get("userinfo_endpoint"),
                "issuer": discovery_doc.get("issuer")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error testing OIDC connection: {str(e)}")
