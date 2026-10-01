import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app

base_module = "agent.api.container_api"

client = TestClient(app)


@pytest.mark.parametrize(
    ("http_method", "path", "docker_method"),
    [
        ("post", "/api/container/start/c1", "start"),
        ("post", "/api/container/stop/c1", "stop"),
        ("post", "/api/container/restart/c1", "restart"),
        ("post", "/api/container/kill/c1", "kill"),
        ("post", "/api/container/pause/c1", "pause"),
        ("post", "/api/container/unpause/c1", "unpause"),
        ("delete", "/api/container/remove/c1", "remove"),
    ],
)
def test_container_action_returns_id(
    mocker: MockerFixture,
    http_method: str,
    path: str,
    docker_method: str,
):
    mocker.patch(f"{base_module}.DOCKER.container.exists", return_value=True)
    action = mocker.patch(f"{base_module}.DOCKER.container.{docker_method}")

    response = getattr(client, http_method)(path)

    assert response.status_code == 200
    assert response.json() == "c1"
    action.assert_called_once_with("c1")


def test_exec_forbidden_when_allow_exec_false(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", False)
    mocker.patch(
        f"{base_module}.DOCKER.container.exists",
        return_value=True,
    )
    execute_mock = mocker.patch(f"{base_module}.DOCKER.container.execute")

    response = client.post(
        "/api/container/exec/my-container",
        json={"command": "echo hi"},
    )

    assert response.status_code == 403
    execute_mock.assert_not_called()


def test_exec_runs_command_when_allow_exec_true(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", True)
    mocker.patch(
        f"{base_module}.DOCKER.container.exists",
        return_value=True,
    )
    execute_mock = mocker.patch(
        f"{base_module}.DOCKER.container.execute",
        return_value="hi\n",
    )

    response = client.post(
        "/api/container/exec/my-container",
        json={"command": "echo hi"},
    )

    assert response.status_code == 200
    assert response.json() == "hi\n"
    execute_mock.assert_called_once_with(
        "my-container",
        ["sh", "-c", "echo hi"],
    )


def test_exec_404_when_container_missing(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_EXEC", True)
    mocker.patch(
        f"{base_module}.DOCKER.container.exists",
        return_value=False,
    )

    response = client.post(
        "/api/container/exec/missing",
        json={"command": "echo hi"},
    )

    assert response.status_code == 404
