from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Response
from pytest_mock import MockerFixture

from backend.core.agent_protocol import agent_protocol_error
from backend.exception import TugAgentClientError
from backend.modules.hosts.hosts_router import get_status
from shared.agent_protocol import AGENT_UPGRADE_MESSAGE, AgentProtocol


def _error(status_code: int) -> TugAgentClientError:
    return TugAgentClientError(
        "Agent request error", "http://agent", "GET", status_code, ""
    )


@pytest.mark.asyncio
async def test_matching_protocol_is_accepted() -> None:
    client = MagicMock()
    client.public.version = AsyncMock(
        return_value=AgentProtocol(version="2.0.0", protocol=2)
    )

    assert await agent_protocol_error(client) is None


@pytest.mark.asyncio
async def test_other_protocol_requires_upgrade() -> None:
    client = MagicMock()
    client.public.version = AsyncMock(
        return_value=AgentProtocol(version="1.45.2", protocol=1)
    )

    assert await agent_protocol_error(client) == AGENT_UPGRADE_MESSAGE


@pytest.mark.asyncio
async def test_missing_version_route_requires_upgrade() -> None:
    client = MagicMock()
    client.public.version = AsyncMock(side_effect=_error(404))

    assert await agent_protocol_error(client) == AGENT_UPGRADE_MESSAGE


@pytest.mark.asyncio
async def test_connection_failure_is_not_an_upgrade_error() -> None:
    client = MagicMock()
    client.public.version = AsyncMock(side_effect=_error(502))

    with pytest.raises(TugAgentClientError, match="Agent request error") as exc_info:
        await agent_protocol_error(client)

    assert AGENT_UPGRADE_MESSAGE not in str(exc_info.value)


def _host() -> MagicMock:
    host = MagicMock()
    host.id = 1
    host.enabled = True
    host.is_swarm = False
    host.swarm_cluster_id = None
    return host


@pytest.mark.asyncio
async def test_status_reports_upgrade(mocker: MockerFixture) -> None:
    mocker.patch(
        "backend.modules.hosts.hosts_router.get_host",
        new=AsyncMock(return_value=_host()),
    )
    client = MagicMock()
    client.public.health = AsyncMock(return_value="OK")
    client.public.access = AsyncMock(return_value="OK")
    client.public.version = AsyncMock(side_effect=_error(404))
    mocker.patch(
        "backend.modules.hosts.hosts_router.AgentClientManager.get_host_client",
        return_value=client,
    )

    body = await get_status(1, Response(), session=AsyncMock())

    assert body.ok is False
    assert body.err == AGENT_UPGRADE_MESSAGE


@pytest.mark.asyncio
async def test_status_keeps_connection_errors(mocker: MockerFixture) -> None:
    mocker.patch(
        "backend.modules.hosts.hosts_router.get_host",
        new=AsyncMock(return_value=_host()),
    )
    client = MagicMock()
    client.public.health = AsyncMock(side_effect=_error(502))
    mocker.patch(
        "backend.modules.hosts.hosts_router.AgentClientManager.get_host_client",
        return_value=client,
    )

    body = await get_status(1, Response(), session=AsyncMock())

    assert body.ok is False
    assert body.err is not None
    assert AGENT_UPGRADE_MESSAGE not in body.err
