from zoneinfo import available_timezones
from apprise.exception import AppriseException
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_core import is_authorized
from app.db.session import get_async_session
from app.db.models import SettingModel
from app.db.util import get_setting_typed_value
from app.schemas.settings_schema import (
    SettingsGetResponseItem,
    SettingsPatchRequestItem,
    TestNotificationRequestBody,
)
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
            "Tugtainer", "This is test notification", data.url
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



