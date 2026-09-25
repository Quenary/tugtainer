from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from backend.app import app
from backend.core.agent_client import AgentClientManager
from backend.modules.auth.auth_util import is_authorized_req
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.services.services_model import SwarmServicesModel
from shared.schemas.service_schemas import (
    ServiceListItemSchema,
    ServiceReplicasSchema,
)

client = TestClient(app)


async def override_auth():
    return True


app.dependency_overrides[is_authorized_req] = override_auth


@pytest.fixture
def mock_host():
    return HostsModel(
        id=1,
        name="swarm-manager",
        enabled=True,
        prune=False,
        prune_all=False,
        url="http://127.0.0.1:8001",
        is_swarm=True,
        swarm_cluster_id="cluster-1",
        timeout=5,
        container_hc_timeout=60,
    )


@pytest.mark.asyncio
async def test_list_services(mocker: MockerFixture, mock_host: HostsModel):
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=mock_host,
    )
    agent_client = MagicMock()
    agent_client.service.list = AsyncMock(
        return_value=[
            ServiceListItemSchema(
                id="s1",
                name="web",
                image="nginx:latest",
                replicas=ServiceReplicasSchema(running=2, desired=2),
            )
        ]
    )
    mocker.patch.object(
        AgentClientManager,
        "get_host_client",
        return_value=agent_client,
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host_services",
        return_value=[],
    )

    response = client.get("/api/hosts/1/services")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "web"
    assert data[0]["replicas_running"] == 2
    assert data[0]["check_enabled"] is False


@pytest.mark.asyncio
async def test_patch_service(mocker: MockerFixture, mock_host: HostsModel):
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=mock_host,
    )
    agent_client = MagicMock()
    agent_client.service.list = AsyncMock(
        return_value=[
            ServiceListItemSchema(
                id="s1",
                name="web",
                image="nginx:latest",
                replicas=ServiceReplicasSchema(running=1, desired=1),
            )
        ]
    )
    mocker.patch.object(
        AgentClientManager,
        "get_host_client",
        return_value=agent_client,
    )

    mock_db_item = SwarmServicesModel(
        id=1,
        host_id=1,
        service_id="s1",
        name="web",
        image="nginx:latest",
        check_enabled=False,
        update_enabled=False,
    )

    mocker.patch(
        "backend.modules.services.services_router.get_or_create_service",
        return_value=mock_db_item,
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    from backend.db.session import get_async_session

    app.dependency_overrides[get_async_session] = lambda: mock_session
    try:
        response = client.patch(
            "/api/hosts/1/services/web",
            json={"check_enabled": True, "update_enabled": True},
        )
    finally:
        app.dependency_overrides.pop(get_async_session, None)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "web"
    assert data["check_enabled"] is True


@pytest.mark.asyncio
async def test_check_services_trigger(mocker: MockerFixture, mock_host: HostsModel):
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=mock_host,
    )
    submit_mock = mocker.patch(
        "backend.modules.services.services_router.host_job_coordinator.submit",
        new=AsyncMock(),
    )

    response = client.post(
        "/api/hosts/1/services/check",
        json={"names": ["web"]},
    )
    assert response.status_code == 200
    submit_mock.assert_called_once_with(
        mock_host,
        "check_services",
        names=["web"],
        manual=True,
        wait=False,
    )


@pytest.mark.asyncio
async def test_service_logs(mocker: MockerFixture, mock_host: HostsModel):
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=mock_host,
    )
    agent_client = MagicMock()
    agent_client.service.logs = AsyncMock(return_value="service log content")
    mocker.patch.object(
        AgentClientManager,
        "get_host_client",
        return_value=agent_client,
    )

    response = client.get("/api/hosts/1/services/web/logs?tail=50")
    assert response.status_code == 200
    assert response.text == "service log content"


@pytest.mark.asyncio
async def test_list_services_non_swarm_or_disabled(mocker: MockerFixture):
    non_swarm = HostsModel(
        id=2,
        name="standalone-docker",
        enabled=True,
        is_swarm=False,
        url="http://127.0.0.1:8002",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=non_swarm,
    )
    response = client.get("/api/hosts/2/services")
    assert response.status_code == 400

    disabled_host = HostsModel(
        id=3,
        name="disabled-host",
        enabled=False,
        is_swarm=True,
        url="http://127.0.0.1:8003",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=disabled_host,
    )
    resp_disabled = client.get("/api/hosts/3/services")
    assert resp_disabled.status_code == 409


@pytest.mark.asyncio
async def test_patch_service_disabled_or_non_swarm(mocker: MockerFixture):
    disabled_host = HostsModel(
        id=3,
        name="disabled-host",
        enabled=False,
        is_swarm=True,
        url="http://127.0.0.1:8003",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=disabled_host,
    )
    resp = client.patch(
        "/api/hosts/3/services/web",
        json={"check_enabled": True},
    )
    assert resp.status_code == 409

    non_swarm = HostsModel(
        id=4,
        name="non-swarm",
        enabled=True,
        is_swarm=False,
        url="http://127.0.0.1:8004",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=non_swarm,
    )
    resp2 = client.patch(
        "/api/hosts/4/services/web",
        json={"check_enabled": True},
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_service_logs_disabled_or_non_swarm(mocker: MockerFixture):
    disabled_host = HostsModel(
        id=3,
        name="disabled-host",
        enabled=False,
        is_swarm=True,
        url="http://127.0.0.1:8003",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=disabled_host,
    )
    resp = client.get("/api/hosts/3/services/web/logs")
    assert resp.status_code == 409

    non_swarm = HostsModel(
        id=4,
        name="non-swarm",
        enabled=True,
        is_swarm=False,
        url="http://127.0.0.1:8004",
    )
    mocker.patch(
        "backend.modules.services.services_router.get_host",
        return_value=non_swarm,
    )
    resp2 = client.get("/api/hosts/4/services/web/logs")
    assert resp2.status_code == 400
