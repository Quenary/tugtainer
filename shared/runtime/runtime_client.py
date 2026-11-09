import asyncio
import base64
import json
import logging
import os
import ssl as ssl_lib
from collections.abc import Awaitable, Callable
from typing import Any, Final, TypeVar

import aiohttp
from pydantic import BaseModel

from shared.schemas.container_schemas import CreateContainerRequestBodySchema

from .container_create_payload import build_create_request
from .runtime_errors import (
    IncompatibleRuntimeError,
    RuntimeClientError,
    RuntimeConflictError,
    RuntimeExecError,
    RuntimeNotFoundError,
)
from .runtime_models import (
    ContainerInspectResult,
    ImageInspectResult,
    RuntimeVersion,
)
from .runtime_stream import (
    parse_json_lines_stream,
    read_exec_stream,
    read_stream_as_text,
)

logger: Final = logging.getLogger("runtime.client")

CLIENT_MIN_DOCKER_API: Final = (1, 44)
CLIENT_MAX_DOCKER_API: Final = (1, 48)
LIST_INSPECT_CONCURRENCY: Final = 8

T = TypeVar("T")


def parse_version_tuple(v_str: str | None) -> tuple[int, int]:
    """Parse '1.45' or '1.45.1' into integer tuple (1, 45)."""
    if not v_str:
        return (0, 0)
    parts = v_str.split(".")
    try:
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return (0, 0)


def split_image_ref(spec: str) -> tuple[str, str | None, str | None]:
    """Split an image reference into repository, tag, and digest.

    A digest is the part after ``@``. A tag is the part after the last ``:``
    that appears after the last ``/``, so registry ports stay in the repository.
    """
    name, sep, digest_part = spec.partition("@")
    digest = digest_part if sep and digest_part else None
    last_slash = name.rfind("/")
    colon = name.rfind(":")
    tag: str | None = None
    if colon > last_slash:
        tag = name[colon + 1 :] or None
        name = name[:colon]
    return name, tag, digest


def _create_payload(
    payload: dict[str, Any] | BaseModel,
    name: str | None,
) -> tuple[dict[str, Any], str | None, str | None]:
    body: CreateContainerRequestBodySchema | None = None
    if isinstance(payload, CreateContainerRequestBodySchema):
        body = payload
    elif isinstance(payload, dict) and "image" in payload and "Image" not in payload:
        body = CreateContainerRequestBodySchema.model_validate(payload)
    if body is not None:
        data, schema_name = build_create_request(body)
        return data, name or schema_name, body.platform
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_unset=True, by_alias=True), name, None
    return dict(payload), name, None


def encode_registry_auth(auth_dict: dict[str, Any] | None) -> str | None:
    """Base64url-encode auth configuration JSON, keeping padding.

    The Engine API decodes ``X-Registry-Auth`` with Go's ``URLEncoding``,
    which requires ``=`` padding. A stripped header is ignored, and the
    daemon then pulls with no credentials.
    """
    if not auth_dict:
        return None
    raw = json.dumps(auth_dict).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


class RuntimeClient:
    """Direct asynchronous HTTP client for Docker and Podman runtimes."""

    def __init__(
        self,
        docker_host: str | None = None,
        timeout: float = 15.0,
        ssl_context: ssl_lib.SSLContext | bool = True,
    ):
        self._raw_host = docker_host or os.environ.get("DOCKER_HOST")
        self._timeout = timeout
        self._ssl_context = ssl_context
        self._session: aiohttp.ClientSession | None = None
        self._session_lock: Final = asyncio.Lock()
        self._base_url: str = "http://localhost"
        self._negotiated_api_prefix: str = ""
        self._runtime_type: str = "docker"
        self._libpod_api_version: str | None = None
        self._version_info: RuntimeVersion | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                host = self._raw_host
                connector: aiohttp.BaseConnector
                if not host or host.startswith("unix://"):
                    path = (
                        host.removeprefix("unix://") if host else "/var/run/docker.sock"
                    )
                    if not os.path.exists(path) and os.path.exists(
                        "/run/podman/podman.sock"
                    ):
                        path = "/run/podman/podman.sock"
                    connector = aiohttp.UnixConnector(path=path)
                    self._base_url = "http://localhost"
                elif (
                    host.startswith("tcp://")
                    or host.startswith("http://")
                    or host.startswith("https://")
                ):
                    clean_url = host.replace("tcp://", "http://", 1)
                    self._base_url = clean_url.rstrip("/")
                    connector = aiohttp.TCPConnector(ssl=self._ssl_context)
                elif "://" in host:
                    scheme = host.split("://", 1)[0]
                    raise RuntimeClientError(
                        f"Unsupported DOCKER_HOST scheme '{scheme}'. "
                        "Use unix://, tcp://, http://, or https://. "
                        "ssh:// is not supported, and DOCKER_TLS_VERIFY and "
                        "DOCKER_CERT_PATH are not read."
                    )
                else:
                    connector = aiohttp.UnixConnector(path=host)
                    self._base_url = "http://localhost"

                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                )
            return self._session

    async def close(self) -> None:
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    async def __aenter__(self) -> "RuntimeClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        use_api_prefix: bool = True,
    ) -> aiohttp.ClientResponse:
        session = await self._get_session()
        prefix = self._negotiated_api_prefix if use_api_prefix else ""
        url = f"{self._base_url}{prefix}/{path.lstrip('/')}"
        req_headers = headers or {}
        req_timeout = (
            aiohttp.ClientTimeout(total=timeout)
            if timeout is not None
            else aiohttp.ClientTimeout(total=self._timeout)
        )

        clean_params = None
        if params:
            clean_params = {
                k: str(v).lower() if isinstance(v, bool) else str(v)
                for k, v in params.items()
                if v is not None
            }

        try:
            resp = await session.request(
                method=method,
                url=url,
                params=clean_params,
                json=json_data,
                headers=req_headers,
                timeout=req_timeout,
            )
        except TimeoutError as e:
            raise RuntimeClientError(
                f"Connection timeout to runtime daemon at {url}"
            ) from e
        except aiohttp.ClientError as e:
            raise RuntimeClientError(f"Connection error to runtime daemon: {e}") from e

        if resp.status == 404:
            body = await resp.text()
            resp.close()
            raise RuntimeNotFoundError(
                f"Resource not found at {path}", status_code=404, detail=body
            )
        if resp.status == 409:
            body = await resp.text()
            resp.close()
            raise RuntimeConflictError(
                f"Conflict error at {path}", status_code=409, detail=body
            )
        if resp.status >= 400:
            try:
                body = await resp.json()
            except Exception:
                body = await resp.text()
            resp.close()
            raise RuntimeClientError(
                f"Runtime engine error {resp.status} on {method} {path}",
                status_code=resp.status,
                detail=body,
            )
        return resp

    # Discovery & Health

    async def ping(self) -> str:
        """Ping daemon via /_ping."""
        resp = await self._request("GET", "/_ping", use_api_prefix=False)
        try:
            return (await resp.text()).strip()
        finally:
            resp.close()

    async def get_version(self) -> RuntimeVersion:
        """Discover runtime engine, detect Podman vs Docker, and negotiate API version."""
        if self._version_info:
            return self._version_info

        resp = await self._request("GET", "/version", use_api_prefix=False)
        try:
            data = await resp.json()
            headers = resp.headers
        finally:
            resp.close()

        # Detection signals for Podman
        is_podman = False
        components = data.get("Components") or []
        for c in components:
            c_name = c.get("Name", "")
            if "Podman" in c_name:
                is_podman = True
                break

        platform = data.get("Platform") or {}
        if "podman" in platform.get("Name", "").lower():
            is_podman = True

        libpod_ver = headers.get("Libpod-API-Version")
        if libpod_ver:
            is_podman = True

        server_api = data.get("ApiVersion")
        min_api = data.get("MinAPIVersion")

        if is_podman:
            self._runtime_type = "podman"
            self._libpod_api_version = libpod_ver or data.get("Version")
            # Podman exposes Docker compat at /v{ApiVersion}/
            self._negotiated_api_prefix = f"/v{server_api}" if server_api else ""
        else:
            self._runtime_type = "docker"
            daemon_tuple = parse_version_tuple(server_api)
            daemon_min_tuple = parse_version_tuple(min_api)

            if daemon_tuple < CLIENT_MIN_DOCKER_API:
                raise IncompatibleRuntimeError(
                    f"Docker API {server_api} is below minimum supported {CLIENT_MIN_DOCKER_API[0]}.{CLIENT_MIN_DOCKER_API[1]} (Docker 25.0+)"
                )
            if daemon_min_tuple > CLIENT_MAX_DOCKER_API:
                raise IncompatibleRuntimeError(
                    f"Daemon minimum API {min_api} exceeds client maximum {CLIENT_MAX_DOCKER_API[0]}.{CLIENT_MAX_DOCKER_API[1]}"
                )

            negotiated = min(daemon_tuple, CLIENT_MAX_DOCKER_API)
            self._negotiated_api_prefix = f"/v{negotiated[0]}.{negotiated[1]}"

        self._version_info = RuntimeVersion.model_validate(
            {
                **data,
                "runtime_type": self._runtime_type,
                "negotiated_api": self._negotiated_api_prefix.removeprefix("/v"),
                "libpod_api_version": self._libpod_api_version,
            }
        )
        return self._version_info

    async def get_info(self) -> dict[str, Any]:
        """Fetch system info."""
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request("GET", "/info")
        try:
            return await resp.json()
        finally:
            resp.close()

    # Container Operations

    async def container_list(
        self,
        all: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> list[ContainerInspectResult]:
        if not self._negotiated_api_prefix:
            await self.get_version()
        params: dict[str, Any] = {"all": all}
        if filters:
            params["filters"] = json.dumps(filters)
        resp = await self._request("GET", "/containers/json", params=params)
        try:
            items = await resp.json()
        finally:
            resp.close()
        return await self._inspect_listed(items, self.container_inspect)

    async def container_inspect(self, name_or_id: str) -> ContainerInspectResult:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request("GET", f"/containers/{name_or_id}/json")
        try:
            data = await resp.json()
            return ContainerInspectResult.model_validate(data)
        finally:
            resp.close()

    async def container_exists(self, name_or_id: str) -> bool:
        try:
            await self.container_inspect(name_or_id)
            return True
        except RuntimeNotFoundError:
            return False

    async def container_create(
        self,
        payload: dict[str, Any] | BaseModel,
        name: str | None = None,
    ) -> ContainerInspectResult:
        if not self._negotiated_api_prefix:
            await self.get_version()
        data, name, platform = _create_payload(payload, name)
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        if platform:
            params["platform"] = platform
        resp = await self._request(
            "POST", "/containers/create", params=params, json_data=data, timeout=600.0
        )
        try:
            res = await resp.json()
            new_id = res["Id"]
        finally:
            resp.close()
        return await self.container_inspect(new_id)

    async def container_start(self, name_or_id: str) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/start", timeout=600.0
        )
        resp.close()

    async def container_stop(self, name_or_id: str, timeout: int | None = 10) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        params = {"t": timeout} if timeout is not None else None
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/stop", params=params, timeout=600.0
        )
        resp.close()

    async def container_restart(
        self, name_or_id: str, timeout: int | None = 10
    ) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        params = {"t": timeout} if timeout is not None else None
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/restart", params=params, timeout=600.0
        )
        resp.close()

    async def container_kill(self, name_or_id: str, signal: str = "SIGKILL") -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "POST",
            f"/containers/{name_or_id}/kill",
            params={"signal": signal},
            timeout=600.0,
        )
        resp.close()

    async def container_pause(self, name_or_id: str) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/pause", timeout=600.0
        )
        resp.close()

    async def container_unpause(self, name_or_id: str) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/unpause", timeout=600.0
        )
        resp.close()

    async def container_rename(self, name_or_id: str, new_name: str) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "POST", f"/containers/{name_or_id}/rename", params={"name": new_name}
        )
        resp.close()

    async def container_remove(
        self, name_or_id: str, force: bool = True, volumes: bool = False
    ) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request(
            "DELETE",
            f"/containers/{name_or_id}",
            params={"force": force, "v": volumes},
            timeout=600.0,
        )
        resp.close()

    async def container_logs(
        self,
        name_or_id: str,
        stdout: bool = True,
        stderr: bool = True,
        tail: int | None = None,
        timestamps: bool = False,
        since: Any = None,
        until: Any = None,
        details: bool = False,
    ) -> str:
        if not self._negotiated_api_prefix:
            await self.get_version()
        inspect_data = await self.container_inspect(name_or_id)
        is_tty = bool(inspect_data.config and inspect_data.config.tty)

        params: dict[str, Any] = {
            "stdout": stdout,
            "stderr": stderr,
            "timestamps": timestamps,
            "details": details,
        }
        if tail is not None:
            params["tail"] = tail
        if since is not None:
            params["since"] = since
        if until is not None:
            params["until"] = until

        resp = await self._request(
            "GET", f"/containers/{name_or_id}/logs", params=params
        )
        try:
            return await read_stream_as_text(resp.content, is_tty=is_tty)
        finally:
            resp.close()

    async def container_exec(self, name_or_id: str, cmd: list[str]) -> str:
        """Execute command in container via Engine API exec, reading stream to completion."""
        if not self._negotiated_api_prefix:
            await self.get_version()

        # 1. Create exec instance
        create_resp = await self._request(
            "POST",
            f"/containers/{name_or_id}/exec",
            json_data={"AttachStdout": True, "AttachStderr": True, "Cmd": cmd},
        )
        try:
            exec_res = await create_resp.json()
            exec_id = exec_res["Id"]
        finally:
            create_resp.close()

        # 2. Start exec stream and read until EOF
        start_resp = await self._request(
            "POST",
            f"/exec/{exec_id}/start",
            json_data={"Detach": False, "Tty": False},
            timeout=600.0,
        )
        stdout, stderr = "", ""
        try:
            stdout, stderr = await read_exec_stream(start_resp.content, is_tty=False)
        finally:
            start_resp.close()

        # 3. Inspect final exit code
        inspect_resp = await self._request("GET", f"/exec/{exec_id}/json")
        try:
            info = await inspect_resp.json()
            exit_code = info.get("ExitCode")
        finally:
            inspect_resp.close()

        if exit_code is not None and exit_code != 0:
            raise RuntimeExecError(exit_code=exit_code, stdout=stdout, stderr=stderr)
        return stdout

    # Network Operations

    async def network_connect(
        self,
        network_id: str,
        container_id: str,
        endpoint_config: dict[str, Any] | None = None,
    ) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        payload: dict[str, Any] = {"Container": container_id}
        if endpoint_config:
            payload["EndpointConfig"] = endpoint_config
        resp = await self._request(
            "POST", f"/networks/{network_id}/connect", json_data=payload
        )
        resp.close()

    async def network_disconnect(
        self,
        network_id: str,
        container_id: str,
        force: bool = False,
    ) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        payload = {"Container": container_id, "Force": force}
        resp = await self._request(
            "POST", f"/networks/{network_id}/disconnect", json_data=payload
        )
        resp.close()

    # Image Operations

    async def image_inspect(self, name_or_id: str) -> ImageInspectResult:
        if not self._negotiated_api_prefix:
            await self.get_version()
        resp = await self._request("GET", f"/images/{name_or_id}/json")
        try:
            data = await resp.json()
            return ImageInspectResult.model_validate(data)
        finally:
            resp.close()

    async def image_exists(self, name_or_id: str) -> bool:
        try:
            await self.image_inspect(name_or_id)
            return True
        except RuntimeNotFoundError:
            return False

    async def image_list(
        self,
        all: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> list[ImageInspectResult]:
        if not self._negotiated_api_prefix:
            await self.get_version()
        params: dict[str, Any] = {"all": all}
        if filters:
            params["filters"] = json.dumps(filters)
        resp = await self._request("GET", "/images/json", params=params)
        try:
            items = await resp.json()
        finally:
            resp.close()
        return await self._inspect_listed(items, self.image_inspect)

    async def _inspect_listed(
        self,
        items: list[dict[str, Any]],
        inspect_one: Callable[[str], Awaitable[T]],
    ) -> list[T]:
        """Inspect each summary id. Skip objects removed between list and inspect."""
        ids = [
            item_id for item in items if (item_id := item.get("Id") or item.get("id"))
        ]
        semaphore = asyncio.Semaphore(LIST_INSPECT_CONCURRENCY)

        async def inspect_id(item_id: str) -> T | None:
            async with semaphore:
                try:
                    return await inspect_one(item_id)
                except RuntimeNotFoundError:
                    logger.debug("Skipping %s removed during list", item_id)
                    return None

        inspected = await asyncio.gather(*(inspect_id(item_id) for item_id in ids))
        return [item for item in inspected if item is not None]

    async def image_pull(
        self,
        spec: str,
        auth_config: dict[str, Any] | None = None,
        platform: str | None = None,
    ) -> ImageInspectResult:
        if not self._negotiated_api_prefix:
            await self.get_version()

        repo, tag, digest = split_image_ref(spec)
        if digest:
            params: dict[str, Any] = {"fromImage": f"{repo}@{digest}"}
        else:
            params = {"fromImage": repo, "tag": tag or "latest"}
        if platform:
            params["platform"] = platform

        headers: dict[str, str] = {}
        auth_header = encode_registry_auth(auth_config)
        if auth_header:
            headers["X-Registry-Auth"] = auth_header

        resp = await self._request(
            "POST", "/images/create", params=params, headers=headers, timeout=600.0
        )
        try:
            async for _ in parse_json_lines_stream(resp.content):
                pass
        finally:
            resp.close()

        return await self.image_inspect(spec)

    async def image_tag(
        self, spec_or_id: str, repo: str, tag: str | None = None
    ) -> None:
        if not self._negotiated_api_prefix:
            await self.get_version()
        if tag is None:
            repo_part, tag_part, _digest = split_image_ref(repo)
            tag_part = tag_part or "latest"
        else:
            repo_part, tag_part = repo, tag
        resp = await self._request(
            "POST",
            f"/images/{spec_or_id}/tag",
            params={"repo": repo_part, "tag": tag_part},
        )
        resp.close()

    async def image_prune(self, filters: dict[str, Any] | None = None) -> str:
        if not self._negotiated_api_prefix:
            await self.get_version()
        params = {"filters": json.dumps(filters)} if filters else None
        resp = await self._request(
            "POST", "/images/prune", params=params, timeout=600.0
        )
        try:
            data = await resp.text()
            return data
        finally:
            resp.close()

    # Swarm Operations

    async def service_list(self) -> list[dict[str, Any]]:
        if not self._negotiated_api_prefix:
            await self.get_version()
        if self._runtime_type == "podman":
            return []
        resp = await self._request("GET", "/services", params={"status": True})
        try:
            return await resp.json()
        finally:
            resp.close()

    async def service_inspect(self, name_or_id: str) -> dict[str, Any]:
        if not self._negotiated_api_prefix:
            await self.get_version()
        if self._runtime_type == "podman":
            raise RuntimeNotFoundError(
                f"Service {name_or_id} not found: Swarm unsupported on Podman"
            )
        resp = await self._request("GET", f"/services/{name_or_id}")
        try:
            return await resp.json()
        finally:
            resp.close()

    async def service_update(
        self,
        service_id: str,
        new_image: str,
        auth_config: dict[str, Any] | None = None,
    ) -> None:
        """Update Swarm service spec with optimistic concurrency via Version.Index."""
        if not self._negotiated_api_prefix:
            await self.get_version()
        if self._runtime_type == "podman":
            raise IncompatibleRuntimeError("Swarm service update unsupported on Podman")

        current = await self.service_inspect(service_id)
        version_index = current.get("Version", {}).get("Index")
        if version_index is None:
            raise RuntimeClientError(
                "Missing service Version.Index for optimistic concurrency"
            )

        spec = current.get("Spec")
        if not spec:
            raise RuntimeClientError("Missing service Spec in inspect result")

        task_template = spec.setdefault("TaskTemplate", {})
        container_spec = task_template.setdefault("ContainerSpec", {})
        container_spec["Image"] = new_image

        headers: dict[str, str] = {}
        auth_header = encode_registry_auth(auth_config)
        if auth_header:
            headers["X-Registry-Auth"] = auth_header

        resp = await self._request(
            "POST",
            f"/services/{service_id}/update",
            params={"version": version_index},
            json_data=spec,
            headers=headers,
            timeout=60.0,
        )
        resp.close()

    async def service_logs(
        self,
        name_or_id: str,
        tail: int = 100,
        timestamps: bool = False,
    ) -> str:
        if not self._negotiated_api_prefix:
            await self.get_version()
        if self._runtime_type == "podman":
            return ""
        params = {
            "stdout": 1,
            "stderr": 1,
            "tail": tail,
            "timestamps": timestamps,
        }
        resp = await self._request(
            "GET", f"/services/{name_or_id}/logs", params=params, timeout=60.0
        )
        try:
            return await read_stream_as_text(resp.content, is_tty=False)
        finally:
            resp.close()
