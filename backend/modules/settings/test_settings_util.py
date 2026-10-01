from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from backend.config import Config
from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError
from backend.modules.settings.settings_util import (
    validate_notification_urls,
    validate_notification_urls_against_ssrf,
)


def test_validate_notification_urls_rejects_missing_scheme(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(Config, "NOTIFICATION_ALLOW_SCHEMES", {"https"})
    with pytest.raises(ValueError, match="Missing scheme"):
        validate_notification_urls("example.com/hook")


def test_validate_notification_urls_rejects_disallowed_scheme(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(Config, "NOTIFICATION_ALLOW_SCHEMES", {"https"})
    with pytest.raises(ValueError, match="not allowed"):
        validate_notification_urls("http://example.com/hook")


@pytest.mark.asyncio
async def test_notification_ssrf_becomes_422(mocker: MockerFixture) -> None:
    mocker.patch(
        "backend.modules.settings.settings_util.validate_url_against_ssrf",
        new=AsyncMock(side_effect=TugUrlValidationSSRFError("restricted")),
    )
    with pytest.raises(HTTPException) as exc_info:
        await validate_notification_urls_against_ssrf("https://evil.example")
    assert exc_info.value.status_code == 422
    assert "NOTIFICATION_ALLOW_NETWORKS" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_notification_ssrf_ignores_non_ssrf_errors(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "backend.modules.settings.settings_util.validate_url_against_ssrf",
        new=AsyncMock(side_effect=TugUrlValidationError("not a standard URL")),
    )
    await validate_notification_urls_against_ssrf("tgram://bot/chat")
