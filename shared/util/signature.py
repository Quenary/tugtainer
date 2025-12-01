import hmac
import hashlib
import base64
import json
from typing import Any, Literal
import time
from fastapi import HTTPException, status
import logging


X_TIMESTAMP = "x-tugtainer-timestamp"
X_SIGNATURE = "x-tugtainer-signature"


def get_signature_headers(
    secret_key: str | None,
    method: str,
    path: str,
    body: Any,
) -> dict[str, str]:
    """
    Get signature headers
    :param secret_key: AGENT_SECRET
    :param method: method of the req
    :param path: path of the req e.g. /api/containers/list
    :param body: body of the req
    """
    logging.debug(
        f"Getting signature headers for: \n{method} \n{path} \n{body}"
    )
    timestamp = int(time.time())
    headers = {X_TIMESTAMP: str(timestamp)}
    if not secret_key:
        return headers

    signature = _get_req_signature(
        secret_key, timestamp, method, path, body
    )
    headers[X_SIGNATURE] = signature
    logging.debug(f"Signature headers: {headers}")
    return headers


def verify_signature_headers(
    secret_key: str | None,
    signature_ttl: int,
    headers: dict[str, str],
    method: str,
    path: str,
    body: Any,
) -> Literal[True]:
    """
    Verify signature headers
    :param secret_key: AGENT_SECRET
    :param signature_ttl: AGENT_SIGNATURE_TTL
    :param headers:  headers of the request
    :param method: method of the req
    :param path: path of the req e.g. /api/containers/list
    :param body: body of the req
    """
    current_timestamp = int(time.time())
    timestamp = int(headers.get(X_TIMESTAMP, "0"))
    signature = headers.get(X_SIGNATURE, "")
    logging.debug(
        f"Verifying signature headers for:\n{method}\n{path}\n{body}\n{headers}"
    )
    if abs(current_timestamp - timestamp) > signature_ttl:
        message = (
            f"Signature expired (age={current_timestamp - timestamp}s)"
        )
        message = f"""\
Signature expired for:
method={method}
path={path}
body={body}
age={current_timestamp - timestamp}s
current_timestamp={current_timestamp}s
request_timestamp={timestamp}s
"""
        logging.warning(message)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            message,
        )
    if not secret_key:
        return True
    expected = _get_req_signature(
        secret_key, timestamp, method, path, body
    )
    if not hmac.compare_digest(expected, signature):
        message = f"""\
Invalid signature for:
method={method}
path={path}
body={body}
signature={signature}
"""
        logging.warning(message)
        raise HTTPException(401, message)
    return True


def _get_req_signature(
    secret_key: str,
    timestamp: int,
    method: str,
    path: str,
    body: Any,
) -> str:
    if not secret_key:
        return ""
    sig_bytes = (
        method.upper().encode()
        + path.encode()
        + _get_body_bytes(body)
        + str(timestamp).encode()
    )
    return _get_sig_encoded(secret_key, sig_bytes)


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
