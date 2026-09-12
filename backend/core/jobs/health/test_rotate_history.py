from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.health.rotate_history import rotate_health_history

base_module = "backend.core.jobs.health.rotate_history"


@pytest.mark.asyncio
async def test_rotate_health_history(mocker: MockerFixture):
    session = AsyncMock()

    class DeleteResult:
        rowcount = 5

    session.execute.return_value = DeleteResult()

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    await rotate_health_history()

    # Verify session was committed
    session.commit.assert_called_once()
    assert session.execute.call_count == 1
