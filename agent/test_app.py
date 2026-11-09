from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from agent.app import (
    runtime_conflict_handler,
    runtime_exception_handler,
    runtime_not_found_handler,
    timeout_exception_handler,
    warn_if_agent_secret_missing,
)
from shared.runtime import (
    RuntimeClientError,
    RuntimeConflictError,
    RuntimeNotFoundError,
)


@pytest.mark.parametrize(
    ("secret", "allow_unauthenticated", "expect_warning"),
    [
        (None, False, True),
        (None, True, False),
        ("my-secret", False, False),
    ],
)
def test_warn_if_agent_secret_missing(
    mocker: MockerFixture,
    secret: str | None,
    allow_unauthenticated: bool,
    expect_warning: bool,
):
    mocker.patch("agent.app.Config.AGENT_SECRET", secret)
    mocker.patch(
        "agent.app.Config.ALLOW_UNAUTHENTICATED_AGENT",
        allow_unauthenticated,
    )
    warning = mocker.patch("agent.app.logging.warning")

    warn_if_agent_secret_missing()

    if expect_warning:
        warning.assert_called_once()
        assert "AGENT_SECRET is not set" in warning.call_args.args[0]
    else:
        warning.assert_not_called()


@pytest.mark.asyncio
async def test_timeout_exception_handler():
    with pytest.raises(HTTPException) as exc_info:
        await timeout_exception_handler(MagicMock(), TimeoutError())
    assert exc_info.value.status_code == 500
    assert "Timeout error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_runtime_not_found_handler():
    exc = RuntimeNotFoundError("container not found")
    with pytest.raises(HTTPException) as exc_info:
        await runtime_not_found_handler(MagicMock(), exc)
    assert exc_info.value.status_code == 404
    assert "container not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_runtime_conflict_handler():
    exc = RuntimeConflictError("name conflict")
    with pytest.raises(HTTPException) as exc_info:
        await runtime_conflict_handler(MagicMock(), exc)
    assert exc_info.value.status_code == 409
    assert "name conflict" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_runtime_exception_handler():
    exc = RuntimeClientError("connection refused")
    with pytest.raises(HTTPException) as exc_info:
        await runtime_exception_handler(MagicMock(), exc)
    assert exc_info.value.status_code == 424
    assert "connection refused" in str(exc_info.value.detail)
