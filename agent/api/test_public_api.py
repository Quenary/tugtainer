from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from shared.agent_protocol import AGENT_PROTOCOL
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


def test_version_reports_protocol(mocker: MockerFixture) -> None:
    mocker.patch(
        "agent.api.public_api.read_installed_version",
        return_value="2.0.0",
    )

    response = client.get("/api/public/version")

    assert response.status_code == 200
    assert response.json() == {"version": "2.0.0", "protocol": AGENT_PROTOCOL}
