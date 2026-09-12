from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import app
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized_req
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.health.health_model import ContainerHealthHistory
from backend.modules.health.health_router import health_router

client = TestClient(app)


async def override_is_authorized_req():
    return True


app.dependency_overrides[is_authorized_req] = override_is_authorized_req


def test_health_router_is_protected_by_auth():
    dep_callables = [d.dependency for d in health_router.dependencies]
    assert is_authorized_req in dep_callables


@pytest.mark.asyncio
async def test_get_health_history_success(mocker: MockerFixture):

    now_dt = datetime.now(UTC)
    mock_history_item = ContainerHealthHistory(
        id=10,
        host_id=1,
        container_id=5,
        status="healthy",
        restarted=False,
        notified=False,
        created_at=now_dt,
    )
    mock_history_item.container = ContainersModel(
        id=5, host_id=1, name="nginx_container"
    )

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = 1
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_history_item]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    async def override_get_async_session():
        yield mock_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        response = client.post(
            "/health/history",
            json={"host_id": 1, "page": 1, "limit": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["limit"] == 20
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["id"] == 10
        assert item["host_id"] == 1
        assert item["container_id"] == 5
        assert item["container_name"] == "nginx_container"
        assert item["status"] == "healthy"
        assert item["restarted"] is False
        assert item["notified"] is False
    finally:
        app.dependency_overrides.pop(get_async_session, None)


@pytest.mark.asyncio
async def test_get_health_history_fallback_container_name(mocker: MockerFixture):
    now_dt = datetime.now(UTC)
    mock_history_item = ContainerHealthHistory(
        id=11,
        host_id=1,
        container_id=6,
        status="unhealthy",
        restarted=True,
        notified=True,
        created_at=now_dt,
    )
    mock_history_item.container = None  # deleted container

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.scalar.return_value = 1
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_history_item]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    async def override_get_async_session():
        yield mock_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        response = client.post(
            "/health/history",
            json={"host_id": 1, "container_id": 6, "status": ["unhealthy"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["container_name"] == "Unknown"
        assert item["status"] == "unhealthy"
        assert item["restarted"] is True
        assert item["notified"] is True
    finally:
        app.dependency_overrides.pop(get_async_session, None)
