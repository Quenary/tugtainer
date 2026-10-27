from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import ContainerInspectResult

from backend.core.container_util.wait_for_container_healthy import (
    wait_for_container_healthy,
)

base_module = "backend.core.container_util.wait_for_container_healthy"


@pytest.mark.asyncio
async def test_wait_delegates_to_shared_rule_with_agent_inspect(
    mocker: MockerFixture,
) -> None:
    inspected = SimpleNamespace(id="c1")
    shared_wait = mocker.patch(
        f"{base_module}._wait_for_container_healthy",
        new=AsyncMock(return_value=(True, inspected)),
    )
    client = AsyncMock()
    container = cast(ContainerInspectResult, SimpleNamespace(id="c1"))

    ok, got = await wait_for_container_healthy(client, container, timeout=30)

    assert ok is True
    assert got is inspected
    shared_wait.assert_awaited_once_with(client.container.inspect, container, 30)
