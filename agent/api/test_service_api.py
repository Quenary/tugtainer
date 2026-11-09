from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from agent.testing import make_service_inspect, make_swarm_info

client = TestClient(app)


def _patch_manager(mocker: MockerFixture, *, control_available: bool) -> None:
    info = make_swarm_info(
        control_available=control_available,
        local_node_state="active",
    )
    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.get_info",
        new=AsyncMock(return_value=info),
    )


@pytest.mark.parametrize(
    ("state", "control_available", "node_id", "cluster_id", "with_cluster", "expected"),
    [
        (
            "inactive",
            False,
            None,
            None,
            True,
            {"is_manager": False, "cluster_id": None, "node_id": None},
        ),
        (
            "active",
            True,
            "node123",
            "cluster456",
            True,
            {"is_manager": True, "cluster_id": "cluster456", "node_id": "node123"},
        ),
        (
            "active",
            False,
            "worker1",
            "cluster456",
            True,
            {"is_manager": False, "cluster_id": "cluster456", "node_id": "worker1"},
        ),
        (
            "active",
            True,
            "",
            None,
            False,
            {"is_manager": True, "cluster_id": None, "node_id": None},
        ),
    ],
)
def test_swarm_info(
    mocker: MockerFixture,
    state: str,
    control_available: bool,
    node_id: str | None,
    cluster_id: str | None,
    with_cluster: bool,
    expected: dict[str, object],
):
    info = make_swarm_info(
        control_available=control_available,
        local_node_state=state,
        node_id=node_id,
        cluster_id=cluster_id,
        with_cluster=with_cluster,
    )
    mocker.patch(
        "agent.api.common_api.RUNTIME_CLIENT.get_info",
        new=AsyncMock(return_value=info),
    )

    response = client.get("/api/common/swarm-info")

    assert response.status_code == 200
    assert response.json() == expected


def test_service_list_not_manager(mocker: MockerFixture):
    _patch_manager(mocker, control_available=False)

    response = client.get("/api/service/list")

    assert response.status_code == 503


def test_service_list_empty(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_list",
        new=AsyncMock(return_value=[]),
    )

    response = client.get("/api/service/list")

    assert response.status_code == 200
    assert response.json() == []


def test_service_list_manager_returns_services(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    inspect_data = [
        make_service_inspect(
            "svc1",
            "web",
            "nginx:latest",
            replicas=3,
            running_tasks=3,
            desired_tasks=3,
            labels={"com.example": "true"},
            update_state="completed",
            update_message="update completed",
        )
    ]
    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_list",
        new=AsyncMock(return_value=inspect_data),
    )

    response = client.get("/api/service/list")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "web"
    assert data[0]["image"] == "nginx:latest"
    assert data[0]["replicas"]["running"] == 3
    assert data[0]["replicas"]["desired"] == 3
    assert data[0]["update_status_state"] == "completed"
    assert data[0]["update_status_message"] == "update completed"


def test_service_list_replicated_desired_from_mode(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    inspect_data = [make_service_inspect("svc3", "db", "postgres:16", replicas=4)]

    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_list",
        new=AsyncMock(return_value=inspect_data),
    )

    response = client.get("/api/service/list")

    assert response.status_code == 200
    replicas = response.json()[0]["replicas"]
    assert replicas["running"] == 0
    assert replicas["desired"] == 4


def test_service_list_global_mode_ignores_replicated_default(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    inspect_data = [
        make_service_inspect("svc4", "agent", "agent:latest", mode="global")
    ]

    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_list",
        new=AsyncMock(return_value=inspect_data),
    )

    response = client.get("/api/service/list")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["mode"] == "global"
    assert item["replicas"]["running"] == 0
    assert item["replicas"]["desired"] is None


def test_service_update(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    update_mock = mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_update",
        new=AsyncMock(),
    )

    response = client.post(
        "/api/service/update",
        json={"service_id": "svc1", "image": "nginx:1.25"},
    )

    assert response.status_code == 200
    assert response.json() == "svc1"
    update_mock.assert_awaited_once_with(
        "svc1",
        "nginx:1.25",
    )


@pytest.mark.parametrize(
    ("logs", "expected"),
    [
        ("log line 1\nlog line 2", "log line 1\nlog line 2"),
        ("", ""),
        (None, ""),
    ],
)
def test_service_logs(mocker: MockerFixture, logs: str | None, expected: str):
    _patch_manager(mocker, control_available=True)
    logs_mock = mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_logs",
        new=AsyncMock(return_value=logs or ""),
    )

    response = client.get("/api/service/logs/svc1?tail=50")

    assert response.status_code == 200
    assert response.json() == expected
    logs_mock.assert_awaited_once_with("svc1", tail=50, timestamps=False)


def test_service_inspect_not_found(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_inspect",
        new=AsyncMock(return_value=None),
    )

    response = client.get("/api/service/inspect/missing")

    assert response.status_code == 404


def test_service_inspect_returns_object(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch(
        "agent.api.service_api.RUNTIME_CLIENT.service_inspect",
        new=AsyncMock(return_value={"ID": "svc1", "Spec": {"Name": "web"}}),
    )

    response = client.get("/api/service/inspect/svc1")

    assert response.status_code == 200
    assert response.json()["ID"] == "svc1"
    assert response.json()["Spec"]["Name"] == "web"
