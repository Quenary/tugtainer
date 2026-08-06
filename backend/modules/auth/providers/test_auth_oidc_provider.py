import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import rsa
from fastapi import HTTPException, status
from jose import JWTError, jwt

from backend.config import Config
from backend.modules.auth.providers.auth_oidc_provider import AuthOidcProvider


def _base64url_uint(value: int) -> str:
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def signing_key():
    return rsa.newkeys(2048)


@pytest.fixture
def discovery_doc():
    return {
        "issuer": "https://idp.example.com",
        "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
        "id_token_signing_alg_values_supported": ["RS256"],
    }


def _jwk(signing_key, kid: str = "signing-key") -> dict[str, str]:
    public_key, _ = signing_key
    return {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _base64url_uint(public_key.n),
        "e": _base64url_uint(public_key.e),
    }


def _id_token(signing_key, **claim_overrides) -> str:
    _, private_key = signing_key
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
    return jwt.encode(
        claims,
        private_key.save_pkcs1(),
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
    other_key = rsa.newkeys(2048)
    provider = AuthOidcProvider()
    provider._fetch_oidc_jwks = AsyncMock(return_value={"keys": [_jwk(other_key)]})

    with pytest.raises(JWTError):
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

    with pytest.raises(JWTError):
        await provider._verify_oidc_id_token(
            _id_token(signing_key, aud="another-client"),
            None,
            discovery_doc,
            "tugtainer",
        )


@pytest.mark.parametrize(
    "allowed_emails, allowed_subjects, claims",
    [
        (set(), set(), {"email": "anyone@example.com", "sub": "anyone"}),
        ({"admin@example.com"}, set(), {"email": "ADMIN@example.com", "sub": "x"}),
        (set(), {"subject-123"}, {"email": "other@example.com", "sub": "subject-123"}),
    ],
)
def test_oidc_identity_allowlist_accepts_matching_identity(
    monkeypatch, allowed_emails, allowed_subjects, claims
):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", allowed_emails)
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", allowed_subjects)

    AuthOidcProvider()._enforce_oidc_identity_allowlist(claims)


def test_oidc_identity_allowlist_rejects_unlisted_identity(monkeypatch):
    monkeypatch.setattr(Config, "OIDC_ALLOWED_EMAILS", {"admin@example.com"})
    monkeypatch.setattr(Config, "OIDC_ALLOWED_SUBJECTS", {"subject-123"})

    with pytest.raises(HTTPException) as exc_info:
        AuthOidcProvider()._enforce_oidc_identity_allowlist(
            {"email": "user@example.com", "sub": "subject-456"}
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
