import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from agent.auth import verify_signature

client = TestClient(app)


async def override_verify_signature():
    return None


app.dependency_overrides[verify_signature] = override_verify_signature


@pytest.mark.asyncio
async def test_swarm_info_inactive(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.local_node_state = "inactive"
    info_mock.swarm.control_available = False
    mocker.patch("agent.api.common_api.DOCKER.info", return_value=info_mock)

    response = client.get("/api/common/swarm-info")
    assert response.status_code == 200
    data = response.json()
    assert data["is_manager"] is False
    assert data["cluster_id"] is None


@pytest.mark.asyncio
async def test_swarm_info_active_manager(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.local_node_state = "active"
    info_mock.swarm.control_available = True
    info_mock.swarm.node_id = "node123"
    info_mock.swarm.cluster.id = "cluster456"
    mocker.patch("agent.api.common_api.DOCKER.info", return_value=info_mock)

    response = client.get("/api/common/swarm-info")
    assert response.status_code == 200
    data = response.json()
    assert data["is_manager"] is True
    assert data["cluster_id"] == "cluster456"
    assert data["node_id"] == "node123"


@pytest.mark.asyncio
async def test_service_list_not_manager(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.local_node_state = "active"
    info_mock.swarm.control_available = False
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info_mock)

    response = client.get("/api/service/list")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_service_list_manager_returns_services(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.control_available = True
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info_mock)

    svc_mock = MagicMock()
    svc_mock.id = "svc1"
    mocker.patch("agent.api.service_api.DOCKER.service.list", return_value=[svc_mock])

    inspect_data = [
        {
            "ID": "svc1",
            "Spec": {
                "Name": "web",
                "Labels": {"com.example": "true"},
                "Mode": {"Replicated": {"Replicas": 3}},
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": "nginx:latest",
                    }
                },
            },
            "ServiceStatus": {
                "RunningTasks": 3,
                "DesiredTasks": 3,
            },
            "UpdateStatus": {
                "State": "completed",
                "Message": "update completed",
            },
        }
    ]
    mocker.patch("agent.api.service_api.run", return_value=json.dumps(inspect_data))

    response = client.get("/api/service/list")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "web"
    assert data[0]["image"] == "nginx:latest"
    assert data[0]["replicas"]["running"] == 3
    assert data[0]["replicas"]["desired"] == 3
    assert data[0]["update_status_state"] == "completed"


@pytest.mark.asyncio
async def test_service_list_replicas_from_service_ls(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.control_available = True
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info_mock)

    svc_mock = MagicMock()
    svc_mock.id = "svc2"
    mocker.patch("agent.api.service_api.DOCKER.service.list", return_value=[svc_mock])

    inspect_data = [
        {
            "ID": "svc2",
            "Spec": {
                "Name": "app",
                "Mode": {"Replicated": {"Replicas": 2}},
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": "app:1.0",
                    }
                },
            },
        }
    ]
    ls_data = '{"ID":"svc2","Name":"app","Replicas":"2/2"}\n'

    def mock_run(cmd):
        if "inspect" in cmd:
            return json.dumps(inspect_data)
        if "ls" in cmd:
            return ls_data
        return ""

    mocker.patch("agent.api.service_api.run", side_effect=mock_run)

    response = client.get("/api/service/list")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "app"
    assert data[0]["replicas"]["running"] == 2
    assert data[0]["replicas"]["desired"] == 2


@pytest.mark.asyncio
async def test_service_update(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.control_available = True
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info_mock)
    update_mock = mocker.patch("agent.api.service_api.DOCKER.service.update")

    response = client.post(
        "/api/service/update",
        json={"service_id": "svc1", "image": "nginx:1.25"},
    )
    assert response.status_code == 200
    assert response.json() == "svc1"
    update_mock.assert_called_once_with(
        "svc1",
        image="nginx:1.25",
        detach=True,
        with_registry_authentication=True,
    )


@pytest.mark.asyncio
async def test_service_logs(mocker: MockerFixture):
    info_mock = MagicMock()
    info_mock.swarm.control_available = True
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info_mock)
    mocker.patch(
        "agent.api.service_api.DOCKER.service.logs",
        return_value="log line 1\nlog line 2",
    )

    response = client.get("/api/service/logs/svc1?tail=50")
    assert response.status_code == 200
    assert "log line 1" in response.text
