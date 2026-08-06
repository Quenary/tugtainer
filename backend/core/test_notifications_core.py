from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import Config
from backend.core.notifications_core import send_notification
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
            (url, Config.NOTIFICATION_ALLOW_NETWORKS, Config.NOTIFICATION_ALLOW_ENDPOINTS),
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
