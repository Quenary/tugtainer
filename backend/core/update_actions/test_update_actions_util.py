from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.core.agent_client import AgentClient, AgentClientNetwork
from backend.core.update_actions.update_actions_util import (
    disconnect_all_networks,
)
from shared.schemas.network_schemas import NetworkDisconnectBodySchema


def _container(
    name: str = "app",
    networks: dict | None = None,
):
    return SimpleNamespace(
        name=name,
        network_settings=SimpleNamespace(networks=networks),
    )


@pytest.mark.asyncio
async def test_disconnect_all_networks_disconnects_each_network():
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    container = _container(networks={"stacka_shared": {}, "proxy": {}})

    await disconnect_all_networks(client, container, True)

    assert client.network.disconnect.call_count == 2
    called_networks = {
        call.args[0].network for call in client.network.disconnect.call_args_list
    }
    assert called_networks == {"stacka_shared", "proxy"}
    for call in client.network.disconnect.call_args_list:
        body = call.args[0]
        assert isinstance(body, NetworkDisconnectBodySchema)
        assert body.container == "app"
        assert body.force is True


@pytest.mark.asyncio
async def test_disconnect_all_networks_logs_failure_and_continues(caplog):
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    client.network.disconnect.side_effect = [
        Exception("network in use"),
        None,
    ]
    container = _container(networks={"owned": {}, "proxy": {}})

    await disconnect_all_networks(client, container, True)

    assert client.network.disconnect.call_count == 2
    assert "Failed to disconnect app from network owned" in caplog.text
    assert "network in use" in caplog.text


@pytest.mark.asyncio
async def test_disconnect_all_networks_noop_without_networks():
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    container = _container(networks=None)

    await disconnect_all_networks(client, container, True)

    client.network.disconnect.assert_not_called()
