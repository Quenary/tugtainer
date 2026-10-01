import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal, cast
from urllib.parse import urlencode, urlparse

import aiohttp
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.core.container_util.container_labels import (
    get_container_auto_check_label,
)
from backend.docker_config import DockerConfig, normalize_registry_host
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.get_version_from_labels import get_version_from_labels


def filter_containers_by_check_enabled(
    containers: list[ContainerInspectResult],
    containers_db_map: dict[str, ContainersModel],
) -> list[ContainerInspectResult]:
    _containers: list[ContainerInspectResult] = []
    for c in containers:
        lbl = get_container_auto_check_label(c)
        if lbl is not None:
            if lbl:
                _containers.append(c)
            continue
        c_db = containers_db_map.get(cast(str, c.name))
        if c_db and c_db.check_enabled:
            _containers.append(c)
    return _containers


def sort_containers_by_checked_at(
    containers: list[ContainerInspectResult],
    containers_db_map: dict[str, ContainersModel],
) -> list[ContainerInspectResult]:
    """
    Sort containers by checked_at date
    (from earliest to latest)
    """
    return sorted(
        containers,
        key=lambda c: (
            (c_db := containers_db_map.get(cast(str, c.name))) is not None
            and c_db.checked_at is not None,
            (c_db.checked_at if c_db and c_db.checked_at else datetime.min),
        ),
    )


async def get_image_remote_digest(
    spec: str,
    local_digest: str | None = None,
) -> str | None:
    """
    Get image digest from registry using HEAD request.
    :param spec: image spec e.g. ghcr.io/quenary/tugtainer:1
    :param local_digest: local digest to utilize If-None-Match 304 response
    :return: new image digest if any or local_digest
    """
    logger: Final = logging.getLogger("get_image_remote_digest")
    registry, repo, tag = parse_image_spec(spec)

    insecure_registries = SettingsStorage.get(ESettingKey.INSECURE_REGISTRIES)
    logger.debug(f"Insecure Registries: {insecure_registries}")

    insecure = is_insecure_registry(registry, insecure_registries)

    schemes: list[str] = ["https"]
    if insecure:
        schemes.append("http")
    ssl = not insecure

    logger.info(
        f"Checking registry: {registry}, repo: {repo}, tag: {tag}, insecure: {insecure}"
    )

    headers = {
        "Accept": ",".join(
            [
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            ]
        )
    }

    if local_digest:
        local_digest = local_digest.split("@")[-1]
        headers["If-None-Match"] = local_digest

    docker_config = DockerConfig()
    basic_token = docker_config.get_basic_token(registry)

    def _on_resp(resp: aiohttp.ClientResponse) -> str | None:
        logger.debug(resp)
        resp.raise_for_status()
        if resp.status == 304:
            return local_digest
        return resp.headers.get("Docker-Content-Digest") or resp.headers.get("Etag")

    async def _do_request(
        session: aiohttp.ClientSession,
        url: str,
        headers: dict,
        ssl: bool = True,
    ):
        async with session.head(url, headers=headers, ssl=ssl) as resp:
            logger.debug(resp)

            if resp.status in (401, 403):
                logger.info(f"Registry responded with {resp.status}, trying auth")

                auth_header = resp.headers.get("WWW-Authenticate", "")
                auth_applied = False

                if "Bearer" in auth_header:
                    logger.info(f"Trying Bearer token flow with: {auth_header}")
                    bearer_token = await get_registry_bearer_token(
                        session,
                        auth_header,
                        repo,
                        basic_token,
                        ssl,
                        insecure,
                    )
                    headers["Authorization"] = f"Bearer {bearer_token}"
                    auth_applied = True
                elif basic_token:
                    logger.info("Fallback to Basic auth")
                    headers["Authorization"] = f"Basic {basic_token}"
                    auth_applied = True

                if auth_applied:
                    async with session.head(url, headers=headers, ssl=ssl) as resp2:
                        return _on_resp(resp2)

            return _on_resp(resp)

    async with aiohttp.ClientSession(trust_env=True) as session:
        last_error: Exception | None = None

        for scheme in schemes:
            url = f"{scheme}://{registry}/v2/{repo}/manifests/{tag}"

            logger.info(f"Trying {url}")

            try:
                attempt_headers = dict(headers)
                return await _do_request(session, url, attempt_headers, ssl)
            except (
                aiohttp.ClientSSLError,
                aiohttp.ClientConnectorError,
            ) as e:
                logger.warning(f"Error on {scheme}: {e}")
                last_error = e

        if last_error:
            raise last_error

        return None


def parse_image_spec(spec: str) -> tuple[str, str, str]:
    """
    Convert spec to registry, repo, tag
    """
    tag = "latest"

    if ":" in spec and "/" in spec and spec.rfind(":") > spec.rfind("/"):
        spec, tag = spec.rsplit(":", 1)
    elif ":" in spec and spec.count(":") == 1 and "/" not in spec:
        spec, tag = spec.rsplit(":", 1)

    parts = spec.split("/")

    if "." in parts[0] or ":" in parts[0] or parts[0] == "localhost":
        registry = parts[0]
        repo = "/".join(parts[1:])
    else:
        registry = "registry-1.docker.io"
        repo = spec

    # Docker Hub website hosts are not the Registry API endpoint.
    # https://docs.docker.com/reference/api/registry/latest/
    if registry in {"docker.io", "index.docker.io"}:
        registry = "registry-1.docker.io"

    if registry == "registry-1.docker.io" and "/" not in repo:
        repo = f"library/{repo}"

    return registry, repo, tag


def is_insecure_registry(
    registry: str,
    insecure_registries: str | None,
) -> bool:
    """
    True if registry host[:port] exactly matches an INSECURE_REGISTRIES entry.
    """
    if not insecure_registries:
        return False
    target = normalize_registry_host(registry)
    if not target:
        return False
    return any(
        normalize_registry_host(line) == target
        for line in insecure_registries.splitlines()
    )


def _validate_bearer_realm(realm: str, insecure: bool) -> None:
    parsed = urlparse(realm)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Invalid Bearer realm URL: {realm}")
    if parsed.scheme == "http" and not insecure:
        raise ValueError("HTTP Bearer realm is only allowed for insecure registries")


async def get_registry_bearer_token(
    session: aiohttp.ClientSession,
    auth_header: str,
    repo: str,
    basic_token: str | None = None,
    ssl: bool = True,
    insecure: bool = False,
) -> str:
    """
    Get registry bearer token
    :param session: aiohttp session
    :param auth_header: WWW-Authenticate header value
        e.g. Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"
    :param repo: repo name
    :param basic_token: basic token
    :param ssl: ssl flag for request
    :param insecure: whether the image registry is in INSECURE_REGISTRIES
    :return: token
    """

    parts = auth_header.replace("Bearer ", "")
    items = dict(item.split("=", 1) for item in parts.replace('"', "").split(","))

    realm = items.get("realm")
    if not realm:
        raise ValueError("Bearer realm is missing from WWW-Authenticate header")
    _validate_bearer_realm(realm, insecure)

    service = items.get("service")
    scope = items.get("scope") or f"repository:{repo}:pull"

    params = {"service": service, "scope": scope}

    url = f"{realm}?{urlencode(params)}"

    headers = {}

    if basic_token:
        headers["Authorization"] = f"Basic {basic_token}"

    async with session.get(
        url,
        headers=headers,
        ssl=ssl,
        allow_redirects=False,
    ) as resp:
        resp.raise_for_status()
        data: dict[str, Any] = await resp.json()
        return data.get("token") or data.get("access_token") or ""


_MANIFEST_ACCEPT: Final = ",".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)
_CONFIG_ACCEPT: Final = ",".join(
    [
        "application/vnd.oci.image.config.v1+json",
        "application/vnd.docker.container.image.v1+json",
    ]
)
_INDEX_MEDIA_TYPES: Final = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}
_OCI_CREATED_RE: Final = re.compile(
    r"^(?P<head>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})"
    r"(?:\.(?P<frac>\d+))?"
    r"(?P<tz>Z|[+-]\d{2}:\d{2})?$"
)
ManifestStepKind = Literal["config", "manifest"]


@dataclass(frozen=True)
class ImagePlatform:
    """OS and CPU of the image whose config we want to read."""

    os: str | None = None
    architecture: str | None = None
    variant: str | None = None


@dataclass(frozen=True)
class RemoteImageMetadata:
    """
    Version and build time of a remote image.

    Version comes from image labels and may be missing.
    Created is the image config's created field.
    """

    version: str | None = None
    created: datetime | None = None


def platform_from_image(image: ImageInspectResult | None) -> ImagePlatform:
    """Platform of an already inspected image, used to pick a manifest."""
    if image is None:
        return ImagePlatform()
    return ImagePlatform(
        os=image.os,
        architecture=image.architecture,
        variant=image.variant,
    )


def metadata_from_image_inspect(
    image: ImageInspectResult,
) -> RemoteImageMetadata:
    """
    Read version and created from an image that is already local.
    Used when the pending image was pulled before the check.
    """
    labels = image.config.labels if image.config else None
    return RemoteImageMetadata(
        version=get_version_from_labels(labels),
        created=naive_utc(image.created),
    )


def naive_utc(value: datetime | None) -> datetime | None:
    """UTC datetime without tzinfo, matching the rest of the database."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def parse_oci_created(value: object) -> datetime | None:
    """
    Parse the image config `created` string.

    Registries emit fractional seconds with more than six digits
    and a trailing Z. Stored value is naive UTC.
    """
    if isinstance(value, datetime):
        return naive_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    match = _OCI_CREATED_RE.match(value.strip())
    if not match:
        return None
    frac = match.group("frac")
    tz = match.group("tz") or ""
    if tz == "Z":
        tz = "+00:00"
    text = match.group("head")
    if frac:
        text += "." + frac[:6]
    text += tz
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return naive_utc(parsed)


def metadata_from_config_blob(blob: object) -> RemoteImageMetadata:
    """Read version labels and created from an OCI image config blob."""
    if not isinstance(blob, dict):
        return RemoteImageMetadata()
    config = blob.get("config")
    labels: dict[str, str] | None = None
    if isinstance(config, dict):
        raw_labels = config.get("Labels")
        if raw_labels is None:
            raw_labels = config.get("labels")
        if isinstance(raw_labels, dict):
            labels = {
                str(key): value
                for key, value in raw_labels.items()
                if isinstance(value, str)
            }
    return RemoteImageMetadata(
        version=get_version_from_labels(labels),
        created=parse_oci_created(blob.get("created")),
    )


def _is_manifest_index(document: dict[str, Any]) -> bool:
    media_type = document.get("mediaType")
    if isinstance(media_type, str) and media_type in _INDEX_MEDIA_TYPES:
        return True
    return "manifests" in document and "config" not in document


def _usable_index_entries(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw = document.get("manifests")
    if not isinstance(raw, list):
        return []
    entries: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("digest"), str):
            continue
        platform = item.get("platform")
        if isinstance(platform, dict) and (
            platform.get("os") == "unknown" or platform.get("architecture") == "unknown"
        ):
            continue
        entries.append(item)
    return entries


def _platform_matches(entry: dict[str, Any], platform: ImagePlatform) -> bool:
    raw = entry.get("platform")
    if not isinstance(raw, dict):
        return False
    if raw.get("os") != platform.os or raw.get("architecture") != platform.architecture:
        return False
    variant = raw.get("variant")
    if platform.variant and isinstance(variant, str) and variant != platform.variant:
        return False
    return True


def next_manifest_step(
    document: object,
    platform: ImagePlatform | None = None,
) -> tuple[ManifestStepKind, str] | None:
    """
    Decide the next registry read for a manifest document.

    An image manifest yields its config blob digest.
    An index yields the digest of the platform-specific manifest.
    A single usable entry is taken even when the local platform is unknown.
    Several entries and no matching platform yield None: guessing would
    report another architecture's version.
    """
    if not isinstance(document, dict):
        return None
    if not _is_manifest_index(document):
        config = document.get("config")
        if not isinstance(config, dict):
            return None
        digest = config.get("digest")
        if isinstance(digest, str) and digest:
            return ("config", digest)
        return None

    entries = _usable_index_entries(document)
    if not entries:
        return None
    if len(entries) == 1:
        return ("manifest", cast(str, entries[0]["digest"]))
    if platform and platform.os and platform.architecture:
        matches = [entry for entry in entries if _platform_matches(entry, platform)]
        if platform.variant:
            exact = [
                entry
                for entry in matches
                if isinstance(entry.get("platform"), dict)
                and entry["platform"].get("variant") == platform.variant
            ]
            if exact:
                matches = exact
        if matches:
            return ("manifest", cast(str, matches[0]["digest"]))
    return None


def _registry_headers(accept: str, previous: dict[str, str]) -> dict[str, str]:
    """Accept for this request, plus a bearer or basic token already obtained."""
    headers = {"Accept": accept}
    authorization = previous.get("Authorization")
    if authorization:
        headers["Authorization"] = authorization
    return headers


async def _registry_get_json(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    repo: str,
    basic_token: str | None,
    ssl: bool,
    insecure: bool,
) -> tuple[object, dict[str, str]]:
    """
    GET a registry URL, applying the same Bearer or Basic auth as digest HEAD.
    Returns the JSON body and the headers that succeeded, so later requests
    reuse the token.
    """
    logger: Final = logging.getLogger("get_remote_image_metadata")
    attempt = dict(headers)

    async def _read(resp: aiohttp.ClientResponse) -> object:
        resp.raise_for_status()
        return await resp.json(content_type=None)

    async with session.get(url, headers=attempt, ssl=ssl) as resp:
        logger.debug(resp)
        if resp.status not in (401, 403):
            return await _read(resp), attempt

        logger.info(f"Registry responded with {resp.status}, trying auth")
        auth_header = resp.headers.get("WWW-Authenticate", "")
        if "Bearer" in auth_header:
            bearer_token = await get_registry_bearer_token(
                session,
                auth_header,
                repo,
                basic_token,
                ssl,
                insecure,
            )
            attempt["Authorization"] = f"Bearer {bearer_token}"
        elif basic_token:
            attempt["Authorization"] = f"Basic {basic_token}"
        else:
            resp.raise_for_status()

    async with session.get(url, headers=attempt, ssl=ssl) as resp2:
        return await _read(resp2), attempt


async def get_remote_image_metadata(
    spec: str,
    platform: ImagePlatform | None = None,
) -> RemoteImageMetadata:
    """
    Read version and created for the image currently pointed at by a tag.

    Fetches the manifest, follows one index entry when the tag is multi-arch,
    then fetches that image's config blob. Raises if the registry cannot
    be read; callers must not cache a failed lookup.
    """
    logger: Final = logging.getLogger("get_remote_image_metadata")
    registry, repo, tag = parse_image_spec(spec)
    insecure_registries = SettingsStorage.get(ESettingKey.INSECURE_REGISTRIES)
    insecure = is_insecure_registry(registry, insecure_registries)
    schemes: list[str] = ["https"]
    if insecure:
        schemes.append("http")
    ssl = not insecure
    basic_token = DockerConfig().get_basic_token(registry)

    async with aiohttp.ClientSession(trust_env=True) as session:
        last_error: Exception | None = None
        document: object | None = None
        auth_headers: dict[str, str] = {}
        used_scheme = schemes[0]
        for scheme in schemes:
            url = f"{scheme}://{registry}/v2/{repo}/manifests/{tag}"
            logger.info(f"Reading manifest {url}")
            try:
                document, auth_headers = await _registry_get_json(
                    session,
                    url,
                    _registry_headers(_MANIFEST_ACCEPT, auth_headers),
                    repo,
                    basic_token,
                    ssl,
                    insecure,
                )
                used_scheme = scheme
                break
            except (
                aiohttp.ClientSSLError,
                aiohttp.ClientConnectorError,
            ) as e:
                logger.warning(f"Error on {scheme}: {e}")
                last_error = e
        if document is None:
            if last_error:
                raise last_error
            raise ValueError(f"Empty manifest response for {spec}")

        config_digest: str | None = None
        for _ in range(2):
            step = next_manifest_step(document, platform)
            if step is None:
                break
            kind, digest = step
            if kind == "config":
                config_digest = digest
                break
            child_url = f"{used_scheme}://{registry}/v2/{repo}/manifests/{digest}"
            logger.info(f"Reading platform manifest {child_url}")
            document, auth_headers = await _registry_get_json(
                session,
                child_url,
                _registry_headers(_MANIFEST_ACCEPT, auth_headers),
                repo,
                basic_token,
                ssl,
                insecure,
            )
        if not config_digest:
            raise ValueError(f"Could not resolve image config digest for {spec}")

        blob_url = f"{used_scheme}://{registry}/v2/{repo}/blobs/{config_digest}"
        logger.info(f"Reading image config {blob_url}")
        blob, _auth = await _registry_get_json(
            session,
            blob_url,
            _registry_headers(_CONFIG_ACCEPT, auth_headers),
            repo,
            basic_token,
            ssl,
            insecure,
        )
        return metadata_from_config_blob(blob)
