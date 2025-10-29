import hmac
import hashlib
import base64
import json
from typing import Any, Literal, Mapping
import time
from fastapi import HTTPException, status


def get_signature_headers(
    secret_key: str | None,
    method: str,
    url: str,
    body: Any,
) -> dict[str, str]:
    """
    Get signature headers
    :param secret_key: AGENT_SECRET
    :param method: method of the req
    :param url: url of the req
    :param body: body of the req
    """
    url = _normalize_url(url)
    timestamp = int(time.time())
    headers = {"X-Timestamp": str(timestamp)}
    if not secret_key:
        return headers

    signature = _get_req_signature(
        secret_key, timestamp, method, url, body
    )
    headers["X-Signature"] = signature
    return headers


def verify_signature_headers(
    secret_key: str | None,
    signature_lifetime: int,
    headers: dict[str, str],
    method: str,
    url: str,
    body: Any,
) -> Literal[True]:
    """
    Verify signature headers
    :param secret_key: AGENT_SECRET
    :param signature_lifetime: AGENT_SIGNATURE_LIFETIME
    :param headers:  headers of the request
    :param method: method of the req
    :param url: url of the req
    :param body: body of the req
    """
    url = _normalize_url(url)
    timestamp = int(headers.get("x-timestamp", "0"))
    signature = headers.get("x-signature", "")
    if abs(time.time() - timestamp) > signature_lifetime:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Signature lifetime expired (age={int(time.time() - timestamp)}s)",
        )
    if not secret_key:
        return True
    expected = _get_req_signature(
        secret_key, timestamp, method, url, body
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid signature")
    return True


def _get_req_signature(
    secret_key: str,
    timestamp: int,
    method: str,
    url: str,
    body: Any,
) -> str:
    if not secret_key:
        return ""
    url = _normalize_url(url)
    sig_bytes = (
        method.upper().encode()
        + url.encode()
        + _get_body_bytes(body)
        + str(timestamp).encode()
    )
    return _get_sig_encoded(secret_key, sig_bytes)


def _normalize_url(url: str) -> str:
    return "/" + url.lstrip("/")


def _get_sig_encoded(secret_key: str, sig_bytes: bytes) -> str:
    return base64.b64encode(
        hmac.new(
            secret_key.encode(), sig_bytes, hashlib.sha256
        ).digest()
    ).decode()


def _get_body_bytes(body: Any) -> bytes:
    return (
        b""
        if not body
        else json.dumps(body, separators=(",", ":")).encode()
    )
