from typing import cast
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.check_actions.check_all_containers import (
    check_all_containers,
)
from backend.core.cron_manager import CronManager
from backend.core.notifications_core import send_check_notification
from backend.core.update_actions.update_all_containers import (
    update_all_containers,
)
from backend.db.session import get_async_session
from backend.enums.cron_jobs_enum import ECronJob
from backend.exception import TugNotificationException
from backend.modules.auth.auth_util import is_authorized

from .settings_constants import TEST_NOTIFICATION_RESULTS
from .settings_enum import ESettingKey
from .settings_model import SettingModel
from .settings_schemas import (
    SettingsGetResponseItem,
    SettingsPatchRequestItem,
    TestNotificationRequestBody,
)
from .settings_storage import SettingsStorage
from .settings_util import (
    get_setting_typed_value,
    split_notification_urls,
    validate_notification_urls_against_ssrf,
)

VALID_TIMEZONES = available_timezones()

settings_router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(is_authorized)],
)


@settings_router.get("/list", response_model=list[SettingsGetResponseItem])
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


@settings_router.patch("/change")
async def change_system_settings(
    data: list[SettingsPatchRequestItem],
    session: AsyncSession = Depends(get_async_session),
):
    for s in data:
        stmt = select(SettingModel).where(SettingModel.key == s.key).limit(1)
        result = await session.execute(stmt)
        setting = result.scalar_one_or_none()
        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting '{s.key}' not found")
        if setting.value_type != type(s.value).__name__:
            raise HTTPException(
                400,
                f"Invalid type of '{s.key}', expected '{setting.value_type}'",
            )

        if s.key == ESettingKey.NOTIFICATION_URLS:
            await validate_notification_urls_against_ssrf(cast(str, s.value))

        setting.value = str(s.value)

    await session.commit()

    def _get(key: ESettingKey) -> str:
        return next(
            (str(item.value) for item in data if item.key == key and item.value),
            cast(str, SettingsStorage.get(key)),
        )

    check_cron_item = _get(ESettingKey.CHECK_CRONTAB_EXPR)
    update_cron_item = _get(ESettingKey.UPDATE_CRONTAB_EXPR)
    tz = _get(ESettingKey.TIMEZONE)
    CronManager.schedule_job(
        ECronJob.CHECK_CONTAINERS,
        check_cron_item,
        tz,
        check_all_containers,
    )
    CronManager.schedule_job(
        ECronJob.UPDATE_CONTAINERS,
        update_cron_item,
        tz,
        update_all_containers,
    )

    return {"status": "updated", "count": len(data)}


@settings_router.post(
    "/test_notification",
    status_code=200,
    description="Send test notification to specified url",
)
async def test_notification(data: TestNotificationRequestBody):
    if not split_notification_urls(data.urls):
        raise HTTPException(400, "Failed to send notification. URLs is undefined.")

    await validate_notification_urls_against_ssrf(data.urls)

    try:
        await send_check_notification(
            TEST_NOTIFICATION_RESULTS,
            title_template=data.title_template,
            body_template=data.body_template,
            urls=data.urls,
        )
        return {}
    except TugNotificationException as e:
        raise HTTPException(500, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Unknown error: {e}") from e


@settings_router.get(
    "/available_timezones",
    status_code=200,
    description="Get available timezones list",
    response_model=set[str],
)
def get_available_timezones() -> set[str]:
    return VALID_TIMEZONES
