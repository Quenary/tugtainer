import asyncio
import time

import pytest
from pytest_mock import MockerFixture

from agent.unil.asyncall import asyncall


@pytest.mark.asyncio
async def test_asyncall_uses_configured_timeout(mocker: MockerFixture):
    mocker.patch("agent.unil.asyncall.Config.DOCKER_TIMEOUT", 4)
    captured: dict[str, float | None] = {}
    real_wait_for = asyncio.wait_for

    async def spy(awaitable, timeout):
        captured["timeout"] = timeout
        return await real_wait_for(awaitable, timeout)

    mocker.patch("agent.unil.asyncall.asyncio.wait_for", spy)

    assert await asyncall(lambda: "ok") == "ok"
    assert captured["timeout"] == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", [None, 0])
async def test_asyncall_skips_wait_for_when_timeout_disabled(
    mocker: MockerFixture,
    timeout: int | None,
):
    wait_for = mocker.patch("agent.unil.asyncall.asyncio.wait_for")

    assert await asyncall(lambda: 7, asyncall_timeout=timeout) == 7
    wait_for.assert_not_called()


@pytest.mark.asyncio
async def test_asyncall_times_out():
    with pytest.raises(TimeoutError):
        await asyncall(lambda: time.sleep(1), asyncall_timeout=0.05)
