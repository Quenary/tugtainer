from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from shared.runtime import RuntimeClientError

client = TestClient(app)


def test_health_ok(mocker: MockerFixture):
    mocker.patch(
        "agent.api.public_api.RUNTIME_CLIENT.ping",
        new=AsyncMock(return_value=True),
    )

    response = client.get("/api/public/health")

    assert response.status_code == 200
    assert response.json() == "OK"


def test_health_docker_failure(mocker: MockerFixture):
    mocker.patch(
        "agent.api.public_api.RUNTIME_CLIENT.ping",
        new=AsyncMock(side_effect=RuntimeClientError("cannot connect")),
    )

    response = client.get("/api/public/health")

    assert response.status_code == 424
    assert response.json()["detail"] == "Failed to connect to container runtime"
