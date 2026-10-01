import json
from unittest.mock import MagicMock

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
    mocker.patch("agent.api.service_api.DOCKER.info", return_value=info)


def _patch_services(mocker: MockerFixture, *service_ids: str) -> None:
    services = []
    for service_id in service_ids:
        svc = MagicMock()
        svc.id = service_id
        services.append(svc)
    mocker.patch("agent.api.service_api.DOCKER.service.list", return_value=services)


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
    mocker.patch("agent.api.common_api.DOCKER.info", return_value=info)

    response = client.get("/api/common/swarm-info")

    assert response.status_code == 200
    assert response.json() == expected


def test_service_list_not_manager(mocker: MockerFixture):
    _patch_manager(mocker, control_available=False)

    response = client.get("/api/service/list")

    assert response.status_code == 503


def test_service_list_empty(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch("agent.api.service_api.DOCKER.service.list", return_value=[])
    run = mocker.patch("agent.api.service_api.run")

    response = client.get("/api/service/list")

    assert response.status_code == 200
    assert response.json() == []
    run.assert_not_called()


def test_service_list_manager_returns_services(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    _patch_services(mocker, "svc1")
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
        "agent.api.service_api.run",
        return_value=json.dumps(inspect_data),
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


def test_service_list_replicas_from_service_ls(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    _patch_services(mocker, "svc2")
    inspect_data = [
        make_service_inspect("svc2", "app", "app:1.0", replicas=2),
    ]
    ls_data = '{"ID":"svc2","Name":"app","Replicas":"2/2"}\n'

    def mock_run(cmd: list[str]) -> str:
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


def test_service_list_replicated_desired_from_mode(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    _patch_services(mocker, "svc3")
    inspect_data = [make_service_inspect("svc3", "db", "postgres:16", replicas=4)]

    def mock_run(cmd: list[str]) -> str:
        if "inspect" in cmd:
            return json.dumps(inspect_data)
        return ""

    mocker.patch("agent.api.service_api.run", side_effect=mock_run)

    response = client.get("/api/service/list")

    assert response.status_code == 200
    replicas = response.json()[0]["replicas"]
    assert replicas["running"] == 0
    assert replicas["desired"] == 4


def test_service_list_global_mode_ignores_replicated_default(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    _patch_services(mocker, "svc4")
    inspect_data = [
        make_service_inspect("svc4", "agent", "agent:latest", mode="global")
    ]

    def mock_run(cmd: list[str]) -> str:
        if "inspect" in cmd:
            return json.dumps(inspect_data)
        return "not-json\n"

    mocker.patch("agent.api.service_api.run", side_effect=mock_run)

    response = client.get("/api/service/list")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["mode"] == "global"
    assert item["replicas"]["running"] == 0
    assert item["replicas"]["desired"] is None


def test_service_list_non_digit_replica_counts(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    _patch_services(mocker, "svc5")
    inspect_data = [make_service_inspect("svc5", "job", "job:1", replicas=1)]
    ls_data = '{"ID":"svc5","Name":"job","Replicas":"x/2"}\n'

    def mock_run(cmd: list[str]) -> str:
        if "inspect" in cmd:
            return json.dumps(inspect_data)
        return ls_data

    mocker.patch("agent.api.service_api.run", side_effect=mock_run)

    response = client.get("/api/service/list")

    assert response.status_code == 200
    replicas = response.json()[0]["replicas"]
    assert replicas["running"] == 0
    assert replicas["desired"] == 2


def test_service_update(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
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
        "agent.api.service_api.DOCKER.service.logs",
        return_value=logs,
    )

    response = client.get("/api/service/logs/svc1?tail=50")

    assert response.status_code == 200
    assert response.json() == expected
    logs_mock.assert_called_once_with("svc1", tail=50, timestamps=False)


def test_service_inspect_not_found(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch("agent.api.service_api.run", return_value="[]")

    response = client.get("/api/service/inspect/missing")

    assert response.status_code == 404


def test_service_inspect_returns_first_object(mocker: MockerFixture):
    _patch_manager(mocker, control_available=True)
    mocker.patch(
        "agent.api.service_api.run",
        return_value=json.dumps([{"ID": "svc1", "Spec": {"Name": "web"}}]),
    )

    response = client.get("/api/service/inspect/svc1")

    assert response.status_code == 200
    assert response.json()["ID"] == "svc1"
    assert response.json()["Spec"]["Name"] == "web"
