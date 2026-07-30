import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from agent.auth import verify_signature

base_module = "agent.api.container_api"

client = TestClient(app)


async def override_verify_signature():
    return None


app.dependency_overrides[verify_signature] = override_verify_signature


@pytest.mark.asyncio
async def test_exec_forbidden_when_allow_exec_false(mocker: MockerFixture):
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


@pytest.mark.asyncio
async def test_exec_runs_command_when_allow_exec_true(mocker: MockerFixture):
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


@pytest.mark.asyncio
async def test_exec_404_when_container_missing(mocker: MockerFixture):
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
