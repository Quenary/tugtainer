from datetime import datetime
from zoneinfo import available_timezones
from apprise.exception import AppriseException
from fastapi import APIRouter, Depends, HTTPException
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
    ContainerState,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.auth.auth_provider_chore import is_authorized
from backend.core.container.schemas.check_result import (
    ContainerCheckResult,
    HostCheckResult,
)
from backend.db.session import get_async_session
from backend.db.models import SettingModel
from backend.db.util import get_setting_typed_value
from backend.helpers.settings_storage import SettingsStorage
from backend.schemas.settings_schema import (
    SettingsGetResponseItem,
    SettingsPatchRequestItem,
    TestNotificationRequestBody,
)
from backend.core.notifications_core import send_check_notification
from backend.core.cron_manager import CronManager
from backend.enums.settings_enum import ESettingKey
from backend.enums.cron_jobs_enum import ECronJob
from backend.core.containers_core import check_all
from backend.exception import TugException
from jinja2.exceptions import TemplateError

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
    cron_expr_item = next(
        (
            item
            for item in data
            if item.key == ESettingKey.CRONTAB_EXPR.value
        ),
        None,
    )
    timezone_item = next(
        (
            item
            for item in data
            if item.key == ESettingKey.TIMEZONE.value
        ),
        None,
    )

    if cron_expr_item or timezone_item:
        # Get current values if not provided in the update
        cron_expr = (
            str(cron_expr_item.value)
            if cron_expr_item
            else SettingsStorage.get(ESettingKey.CRONTAB_EXPR)
        )
        timezone = (
            str(timezone_item.value)
            if timezone_item
            else SettingsStorage.get(ESettingKey.TIMEZONE)
        )

        if cron_expr and timezone:
            CronManager.schedule_job(
                ECronJob.CHECK_CONTAINERS,
                cron_expr,
                timezone,
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
        test_container = ContainerInspectResult(
            id="35d6d68589ab16a7b06d26513ecae15a7dee2cdb067be5648074c99a39db9fab",
            created=datetime.now(),
            path="/hello",
            state=ContainerState(
                status="exited",
                running=False,
                paused=False,
                restarting=False,
                oom_killed=False,
                dead=False,
                pid=0,
                exit_code=0,
                error="",
                started_at=datetime.now(),
                finished_at=datetime.now(),
            ),
            image="sha256:1b44b5a3e06a9aae883e7bf25e45c100be0bb81a0e01b32de604f3ac44711634",
            name="hello-world",
            platform="linux",
            host_config=ContainerHostConfig(
                network_mode="bridge",
                port_bindings={},
            ),
            config=ContainerConfig(
                hostname="35d6d68589ab",
                image="docker.io/hello-world:latest",
                labels={},
            ),
        )
        test_image = ImageInspectResult(
            id="sha256:1b44b5a3e06a9aae883e7bf25e45c100be0bb81a0e01b32de604f3ac44711634",
            repo_tags=["hello-world:latest"],
            repo_digests=[
                "hello-world@sha256:f7931603f70e13dbd844253370742c4fc4202d290c80442b2e68706d8f33ce26"
            ],
            comment="buildkit.dockerfile.v0",
            created=datetime.now(),
            architecture="amd64",
            os="linux",
            size=10072,
            config=ContainerConfig(
                cmd=["/hello"],
            ),
        )
        items: list[ContainerCheckResult] = [
            ContainerCheckResult(
                container=test_container,
                old_image=None,
                new_image=None,
                result=None,
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=None,
                result="not_available",
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=test_image,
                result="updated",
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=test_image,
                result="available",
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=test_image,
                result="available(notified)",
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=test_image,
                result="rolled_back",
            ),
            ContainerCheckResult(
                container=test_container,
                old_image=test_image,
                new_image=test_image,
                result="failed",
            ),
        ]
        prune_result = """
untagged: postgres@sha256:cf2a05fe40887b721e4b3dbac8fd32673c08292dcc8ba6b62b52b7f640433bd0
deleted: sha256:05c1acb89ae44b0bc936fdad9c7bcf32a2300ef1dbab9407bb6dd12eaee1c8c3
deleted: sha256:030dbd4c7f006cf2a8a482f9128f1b3238e5c820bb107aef0a47299e51179e4b        

Total reclaimed space: 1.5GB
"""
        test_results: list[HostCheckResult] = [
            HostCheckResult(
                host_id=1,
                host_name="test_host_1",
                items=items,
                prune_result=prune_result,
            ),
            HostCheckResult(
                host_id=2,
                host_name="test_host_2",
                items=items,
                prune_result=prune_result,
            ),
        ]
        await send_check_notification(
            test_results,
            title_template=data.title_template,
            body_template=data.body_template,
            urls=data.urls,
        )
        return {}
    except (TugException, AppriseException, TemplateError) as e:
        raise HTTPException(500, str(e))


@router.get(
    "/available_timezones",
    status_code=200,
    description="Get available timezones list",
    response_model=set[str],
)
def get_available_timezones() -> set[str]:
    return VALID_TIMEZONES
