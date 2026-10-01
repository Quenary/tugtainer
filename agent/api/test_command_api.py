from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from agent.api.command_api import run
from shared.schemas.command_schemas import RunCommandRequestBodySchema


def _body() -> RunCommandRequestBodySchema:
    return RunCommandRequestBodySchema(
        command=["network", "connect", "vpnnet", "app"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ("", "")),
        ("", ("", "")),
        ("connected", ("connected", "")),
        (("out", "err"), ("out", "err")),
        (123, ("123", "")),
    ],
)
async def test_run_normalizes_command_result(
    mocker: MockerFixture,
    raw: object,
    expected: tuple[str, str],
):
    mocker.patch(
        "agent.api.command_api.asyncall",
        new=AsyncMock(return_value=raw),
    )

    assert await run(_body()) == expected
