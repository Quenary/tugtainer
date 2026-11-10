import base64
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from urllib.parse import urlencode

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from fastapi import HTTPException, Response, status
from jwt.exceptions import InvalidTokenError
from starlette.requests import Request

from backend.config import Config
from backend.modules.auth.providers.auth_oidc_provider import AuthOidcProvider


def _base64url_uint(value: int) -> str:
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def discovery_doc():
    return {
        "issuer": "https://idp.example.com",
        "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
        "id_token_signing_alg_values_supported": ["RS256"],
    }


def _jwk(signing_key, kid: str = "signing-key") -> dict[str, str]:
    public_numbers = signing_key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _base64url_uint(public_numbers.n),
        "e": _base64url_uint(public_numbers.e),
    }


def _id_token(signing_key, **claim_overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": "https://idp.example.com",
        "sub": "user-123",
        "aud": "tugtainer",
        "email": "user@example.com",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **claim_overrides,
    }
    pem = signing_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        NoEncryption(),
    )
    return jwt.encode(
        claims,
        pem,
        algorithm="RS256",
        headers={"kid": "signing-key"},
    )


@pytest.mark.asyncio
async def test_verify_oidc_id_token_validates_signature_and_claims(
    signing_key, discovery_doc
):
    provider = AuthOidcProvider()
    provider._fetch_oidc_jwks = AsyncMock(return_value={"keys": [_jwk(signing_key)]})

    claims = await provider._verify_oidc_id_token(
        _id_token(signing_key),
        None,
        discovery_doc,
        "tugtainer",
    )

    assert claims["sub"] == "user-123"
    provider._fetch_oidc_jwks.assert_awaited_once_with(discovery_doc["jwks_uri"])


@pytest.mark.asyncio
async def test_verify_oidc_id_token_rejects_wrong_signing_key(
    signing_key, discovery_doc
):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider = AuthOidcProvider()
    provider._fetch_oidc_jwks = AsyncMock(return_value={"keys": [_jwk(other_key)]})

    with pytest.raises(InvalidTokenError):
        await provider._verify_oidc_id_token(
            _id_token(signing_key),
            None,
            discovery_doc,
            "tugtainer",
        )


@pytest.mark.asyncio
async def test_verify_oidc_id_token_rejects_wrong_audience(signing_key, discovery_doc):
    provider = AuthOidcProvider()
    provider._fetch_oidc_jwks = AsyncMock(return_value={"keys": [_jwk(signing_key)]})

    with pytest.raises(InvalidTokenError):
        await provider._verify_oidc_id_token(
            _id_token(signing_key, aud="another-client"),
            None,
            discovery_doc,
            "tugtainer",
        )


def _at_hash(access_token: str) -> str:
    digest = hashlib.sha256(access_token.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest[:16]).rstrip(b"=").decode("ascii")


@pytest.mark.asyncio
async def test_verify_oidc_id_token_checks_access_token_hash(
    signing_key, discovery_doc
):
    provider = AuthOidcProvider()
    provider._fetch_oidc_jwks = AsyncMock(return_value={"keys": [_jwk(signing_key)]})
    access_token = "access-token-value"

    claims = await provider._verify_oidc_id_token(
        _id_token(signing_key, at_hash=_at_hash(access_token)),
        access_token,
        discovery_doc,
        "tugtainer",
    )

    assert claims["sub"] == "user-123"

    with pytest.raises(InvalidTokenError):
        await provider._verify_oidc_id_token(
            _id_token(signing_key, at_hash=_at_hash(access_token)),
            "different-access-token",
            discovery_doc,
            "tugtainer",
        )


_MISSING = object()


@pytest.mark.parametrize(
    "allowed_emails, allowed_subjects, claims",
    [
        (set(), set(), {"email": "anyone@example.com", "sub": "anyone"}),
        (
            {"admin@example.com"},
            set(),
            {"email": "ADMIN@example.com", "sub": "x", "email_verified": True},
        ),
        (set(), {"subject-123"}, {"email": "other@example.com", "sub": "subject-123"}),
    ],
)
def test_oidc_identity_allowlist_accepts_matching_identity(
    monkeypatch, allowed_emails, allowed_subjects, claims
):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", allowed_emails)
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", allowed_subjects)

    AuthOidcProvider()._enforce_oidc_identity_allowlist(claims)


def test_oidc_identity_allowlist_rejects_unlisted_identity(monkeypatch, caplog):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", {"subject-123"})

    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as exc_info:
            AuthOidcProvider()._enforce_oidc_identity_allowlist(
                {"email": "user@example.com", "sub": "subject-456"}
            )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "OIDC identity is not allowed"
    assert not any("not verified" in record.message for record in caplog.records)


@pytest.mark.parametrize("email_verified", [True, "true", "TRUE", "True"])
def test_oidc_identity_allowlist_accepts_verified_email(monkeypatch, email_verified):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", set())

    AuthOidcProvider()._enforce_oidc_identity_allowlist(
        {
            "email": "admin@example.com",
            "sub": "not-listed",
            "email_verified": email_verified,
        }
    )


@pytest.mark.parametrize(
    "email_verified",
    [False, "false", "FALSE", None, 0, 1, "yes", " true", _MISSING],
)
def test_oidc_identity_allowlist_rejects_unverified_email(
    monkeypatch, caplog, email_verified
):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", set())
    claims: dict[str, object] = {
        "email": "admin@example.com",
        "sub": "not-listed",
        "access_token": "secret-token-value",
        "id_token": "header.payload.signature",
    }
    if email_verified is not _MISSING:
        claims["email_verified"] = email_verified

    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as exc_info:
            AuthOidcProvider()._enforce_oidc_identity_allowlist(claims)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "OIDC identity is not allowed"
    assert any("not verified" in record.message for record in caplog.records)
    logged = " ".join(record.message for record in caplog.records)
    assert "secret-token-value" not in logged
    assert "header.payload.signature" not in logged


def test_oidc_identity_allowlist_allows_unverified_email_with_listed_subject(
    monkeypatch, caplog
):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", {"subject-123"})

    with caplog.at_level(logging.WARNING):
        AuthOidcProvider()._enforce_oidc_identity_allowlist(
            {
                "email": "admin@example.com",
                "sub": "subject-123",
                "email_verified": False,
            }
        )

    assert not any("not verified" in record.message for record in caplog.records)


def test_oidc_identity_allowlist_allows_unverified_email_when_lists_are_empty(
    monkeypatch,
):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", set())
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", set())

    AuthOidcProvider()._enforce_oidc_identity_allowlist(
        {
            "email": "admin@example.com",
            "sub": "anyone",
            "email_verified": False,
        }
    )


def _oidc_callback_request(state: str = "state-value") -> Request:
    query = urlencode({"code": "auth-code", "state": state})
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/auth/oidc/callback",
        "raw_path": b"/auth/oidc/callback",
        "query_string": query.encode(),
        "headers": [(b"cookie", f"oidc_state={state}".encode())],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_oidc_callback_rejects_unverified_email_without_session_cookies(
    monkeypatch,
):
    monkeypatch.setattr(Config, "OIDC_ENABLED", True)
    monkeypatch.setattr(Config, "DISABLE_AUTH", False)
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", set())

    provider = AuthOidcProvider()
    provider._fetch_oidc_discovery = AsyncMock(return_value={})
    provider._exchange_oidc_code = AsyncMock(
        return_value={
            "access_token": "idp-access-token",
            "id_token_claims": {
                "email": "admin@example.com",
                "sub": "user-123",
                "email_verified": False,
            },
        }
    )
    provider._set_cookies = Mock()
    response = Response()

    with pytest.raises(HTTPException) as exc_info:
        await provider.callback(_oidc_callback_request(), response)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "OIDC identity is not allowed"
    provider._set_cookies.assert_not_called()
    set_cookie = " ".join(response.headers.getlist("set-cookie"))
    assert "access_token=" not in set_cookie
    assert "refresh_token=" not in set_cookie
