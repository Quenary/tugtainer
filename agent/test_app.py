from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture
from python_on_whales import DockerException

from agent.app import (
    docker_exception_handler,
    timeout_exception_handler,
    warn_if_agent_secret_missing,
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
@pytest.mark.parametrize(
    ("stdout", "stderr", "fragments"),
    [
        (None, None, ["Docker Exception"]),
        (b"pulled", None, ["Docker Exception", "stdout: pulled"]),
        (None, b"denied", ["Docker Exception", "stderr: denied"]),
        (b"out", b"err", ["stdout: out", "stderr: err"]),
    ],
)
async def test_docker_exception_handler(
    stdout: bytes | None,
    stderr: bytes | None,
    fragments: list[str],
):
    exc = DockerException(["docker", "info"], 1, stdout=stdout, stderr=stderr)
    with pytest.raises(HTTPException) as exc_info:
        await docker_exception_handler(MagicMock(), exc)
    assert exc_info.value.status_code == 424
    detail = str(exc_info.value.detail)
    for fragment in fragments:
        assert fragment in detail
