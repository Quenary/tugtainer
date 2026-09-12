from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.health.monitor_health import run_health_monitor

base_module = "backend.core.jobs.health.monitor_health"


@pytest.mark.asyncio
async def test_run_health_monitor(mocker: MockerFixture):
    mock_check = mocker.patch(
        f"{base_module}.check_all_containers_health",
        new_callable=AsyncMock,
    )
    mock_rotate = mocker.patch(
        f"{base_module}.rotate_health_history",
        new_callable=AsyncMock,
    )

    await run_health_monitor()

    mock_check.assert_awaited_once()
    mock_rotate.assert_awaited_once()
