from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from agent.app import app
from agent.auth import verify_signature

client = TestClient(app)


def _request(
    *,
    method: str = "POST",
    path: str = "/api/container/list",
    json_body: object | None = None,
    raw_body: bytes = b"",
    json_error: BaseException | None = None,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    req = MagicMock()
    req.method = method
    req.url.path = path
    req.headers = headers or {}
    req.query_params = {} if query is None else query
    if json_error is None:
        req.json = AsyncMock(return_value={} if json_body is None else json_body)
    else:
        req.json = AsyncMock(side_effect=json_error)
    req.body = AsyncMock(return_value=raw_body)
    return req


@pytest.mark.asyncio
async def test_verify_signature_skips_when_unauthenticated_allowed(
    mocker: MockerFixture,
):
    mocker.patch("agent.auth.Config.ALLOW_UNAUTHENTICATED_AGENT", True)
    verify = mocker.patch("agent.auth.verify_signature_headers")
    req = _request()

    await verify_signature(req)

    verify.assert_not_called()
    req.json.assert_not_called()


@pytest.mark.asyncio
async def test_verify_signature_passes_json_body(mocker: MockerFixture):
    mocker.patch("agent.auth.Config.ALLOW_UNAUTHENTICATED_AGENT", False)
    mocker.patch("agent.auth.Config.AGENT_SECRET", "secret")
    mocker.patch("agent.auth.Config.AGENT_SIGNATURE_TTL", 5)
    verify = mocker.patch("agent.auth.verify_signature_headers")
    req = _request(
        json_body={"image": "nginx"},
        headers={"x-tugtainer-signature": "sig"},
    )

    await verify_signature(req)

    verify.assert_called_once_with(
        secret_key="secret",
        signature_ttl=5,
        headers={"x-tugtainer-signature": "sig"},
        method="POST",
        path="/api/container/list",
        body={"image": "nginx"},
        params=None,
    )
    req.body.assert_not_called()


@pytest.mark.asyncio
async def test_verify_signature_decodes_non_json_body_and_query(
    mocker: MockerFixture,
):
    mocker.patch("agent.auth.Config.ALLOW_UNAUTHENTICATED_AGENT", False)
    mocker.patch("agent.auth.Config.AGENT_SECRET", "secret")
    mocker.patch("agent.auth.Config.AGENT_SIGNATURE_TTL", 9)
    verify = mocker.patch("agent.auth.verify_signature_headers")
    req = _request(
        method="GET",
        path="/api/service/logs/svc1",
        json_error=ValueError("not json"),
        raw_body=b"plain\xff",
        query={"tail": "10"},
    )

    await verify_signature(req)

    verify.assert_called_once_with(
        secret_key="secret",
        signature_ttl=9,
        headers={},
        method="GET",
        path="/api/service/logs/svc1",
        body="plain\ufffd",
        params={"tail": "10"},
    )


def test_access_rejects_missing_signature(mocker: MockerFixture):
    mocker.patch("agent.auth.Config.ALLOW_UNAUTHENTICATED_AGENT", False)
    mocker.patch("agent.auth.Config.AGENT_SECRET", None)

    response = client.get("/api/public/access")

    assert response.status_code == 401
