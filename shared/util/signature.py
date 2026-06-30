import base64
import hashlib
import hmac
import logging
import textwrap
import time
from typing import Any, Final, Literal

from aiohttp.typedefs import Query
from fastapi import HTTPException, status

from shared.util.custom_json_dumps import custom_json_dumps

X_TIMESTAMP = "x-tugtainer-timestamp"
X_SIGNATURE = "x-tugtainer-signature"


def get_signature_headers(
    secret_key: str | None,
    method: str,
    path: str,
    body: Any = None,
    params: Query | None = None,
) -> dict[str, str]:
    """
    Get signature headers
    :param secret_key: AGENT_SECRET
    :param method: method of the req
    :param path: path of the req e.g. /api/containers/list
    :param body: body of the req
    """
    logging.debug(
        f"Getting signature headers for: \n{method} \n{path} \n{body} \n{params}"
    )

    timestamp: Final[int] = int(time.time())
    headers: Final[dict[str, str]] = {X_TIMESTAMP: str(timestamp)}

    if secret_key:
        signature: Final[str] = _get_req_signature(
            secret_key, timestamp, method, path, body, params
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
    body: Any = None,
    params: Query | None = None,
) -> Literal[True]:
    """
    Verify signature headers
    :param secret_key: AGENT_SECRET
    :param signature_ttl: AGENT_SIGNATURE_TTL
    :param headers:  headers of the request
    :param method: method of the req
    :param path: path of the req e.g. /api/containers/list
    :param body: body of the req
    :param params: query parameters of the req
    """
    logging.debug(
        f"Verifying signature headers for:\n{method}\n{path}\n{body}\n{params}\n{headers}"
    )

    if not secret_key:
        message = "AGENT_SECRET is not set, cannot verify request signature"
        logging.warning(message)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            message,
        )

    if not headers.get(X_TIMESTAMP):
        message = f"{X_TIMESTAMP} header is missing, cannot verify request signature"
        logging.warning(message)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            message,
        )

    if not headers.get(X_SIGNATURE):
        message = f"{X_SIGNATURE} header is missing, cannot verify request signature"
        logging.warning(message)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            message,
        )

    current_timestamp: Final[int] = int(time.time())
    timestamp: Final[int] = int(headers.get(X_TIMESTAMP, "0"))
    signature: Final[str] = headers.get(X_SIGNATURE, "")

    if abs(current_timestamp - timestamp) > signature_ttl:
        message = textwrap.dedent(f"""\
            Signature expired for:
            method={method}
            path={path}
            body={body}
            params={params}
            age={current_timestamp - timestamp}s
            current_timestamp={current_timestamp}s
            request_timestamp={timestamp}s""")
        logging.warning(message)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            message,
        )

    expected = _get_req_signature(secret_key, timestamp, method, path, body, params)
    if not hmac.compare_digest(expected, signature):
        message = textwrap.dedent(f"""\
            Invalid signature for:
            method={method}
            path={path}
            body={body}
            params={params}
            signature={signature}""")
        logging.warning(message)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, message)

    return True


def _get_req_signature(
    secret_key: str,
    timestamp: int,
    method: str,
    path: str,
    body: Any = None,
    params: Query | None = None,
) -> str:
    if not secret_key:
        return ""
    sig_bytes = (
        method.upper().encode()
        + path.encode()
        + _get_obj_bytes(body)
        + _get_obj_bytes(params)
        + str(timestamp).encode()
    )
    return _get_sig_encoded(secret_key, sig_bytes)


def _get_sig_encoded(secret_key: str, sig_bytes: bytes) -> str:
    return base64.b64encode(
        hmac.new(secret_key.encode(), sig_bytes, hashlib.sha256).digest()
    ).decode()


def _get_obj_bytes(obj: Any) -> bytes:
    return b"" if not obj else custom_json_dumps(obj).encode()
