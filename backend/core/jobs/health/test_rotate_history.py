from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.health.rotate_history import rotate_health_history
from backend.testing import patch_async_session

base_module = "backend.core.jobs.health.rotate_history"


@pytest.mark.asyncio
async def test_rotate_health_history(mocker: MockerFixture):
    session = AsyncMock()

    class DeleteResult:
        rowcount = 5

    session.execute.return_value = DeleteResult()

    patch_async_session(mocker, base_module, session)

    await rotate_health_history()

    session.commit.assert_called_once()
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_rotate_health_history_skips_non_positive_days(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=-1)
    session_maker = mocker.patch(f"{base_module}.async_session_maker")

    await rotate_health_history()

    session_maker.assert_not_called()


@pytest.mark.asyncio
async def test_rotate_health_history_swallows_db_errors(
    mocker: MockerFixture,
) -> None:
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("db down")
    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=7)

    await rotate_health_history()
