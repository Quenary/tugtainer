import base64
import binascii
import json
import logging
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

from shared.runtime.runtime_client import docker_config_dir, split_image_ref

logger: Final = logging.getLogger("runtime.auth")

_DOCKER_HUB_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "docker.io",
        "index.docker.io",
        "registry-1.docker.io",
    }
)
_helper_warning_logged = False


def normalize_registry_host(value: str) -> str:
    """
    Normalize a docker config auth key or image registry to host[:port].

    URL-form keys such as https://ghcr.io/v1/ become ghcr.io.
    Docker Hub aliases (docker.io, index.docker.io, registry-1.docker.io)
    canonicalise to registry-1.docker.io.
    """
    raw = value.strip()
    if not raw:
        return ""

    parsed = urlparse(raw if "://" in raw else f"//{raw}")
    host = (parsed.hostname or "").casefold()
    if not host:
        return ""

    if host in _DOCKER_HUB_HOSTS:
        return "registry-1.docker.io"

    if ":" in host:
        host = f"[{host}]"

    port = parsed.port
    if port is not None:
        return f"{host}:{port}"
    return host


def image_registry_host(spec: str) -> str:
    """Registry host of an image reference. Docker Hub names map to docker.io."""
    repo, _, _ = split_image_ref(spec)
    first = repo.split("/", 1)[0]
    if first and ("." in first or ":" in first or first == "localhost"):
        return first
    return "docker.io"


def registry_auth_for_image(
    image: str,
    config_dir: Path | None = None,
) -> dict[str, str] | None:
    """
    Credentials for the engine X-Registry-Auth header.

    Reads auths from config.json. credsStore and credHelpers are ignored.
    """
    data = _load_config(config_dir)
    _warn_unsupported_helpers(data)
    auths = data.get("auths")
    if not isinstance(auths, dict):
        return None
    target = normalize_registry_host(image_registry_host(image))
    if not target:
        return None
    for key, entry in auths.items():
        if not isinstance(key, str) or normalize_registry_host(key) != target:
            continue
        if not isinstance(entry, dict):
            return None
        return _auth_config(key, entry)
    return None


def _load_config(config_dir: Path | None) -> dict[str, Any]:
    path = (config_dir or docker_config_dir()) / "config.json"
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError:
        logger.warning("Docker config is not readable: %s", path)
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Docker config is not valid JSON: %s", path)
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _warn_unsupported_helpers(data: dict[str, Any]) -> None:
    global _helper_warning_logged
    if _helper_warning_logged:
        return
    if not data.get("credsStore") and not data.get("credHelpers"):
        return
    logger.warning(
        "Docker credential helpers (credsStore, credHelpers) are not supported; "
        "only auths entries in config.json are used"
    )
    _helper_warning_logged = True


def _auth_config(serveraddress: str, entry: dict[str, Any]) -> dict[str, str] | None:
    identity_token = entry.get("identitytoken")
    if isinstance(identity_token, str) and identity_token.strip():
        return {
            "identitytoken": identity_token.strip(),
            "serveraddress": serveraddress,
        }
    username = entry.get("username")
    password = entry.get("password")
    if isinstance(username, str) and isinstance(password, str):
        return {
            "username": username,
            "password": password,
            "serveraddress": serveraddress,
        }
    auth = entry.get("auth")
    if not isinstance(auth, str) or not auth.strip():
        return None
    decoded = _decode_auth(auth.strip())
    if decoded is None:
        logger.warning("Docker config auth for %s is not valid base64", serveraddress)
        return None
    user, secret = decoded
    return {
        "username": user,
        "password": secret,
        "serveraddress": serveraddress,
    }


def _decode_auth(auth: str) -> tuple[str, str] | None:
    padded = auth + "=" * (-len(auth) % 4)
    try:
        raw = base64.b64decode(padded, validate=False).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    username, sep, password = raw.partition(":")
    if not sep:
        return None
    return username, password
