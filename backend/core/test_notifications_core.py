from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jinja2.sandbox import SandboxedEnvironment
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.config import Config
from backend.const import DEFAULT_NOTIFICATION_TEMPLATE
from backend.core.jobs.jobs_results import (
    ContainerJobResult,
    JobNotificationResult,
)
from backend.core.notifications_core import (
    any_worthy,
    send_job_notification,
    send_notification,
)
from backend.exception import (
    TugNotificationException,
    TugUrlValidationError,
    TugUrlValidationSSRFError,
)


@pytest.mark.asyncio
async def test_send_notification_revalidates_urls_before_dispatch():
    apprise = MagicMock()
    apprise.async_notify = AsyncMock(return_value=True)
    urls = ["https://one.example/hook", "https://two.example/hook"]

    with (
        patch(
            "backend.core.notifications_core.validate_url_against_ssrf",
            new_callable=AsyncMock,
        ) as validate,
        patch("backend.core.notifications_core.Apprise", return_value=apprise),
    ):
        await send_notification("title", "body", urls)

    assert validate.await_args_list == [
        (
            (
                url,
                Config.NOTIFICATION_ALLOW_NETWORKS,
                Config.NOTIFICATION_ALLOW_ENDPOINTS,
            ),
            {},
        )
        for url in urls
    ]
    apprise.add.assert_called_once_with(urls)
    apprise.async_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_notification_blocks_url_that_rebinds_to_restricted_network():
    with (
        patch(
            "backend.core.notifications_core.validate_url_against_ssrf",
            new_callable=AsyncMock,
            side_effect=TugUrlValidationSSRFError("restricted address"),
        ),
        patch("backend.core.notifications_core.Apprise") as apprise_class,
    ):
        with pytest.raises(TugNotificationException, match="SSRF protection"):
            await send_notification(
                "title",
                "body",
                ["https://attacker-controlled.example/hook"],
            )

    apprise_class.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_allows_nonstandard_apprise_urls():
    apprise = MagicMock()
    apprise.async_notify = AsyncMock(return_value=True)
    urls = ["tgram://bot-token/chat-id"]

    with (
        patch(
            "backend.core.notifications_core.validate_url_against_ssrf",
            new_callable=AsyncMock,
            side_effect=TugUrlValidationError("not a standard URL"),
        ),
        patch("backend.core.notifications_core.Apprise", return_value=apprise),
    ):
        await send_notification("title", "body", urls)

    apprise.async_notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_notification_skips_when_urls_undefined():
    with patch("backend.core.notifications_core.Apprise") as apprise_class:
        await send_notification("title", "body", [])

    apprise_class.assert_not_called()


@pytest.mark.asyncio
async def test_send_job_notification_skips_when_urls_undefined():
    with (
        patch(
            "backend.core.notifications_core.SettingsStorage.get",
            return_value="",
        ),
        patch(
            "backend.core.notifications_core.send_notification",
            new_callable=AsyncMock,
        ) as send,
    ):
        await send_job_notification([])

    send.assert_not_called()


@pytest.mark.asyncio
async def test_send_job_notification_skips_when_urls_are_blank():
    with patch(
        "backend.core.notifications_core.send_notification",
        new_callable=AsyncMock,
    ) as send:
        await send_job_notification([], urls="  \n  ")

    send.assert_not_called()


def test_default_template_appends_pending_version_when_present():
    env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    env.filters["any_worthy"] = any_worthy
    template = env.from_string(DEFAULT_NOTIFICATION_TEMPLATE)
    item = ContainerJobResult(
        container=ContainerInspectResult(
            name="web",
            config=ContainerConfig(image="nginx:latest"),
        ),
        result="available",
        image_spec="nginx:latest",
        current_version="2.3.6",
        available_version="2.3.7",
    )
    results = [JobNotificationResult(host_id=1, host_name="home", items=[item])]

    with_version = template.render(results=results)
    assert "web nginx:latest 2.3.6 -> 2.3.7" in with_version

    item.available_version = None
    without_version = template.render(results=results)
    assert "web nginx:latest" in without_version
    assert "->" not in without_version
