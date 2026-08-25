from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.agent_client import AgentClient
from backend.util.pinned_ip_resolver import PinnedIpResolver


def _mock_response(mocker: MockerFixture, body: str = "{}"):
    resp = MagicMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.text = AsyncMock(return_value=body)
    resp.json = AsyncMock(return_value={})
    cm = AsyncMock()
    cm.__aenter__.return_value = resp
    cm.__aexit__.return_value = False
    return cm


@pytest.mark.asyncio
async def test_request_keeps_hostname_and_disables_redirects(
    mocker: MockerFixture,
):
    mocker.patch(
        "backend.core.agent_client.validate_agent_url_against_ssrf",
        new=AsyncMock(return_value=set()),
    )
    cm = _mock_response(mocker)
    session = MagicMock()
    session.closed = False
    session.request = MagicMock(return_value=cm)

    client = AgentClient(
        id=1,
        url="https://agent.example.com:9413",
        secret="secret",
    )
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    result = await client._request("GET", "/api/public/health")

    assert result == {}
    args, kwargs = session.request.call_args
    assert args[0] == "GET"
    assert args[1] == "https://agent.example.com:9413/api/public/health"
    assert kwargs["allow_redirects"] is False
    assert kwargs["ssl"] is True


@pytest.mark.asyncio
async def test_session_uses_pinned_resolver_without_dns_cache():
    client = AgentClient(id=1, url="https://agent.example.com")
    session = await client._get_session()
    try:
        connector = session.connector
        assert connector is not None
        assert connector._use_dns_cache is False
        assert isinstance(connector._resolver, PinnedIpResolver)
        assert connector._resolver._url == "https://agent.example.com"
        assert connector._resolver._hostname == "agent.example.com"
    finally:
        await client.close_session()
