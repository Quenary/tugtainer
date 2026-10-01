import ssl
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aiohttp import ClientResponseError
from multidict import CIMultiDict, CIMultiDictProxy
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)
from yarl import URL

from backend.const import LOCAL_AGENT_URL, TUGTAINER_HIDDEN_LABEL
from backend.core.agent_client import AgentClient, build_agent_ssl
from backend.exception import TugAgentClientError
from backend.modules.hosts.test_hosts_schemas import TEST_CA_PEM
from backend.util.pinned_ip_resolver import PinnedIpResolver
from shared.schemas.container_schemas import GetContainerListBodySchema


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
    assert "x-tugtainer-timestamp" in kwargs["headers"]
    assert "x-tugtainer-signature" in kwargs["headers"]


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


@pytest.mark.asyncio
async def test_container_list_returns_hidden_container_from_agent(
    mocker: MockerFixture,
):
    hidden = ContainerInspectResult(
        id="h1",
        name="hidden",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "true"}),
    )
    client = AgentClient(id=1, url="https://agent.example.com", secret="secret")
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=[hidden.model_dump(mode="json")]),
    )

    result = await client.container.list(GetContainerListBodySchema(all=True))

    assert [item.name for item in result] == ["hidden"]
    assert (
        result[0].config is not None
        and result[0].config.labels is not None
        and result[0].config.labels[TUGTAINER_HIDDEN_LABEL] == "true"
    )


@pytest.mark.parametrize(
    ("verify", "ca", "expected_type"),
    [
        (True, None, bool),
        (False, TEST_CA_PEM, bool),
        (True, TEST_CA_PEM, ssl.SSLContext),
    ],
)
def test_build_agent_ssl(verify: bool, ca: str | None, expected_type: type):
    result = build_agent_ssl(verify, ca)
    assert isinstance(result, expected_type)
    if expected_type is bool:
        assert result is verify


def _request_session(mocker: MockerFixture, body: str = "{}"):
    mocker.patch(
        "backend.core.agent_client.validate_agent_url_against_ssrf",
        new=AsyncMock(return_value=set()),
    )
    cm = _mock_response(mocker, body)
    session = MagicMock()
    session.closed = False
    session.request = MagicMock(return_value=cm)
    return session, cm


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ssl_verify", "expected_ssl"),
    [
        (True, "context"),
        (False, False),
    ],
)
async def test_request_ssl_follows_host_settings(
    mocker: MockerFixture,
    ssl_verify: bool,
    expected_ssl: str | bool,
):
    session, _cm = _request_session(mocker)
    client = AgentClient(
        id=1,
        url="https://agent.example.com:9413",
        ssl=ssl_verify,
        ssl_ca=TEST_CA_PEM,
    )
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    await client._request("GET", "/api/public/health")

    ssl_arg = session.request.call_args.kwargs["ssl"]
    if expected_ssl == "context":
        assert isinstance(ssl_arg, ssl.SSLContext)
    else:
        assert ssl_arg is False


@pytest.mark.asyncio
async def test_agent_client_swarm_info_and_service(mocker: MockerFixture):
    client = AgentClient(id=1, url=LOCAL_AGENT_URL)
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(
            side_effect=[
                {"cluster_id": "c1", "node_id": "n1", "is_manager": True},
                [
                    {
                        "id": "s1",
                        "name": "nginx",
                        "image": "nginx:latest",
                        "replicas": {"running": 1, "desired": 1},
                    }
                ],
                "s1",
            ]
        ),
    )

    info = await client.common.swarm_info()
    assert info.is_manager is True
    assert info.cluster_id == "c1"

    services = await client.service.list()
    assert len(services) == 1
    assert services[0].name == "nginx"

    from shared.schemas.service_schemas import ServiceUpdateRequestBody

    updated_id = await client.service.update(
        ServiceUpdateRequestBody(service_id="s1", image="nginx:alpine")
    )
    assert updated_id == "s1"


def _response_error(status_code: int = 500) -> ClientResponseError:
    url = URL("https://agent.example.com/api/public/health")
    headers: CIMultiDictProxy[str] = CIMultiDictProxy(CIMultiDict())
    return ClientResponseError(
        aiohttp.RequestInfo(url, "GET", headers, url),
        (),
        status=status_code,
        message="err",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("", None),
        ("not-json", "not-json"),
    ],
)
async def test_request_parses_empty_and_non_json_bodies(
    mocker: MockerFixture,
    body: str,
    expected: str | None,
):
    session, _cm = _request_session(mocker, body)
    client = AgentClient(id=1, url="https://agent.example.com")
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    assert await client._request("GET", "/api/public/health") == expected
    headers = session.request.call_args.kwargs["headers"]
    assert "x-tugtainer-timestamp" in headers
    assert "x-tugtainer-signature" not in headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_body",
    [{"detail": "denied"}, "plain failure"],
)
async def test_request_maps_http_error(
    mocker: MockerFixture, error_body: dict[str, str] | str
):
    session, cm = _request_session(mocker)
    resp = cm.__aenter__.return_value
    resp.status = 500
    resp.raise_for_status.side_effect = _response_error()
    if isinstance(error_body, dict):
        resp.json = AsyncMock(return_value=error_body)
    else:
        resp.json = AsyncMock(side_effect=ValueError("not json"))
        resp.text = AsyncMock(return_value=error_body)

    client = AgentClient(id=1, url="https://agent.example.com", secret="secret")
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    with pytest.raises(TugAgentClientError) as exc_info:
        await client._request("GET", "/api/public/health")

    assert exc_info.value.status == 500
    rendered = str(exc_info.value)
    if isinstance(error_body, dict):
        assert "denied" in rendered
    else:
        assert error_body in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "closes_session"),
    [
        (TimeoutError(), 408, False),
        (aiohttp.ClientConnectionError("refused"), 502, True),
    ],
)
async def test_request_maps_transport_errors(
    mocker: MockerFixture,
    error: Exception,
    status_code: int,
    closes_session: bool,
):
    mocker.patch(
        "backend.core.agent_client.validate_agent_url_against_ssrf",
        new=AsyncMock(return_value=set()),
    )
    cm = AsyncMock()
    cm.__aenter__.side_effect = error
    session = MagicMock()
    session.request = MagicMock(return_value=cm)
    client = AgentClient(id=1, url="https://agent.example.com", secret="secret")
    close = mocker.patch.object(client, "close_session", new=AsyncMock())
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))

    with pytest.raises(TugAgentClientError) as exc_info:
        await client._request("GET", "/api/public/health")

    assert exc_info.value.status == status_code
    if closes_session:
        close.assert_awaited_once()
    else:
        close.assert_not_awaited()
