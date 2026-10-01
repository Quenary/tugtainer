from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from python_on_whales import DockerException

from agent.app import app

client = TestClient(app)


def test_health_ok(mocker: MockerFixture):
    mocker.patch("agent.api.public_api.DOCKER.info", return_value=MagicMock())

    response = client.get("/api/public/health")

    assert response.status_code == 200
    assert response.json() == "OK"


def test_health_docker_failure(mocker: MockerFixture):
    mocker.patch(
        "agent.api.public_api.DOCKER.info",
        side_effect=DockerException(["docker", "info"], 1, stderr=b"cannot connect"),
    )

    response = client.get("/api/public/health")

    assert response.status_code == 424
    assert response.json()["detail"] == "Failed to get docker cli info"
