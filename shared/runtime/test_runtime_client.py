import pytest
from pytest_mock import MockerFixture

from shared.runtime.runtime_client import (
    CLIENT_MAX_DOCKER_API,
    RuntimeClient,
    encode_registry_auth,
    parse_version_tuple,
)
from shared.runtime.runtime_errors import IncompatibleRuntimeError


def test_parse_version_tuple():
    assert parse_version_tuple("1.44") == (1, 44)
    assert parse_version_tuple("1.48.2") == (1, 48)
    assert parse_version_tuple("2") == (2, 0)
    assert parse_version_tuple(None) == (0, 0)


def test_encode_registry_auth():
    auth = {"serveraddress": "ghcr.io", "username": "user", "password": "token"}
    encoded = encode_registry_auth(auth)
    assert encoded is not None
    assert "=" not in encoded  # Must be stripped padding


@pytest.mark.asyncio
async def test_get_version_docker_negotiation(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "28.0.0",
            "ApiVersion": "1.48",
            "MinAPIVersion": "1.24",
            "Components": [{"Name": "Engine", "Version": "28.0.0"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    assert version_info.runtime_type == "docker"
    assert version_info.negotiated_api == "1.48"
    assert client._negotiated_api_prefix == "/v1.48"


@pytest.mark.asyncio
async def test_get_version_docker_caps_at_max_supported(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    # Future daemon with API 1.55
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "32.0.0",
            "ApiVersion": "1.55",
            "MinAPIVersion": "1.24",
            "Components": [{"Name": "Engine"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    # Must negotiate to CLIENT_MAX_DOCKER_API (1.48)
    assert (
        version_info.negotiated_api
        == f"{CLIENT_MAX_DOCKER_API[0]}.{CLIENT_MAX_DOCKER_API[1]}"
    )
    assert (
        client._negotiated_api_prefix
        == f"/v{CLIENT_MAX_DOCKER_API[0]}.{CLIENT_MAX_DOCKER_API[1]}"
    )


@pytest.mark.asyncio
async def test_get_version_docker_too_old_raises(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    # Daemon older than 1.44 (e.g. 1.41)
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "20.10.0",
            "ApiVersion": "1.41",
            "MinAPIVersion": "1.12",
            "Components": [{"Name": "Engine"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    with pytest.raises(IncompatibleRuntimeError) as exc_info:
        await client.get_version()
    assert "below minimum supported 1.44" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_version_podman_detection(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Libpod-API-Version": "5.2.0"}
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "5.2.0",
            "ApiVersion": "1.41",
            "Components": [{"Name": "Podman Engine", "Version": "5.2.0"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    assert version_info.runtime_type == "podman"
    assert version_info.libpod_api_version == "5.2.0"
    # Podman does NOT raise for ApiVersion < 1.44
    assert client._negotiated_api_prefix == "/v1.41"
