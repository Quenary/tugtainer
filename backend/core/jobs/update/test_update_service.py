from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import backend.modules.containers.containers_model  # noqa: F401
import backend.modules.health.health_model  # noqa: F401
from backend.core.jobs.update.update_service import run_update_service_job
from backend.enums.job_status_enum import EJobStatus
from backend.testing import make_service, patch_async_session

base_module = "backend.core.jobs.update.update_service"


@pytest.fixture
def mock_session(mocker: MockerFixture):
    session = MagicMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    mock_db_svc = MagicMock()
    mock_db_svc.update_available = True
    mock_db_svc.updated_at = None

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_db_svc
    session.execute = AsyncMock(return_value=mock_execute_result)

    patch_async_session(mocker, base_module, session)
    return session, mock_db_svc


@pytest.mark.asyncio
async def test_run_update_service_job_success(
    mocker: MockerFixture, mock_session: tuple[MagicMock, MagicMock]
):
    session, mock_db_svc = mock_session
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    client.service.update = AsyncMock()
    tracker = MagicMock()
    service = make_service(name="web", image="nginx:alpine", service_id="svc-123")

    result = await run_update_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    client.service.update.assert_called_once()
    req_body = client.service.update.call_args[0][0]
    assert req_body.service_id == "svc-123"
    assert req_body.image == "nginx:alpine"

    assert mock_db_svc.update_available is False
    assert mock_db_svc.updated_at is not None
    assert session.commit.called
    assert result.result == "updated"

    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
async def test_run_update_service_job_failure(
    mocker: MockerFixture, mock_session: tuple[MagicMock, MagicMock]
):
    session, _ = mock_session
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    client.service.update = AsyncMock(side_effect=Exception("Docker API error"))
    tracker = MagicMock()
    service = make_service(name="web", image="nginx:alpine")

    result = await run_update_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert result.result == "failed"
    tracker.set_container.assert_called_with("web", EJobStatus.ERROR, result)
