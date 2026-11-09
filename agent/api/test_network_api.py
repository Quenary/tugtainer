from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_connect_sends_gw_priority(mocker: MockerFixture) -> None:
    connect = AsyncMock()
    mocker.patch("agent.api.network_api.RUNTIME_CLIENT.network_connect", connect)
    mocker.patch(
        "agent.api.network_api.RUNTIME_CLIENT._negotiated_api_prefix",
        "/v1.48",
    )

    response = client.post(
        "/api/network/connect",
        json={
            "network": "appnet",
            "container": "web",
            "ipv4_address": "172.20.0.8",
            "aliases": ["web"],
            "mac_address": "02:42:ac:14:00:08",
            "driver_opts": {"com.docker.network.endpoint.ifname": "eth0"},
            "gateway_priority": 4,
        },
    )

    assert response.status_code == 200
    endpoint = connect.await_args.kwargs["endpoint_config"]
    assert endpoint["GwPriority"] == 4
    assert "GatewayPriority" not in endpoint
    assert endpoint["DriverOpts"] == {"com.docker.network.endpoint.ifname": "eth0"}


def test_connect_rejects_gw_priority_below_gate(mocker: MockerFixture) -> None:
    connect = AsyncMock()
    mocker.patch("agent.api.network_api.RUNTIME_CLIENT.network_connect", connect)
    mocker.patch(
        "agent.api.network_api.RUNTIME_CLIENT._negotiated_api_prefix",
        "/v1.47",
    )

    response = client.post(
        "/api/network/connect",
        json={
            "network": "appnet",
            "container": "web",
            "gateway_priority": 4,
        },
    )

    assert response.status_code == 424
    connect.assert_not_called()
