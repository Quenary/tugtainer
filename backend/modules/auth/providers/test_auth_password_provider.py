from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.config import Config
from backend.const import SETUP_CODE_TTL_MIN
from backend.modules.auth.auth_schemas import PasswordSetRequestBody
from backend.modules.auth.providers.auth_password_provider import AuthPasswordProvider

PASSWORD = "NewPass1"


def _body(setup_code: str | None = None) -> PasswordSetRequestBody:
    return PasswordSetRequestBody(
        password=PASSWORD,
        confirm_password=PASSWORD,
        setup_code=setup_code,
    )


@pytest.fixture
def provider(tmp_path, monkeypatch) -> AuthPasswordProvider:
    monkeypatch.setattr(Config, "PASSWORD_FILE", str(tmp_path / "password_hash"))
    monkeypatch.setattr(Config, "DISABLE_AUTH", False)
    monkeypatch.setattr(Config, "DISABLE_PASSWORD", False)
    return AuthPasswordProvider()


def test_issue_setup_code_once_when_password_missing(provider, caplog):
    provider.issue_setup_code()
    code = provider._setup_code
    assert code
    assert provider._setup_code_expires_at is not None
    assert "Initial setup code: " in caplog.text
    assert str(SETUP_CODE_TTL_MIN) in caplog.text

    provider.issue_setup_code()
    assert provider._setup_code == code


def test_issue_skipped_when_password_exists(provider):
    provider._write_password_hash("hash")
    provider.issue_setup_code()
    assert provider._setup_code is None
    assert provider._setup_code_issued is False


def test_issue_skipped_when_password_auth_disabled(provider, monkeypatch):
    monkeypatch.setattr(Config, "DISABLE_PASSWORD", True)
    provider.issue_setup_code()
    assert provider._setup_code is None


@pytest.mark.asyncio
async def test_initial_set_requires_valid_code(provider):
    provider.issue_setup_code()

    with pytest.raises(HTTPException) as missing:
        await provider.set_password(MagicMock(), _body())
    assert missing.value.status_code == 401
    assert missing.value.detail == "Invalid setup code"

    with pytest.raises(HTTPException) as wrong:
        await provider.set_password(MagicMock(), _body("not-the-code"))
    assert wrong.value.detail == "Invalid setup code"
    assert provider._setup_code is not None


@pytest.mark.asyncio
async def test_expired_code_is_not_reissued(provider):
    provider.issue_setup_code()
    code = provider._setup_code
    provider._setup_code_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    provider.issue_setup_code()
    assert provider._setup_code == code

    with pytest.raises(HTTPException) as expired:
        await provider.set_password(MagicMock(), _body(code))
    assert expired.value.status_code == 401
    assert "Restart the container" in expired.value.detail
    assert provider._setup_code == code
    assert not provider.is_password_set()


@pytest.mark.asyncio
async def test_valid_code_sets_password_once(provider):
    provider.issue_setup_code()
    code = provider._setup_code

    response = await provider.set_password(MagicMock(), _body(code))
    assert response.status_code == 201
    assert provider.is_password_set()
    assert provider._setup_code is None

    provider._write_password_hash("")
    assert not provider.is_password_set()
    with pytest.raises(HTTPException) as reused:
        await provider.set_password(MagicMock(), _body(code))
    assert reused.value.detail == "Invalid setup code"


@pytest.mark.asyncio
async def test_authorized_change_ignores_setup_code(provider, monkeypatch):
    provider._write_password_hash(provider._get_password_hash("OldPass1"))
    monkeypatch.setattr(provider, "is_authorized", AsyncMock(return_value=True))

    response = await provider.set_password(MagicMock(), _body())
    assert response.status_code == 201
    assert provider._verify_password(PASSWORD, provider._read_password_hash())
