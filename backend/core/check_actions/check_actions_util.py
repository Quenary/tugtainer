from datetime import datetime
from typing import Any, Final, cast
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.docker_config import DockerConfig
from backend.modules.containers.containers_model import (
    ContainersModel,
)
import aiohttp
from urllib.parse import urlencode
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
import logging


def filter_containers_by_check_enabled(
    containers: list[ContainerInspectResult],
    containers_db_map: dict[str, ContainersModel],
    manual: bool = False,
) -> list[ContainerInspectResult]:
    if manual:
        return containers
    _containers: list[ContainerInspectResult] = []
    for c in containers:
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
            (c_db := containers_db_map.get(cast(str, c.name)))
            is not None
            and c_db.checked_at is not None,
            (
                c_db.checked_at
                if c_db and c_db.checked_at
                else datetime.min
            ),
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
    logger:Final = logging.getLogger('get_image_remote_digest')
    registry, repo, tag = parse_image_spec(spec)

    insecure_registries = SettingsStorage.get(
        ESettingKey.INSECURE_REGISTRIES
    )
    logger.debug(f"Insecure Registries: {insecure_registries}")

    insecure: bool = bool(
        insecure_registries
        and any(
            x and registry and (registry in x or x in registry)
            for x in insecure_registries.splitlines()
        )
    )

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
        return resp.headers.get(
            "Docker-Content-Digest"
        ) or resp.headers.get("Etag")

    async def _do_request(
        session: aiohttp.ClientSession,
        url: str,
        headers: dict,
        ssl: bool = True,
    ):
        async with session.head(
            url, headers=headers, ssl=ssl
        ) as resp:
            logger.debug(resp)

            if resp.status in (401, 403):
                logger.info(
                    f"Registry responded with {resp.status}, trying auth"
                )

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
                    )
                    headers["Authorization"] = (
                        f"Bearer {bearer_token}"
                    )
                    auth_applied = True
                elif basic_token:
                    logger.info("Fallback to Basic auth")
                    headers["Authorization"] = f"Basic {basic_token}"
                    auth_applied = True

                if auth_applied:
                    async with session.head(
                        url, headers=headers, ssl=ssl
                    ) as resp2:
                        return _on_resp(resp2)

            return _on_resp(resp)

    async with aiohttp.ClientSession(trust_env=True) as session:
        last_error: Exception | None = None

        for scheme in schemes:
            url = f"{scheme}://{registry}/v2/{repo}/manifests/{tag}"

            logger.info(f"Trying {url}")

            try:
                attempt_headers = dict(headers)
                return await _do_request(
                    session, url, attempt_headers, ssl
                )
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

    if (
        ":" in spec
        and "/" in spec
        and spec.rfind(":") > spec.rfind("/")
    ):
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

    if registry == "registry-1.docker.io" and "/" not in repo:
        repo = f"library/{repo}"

    return registry, repo, tag


async def get_registry_bearer_token(
    session: aiohttp.ClientSession,
    auth_header: str,
    repo: str,
    basic_token: str | None = None,
    ssl: bool = True,
) -> str:
    """
    Get registry bearer token
    :param session: aiohttp session
    :param auth_header: WWW-Authenticate header value
        e.g. Bearer realm="https://auth.docker.io/token",service="registry.docker.io",scope="repository:library/nginx:pull"
    :param repo: repo name
    :param basic_token: basic token
    :param ssl: ssl flag for request
    :return: token
    """

    parts = auth_header.replace("Bearer ", "")
    items = dict(
        item.split("=", 1)
        for item in parts.replace('"', "").split(",")
    )

    realm = items["realm"]
    service = items.get("service")
    scope = items.get("scope") or f"repository:{repo}:pull"

    params = {"service": service, "scope": scope}

    url = f"{realm}?{urlencode(params)}"

    headers = {}

    if basic_token:
        headers["Authorization"] = f"Basic {basic_token}"

    async with session.get(url, headers=headers, ssl=ssl) as resp:
        resp.raise_for_status()
        data: dict[str, Any] = await resp.json()
        return data.get("token") or data.get("access_token") or ""
