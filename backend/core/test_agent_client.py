import ssl
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.agent_client import AgentClient, build_agent_ssl
from backend.modules.hosts.test_hosts_schemas import TEST_CA_PEM
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


def test_build_agent_ssl_default_verify():
    assert build_agent_ssl(True) is True
    assert build_agent_ssl(True, None) is True


def test_build_agent_ssl_disabled_ignores_ca():
    assert build_agent_ssl(False, TEST_CA_PEM) is False


def test_build_agent_ssl_with_ca_returns_context():
    context = build_agent_ssl(True, TEST_CA_PEM)
    assert isinstance(context, ssl.SSLContext)


@pytest.mark.asyncio
async def test_request_uses_ssl_context_when_ca_set(
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
        ssl=True,
        ssl_ca=TEST_CA_PEM,
    )
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    await client._request("GET", "/api/public/health")

    kwargs = session.request.call_args.kwargs
    assert isinstance(kwargs["ssl"], ssl.SSLContext)


@pytest.mark.asyncio
async def test_request_disables_ssl_even_with_ca(
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
        ssl=False,
        ssl_ca=TEST_CA_PEM,
    )
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    await client._request("GET", "/api/public/health")

    assert session.request.call_args.kwargs["ssl"] is False
