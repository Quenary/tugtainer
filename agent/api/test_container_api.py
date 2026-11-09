from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app

base_module = "agent.api.container_api"

client = TestClient(app)


@pytest.mark.parametrize(
    ("http_method", "path", "client_method"),
    [
        ("post", "/api/container/start/c1", "container_start"),
        ("post", "/api/container/stop/c1", "container_stop"),
        ("post", "/api/container/restart/c1", "container_restart"),
        ("post", "/api/container/kill/c1", "container_kill"),
        ("post", "/api/container/pause/c1", "container_pause"),
        ("post", "/api/container/unpause/c1", "container_unpause"),
        ("delete", "/api/container/remove/c1", "container_remove"),
    ],
)
def test_container_action_returns_id(
    mocker: MockerFixture,
    http_method: str,
    path: str,
    client_method: str,
):
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    action = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.{client_method}",
        new=AsyncMock(),
    )

    response = getattr(client, http_method)(path)

    assert response.status_code == 200
    assert response.json() == "c1"
    if client_method == "container_remove":
        action.assert_awaited_once_with("c1", force=False)
    else:
        action.assert_awaited_once_with("c1")


def test_rename_container(mocker: MockerFixture):
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    rename_mock = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_rename",
        new=AsyncMock(),
    )

    response = client.post("/api/container/rename/c1?new_name=c2")

    assert response.status_code == 200
    assert response.json() == "c2"
    rename_mock.assert_awaited_once_with("c1", "c2")


def test_remove_forwards_force_query(mocker: MockerFixture) -> None:
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    remove = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_remove",
        new=AsyncMock(),
    )

    response = client.delete("/api/container/remove/c1?force=true")

    assert response.status_code == 200
    remove.assert_awaited_once_with("c1", force=True)


def test_exec_forbidden_when_allow_exec_false(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", False)
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    execute_mock = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exec",
        new=AsyncMock(),
    )

    response = client.post(
        "/api/container/exec/my-container",
        json={"command": "echo hi"},
    )

    assert response.status_code == 403
    execute_mock.assert_not_called()


def test_exec_runs_command_when_allow_exec_true(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", True)
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    execute_mock = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exec",
        new=AsyncMock(return_value="hi\n"),
    )

    response = client.post(
        "/api/container/exec/my-container",
        json={"command": "echo hi"},
    )

    assert response.status_code == 200
    assert response.json() == "hi\n"
    execute_mock.assert_awaited_once_with(
        "my-container",
        ["sh", "-c", "echo hi"],
    )


def test_logs_forwards_filters(mocker: MockerFixture):
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=True),
    )
    logs = mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_logs",
        new=AsyncMock(return_value="line\n"),
    )

    response = client.post(
        "/api/container/logs/c1",
        json={
            "tail": 20,
            "timestamps": True,
            "details": True,
            "since": "2026-11-09T12:00:00Z",
            "until": "2026-11-09T13:00:00Z",
        },
    )

    assert response.status_code == 200
    assert response.json() == "line\n"
    kwargs = logs.await_args.kwargs
    assert kwargs["details"] is True
    assert kwargs["timestamps"] is True
    assert kwargs["tail"] == 20
    assert kwargs["since"] is not None
    assert kwargs["until"] is not None


def test_exec_404_when_container_missing(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", True)
    mocker.patch(
        f"{base_module}.RUNTIME_CLIENT.container_exists",
        new=AsyncMock(return_value=False),
    )

    response = client.post(
        "/api/container/exec/missing",
        json={"command": "echo hi"},
    )

    assert response.status_code == 404
