from _asyncio import Future
from datetime import datetime
from docker.models.images import Image
from docker.models.containers import Container
from docker.models.containers import Container
import logging
from docker.models.containers import Container
from typing import Any, NotRequired, Optional, TypedDict, cast
from docker.models.containers import Container
from docker.models.images import Image
from docker.models.containers import Container
from docker import client
from sqlalchemy import select
import time
import asyncio
import concurrent.futures
from cachetools import TTLCache
from app.db.models.containers_model import ContainersModel
from app.db.session import _async_session_maker
from app.core.registries import choose_registry_client, BaseRegistryClient
from app.core.notifications_core import send_notification
from app.enums.check_status_enum import ECheckStatus
from app.helpers import is_self_container

_client = client.from_env()
ROLLBACK_TIMEOUT = 61

STATUS_CACHE = TTLCache(maxsize=10, ttl=600)
STATUS_CACHE_KEY = "check_and_update_containers"


class CheckStatusDict(TypedDict):
    status: NotRequired[ECheckStatus]  # status code
    progress: NotRequired[int]  # progress 0-100
    available: NotRequired[int]  # Count of not updated containers (check only)
    updated: NotRequired[int]  # count of updated containers
    failed: NotRequired[int]  # count of failed updates


def _set_check_status(key: str, value: CheckStatusDict):
    STATUS_CACHE[key] = value


def _update_check_status(key: str, value: CheckStatusDict):
    current = STATUS_CACHE.get(key) or {}
    STATUS_CACHE[key] = {
        **current,
        **value,
    }


def get_check_status(key: str) -> CheckStatusDict | None:
    return STATUS_CACHE.get(key)


def get_local_digest(image: Image) -> str | None:
    repo_digests = image.attrs.get("RepoDigests", [])
    if repo_digests:
        return repo_digests[0].split("@")[1]
    return None


async def filter_containers_for_check(containers: list[Container]) -> list[Container]:
    """Filter containers marked for check"""
    async with _async_session_maker() as session:
        stmt = select(ContainersModel.name).where(ContainersModel.check_enabled == True)
        result = await session.execute(stmt)
        names = result.scalars().all()
        return [c for c in containers if c.name in names]


async def filter_containers_for_update(containers: list[Container]) -> list[Container]:
    """Filter containers marked for update"""
    async with _async_session_maker() as session:
        stmt = select(ContainersModel.name).where(ContainersModel.update_enabled == True)
        result = await session.execute(stmt)
        names = result.scalars().all()
        return [c for c in containers if c.name in names]


def get_service_name(container: Container) -> str:
    """Extract service name from labels"""
    labels = container.labels or {}
    return labels.get("com.docker.compose.service", container.name)


def get_dependencies(container: Container) -> list[str]:
    """Get list of dependencies (container names)"""
    labels: dict[str, str] = container.labels or {}

    # E.g. "service1:condition:value,service2:condition:value"
    depends_on_label: str = labels.get("com.docker.compose.depends_on", "")

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.split(":")
        if parts:  # Берем только имя сервиса (первую часть)
            dependencies.append(parts[0])

    return dependencies


def _sort_containers_by_dependencies(containers: list[Container]) -> list[Container]:
    """
    Sort containers so that those on which others depend come first.
    Use the com.docker.compose.depends_on label, if present.
    """
    # Создаем словарь зависимостей: сервис -> список зависимостей
    container_map: dict[str, Container] = {}
    dependencies: dict[str, list[str]] = {}

    for container in containers:
        service_name = get_service_name(container)
        container_map[service_name] = container
        dependencies[service_name] = get_dependencies(container)

    visited: set[str] = set()
    result: list[Container] = []

    def visit(service) -> None:
        if service in visited:
            return
        visited.add(service)

        # Check all dependencies first
        for dep in dependencies[service]:
            if dep in container_map:
                visit(dep)

        # Then add current service
        if service in container_map:
            result.append(container_map[service])

    for service in container_map:
        visit(service)

    return result


def get_container_config(container: Container) -> dict[str, Any]:
    """
    Get container config ready to be used for recreation.
    """
    attrs: dict[str, Any] = container.attrs
    config: dict[str, Any] = attrs["Config"]
    host_config: dict[str, Any] = attrs["HostConfig"]
    networking_config: dict[str, Any] = attrs.get("NetworkSettings", {})

    # Ports
    ports = {}
    if networking_config.get("Ports"):
        for container_port, bindings in networking_config["Ports"].items():
            if bindings:
                host_ports = [int(b["HostPort"]) for b in bindings if b.get("HostPort")]
                if host_ports:
                    ports[container_port] = host_ports if len(host_ports) > 1 else host_ports[0]

    # Volumes
    volumes = {}
    for mount in attrs.get("Mounts", []):
        bind = {"bind": mount["Destination"], "mode": mount.get("Mode", "rw")}
        if mount["Type"] == "volume":
            volumes[mount["Name"]] = bind
        elif mount["Type"] == "bind":
            volumes[mount["Source"]] = bind

    # Env
    environment = {}
    for env in config.get("Env", []):
        if "=" in env:
            k, v = env.split("=", 1)
            environment[k] = v

    # Networks
    networks = list(networking_config.get("Networks", {}).keys())
    network_mode = host_config.get("NetworkMode")
    network_mode = network_mode if network_mode and network_mode != "default" else None

    return {
        "name": container.name,
        "detach": True,
        "environment": environment or None,
        "ports": ports or None,
        "volumes": volumes or None,
        "entrypoint": config.get("Entrypoint"),
        "command": config.get("Cmd"),
        "restart_policy": host_config.get("RestartPolicy"),
        "network": network_mode or (networks[0] if networks else None),
        "hostname": config.get("Hostname"),
        "domainname": config.get("Domainname"),
        "user": config.get("User"),
        "working_dir": config.get("WorkingDir"),
        "labels": config.get("Labels"),
        "privileged": host_config.get("Privileged", False),
        "cap_add": host_config.get("CapAdd"),
        "cap_drop": host_config.get("CapDrop"),
        "dns": host_config.get("Dns"),
        "extra_hosts": host_config.get("ExtraHosts"),
        "networks_to_connect": networks[1:],  # for post-connect
    }


def wait_for_container_healthy(container: Container, timeout: int = ROLLBACK_TIMEOUT) -> bool:
    """Wait for container healthy status or timeout"""
    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        health = container.attrs.get("State", {}).get("Health", {})
        status = health.get("Status")
        if not status:  # assume healthy if no healthcheck
            return True
        if status == "healthy":
            return True
        if status == "unhealthy":
            return False
        time.sleep(5)
    return False


def recreate_container(container: Container, new_image: str) -> Container:
    """
    Recreate container with new image
    """
    old_image = container.attrs["Config"]["Image"]
    cfg = get_container_config(container)
    networks_to_connect = cfg.pop("networks_to_connect", [])

    try:
        container.stop()
        container.remove()

        logging.info(f"Pulling new image {new_image}...")
        _client.images.pull(new_image)

        logging.info(f"Creating new container {cfg['name']}...")
        new_container: Container = _client.containers.run(new_image, **cfg)

        for net in networks_to_connect[1:]:
            _client.networks.get(net).connect(new_container)

        if wait_for_container_healthy(new_container):
            logging.info(f"Container {cfg['name']} is healthy. Update successful.")
            return new_container

        logging.error(f"Container {cfg['name']} failed healthcheck. Rolling back...")
        new_container.stop()
        new_container.remove()
        raise RuntimeError("Healthcheck failed")

    except Exception as e:
        logging.warning(f"Rollback: recreating {cfg['name']} with old image {old_image}: {e}")
        _client.images.pull(old_image)  # вдруг локально нет
        rolled_back = _client.containers.run(old_image, **cfg)
        for net in networks_to_connect[1:]:
            _client.networks.get(net).connect(rolled_back)
        logging.info(f"Rollback complete for {cfg['name']}.")
        return rolled_back


async def check_and_update_containers(cache_key: str = STATUS_CACHE_KEY):
    """
    Main func for check and update containers
    """
    status = get_check_status(cache_key)
    if status and status.get("status") != ECheckStatus.DONE:
        logging.warning("Check and update process is already running.")
        return

    progress: int = 0  # General progress state
    progress_part = 10
    _set_check_status(cache_key, {"status": ECheckStatus.COLLECTING, "progress": progress})
    logging.info("Start checking for updates")
    containers: list[Container] = _client.containers.list(all=True)
    containers = [item for item in containers if not is_self_container(item)]
    containers = await filter_containers_for_check(containers)

    progress += progress_part
    _update_check_status(
        cache_key,
        {"status": ECheckStatus.CHECKING, "progress": progress},
    )
    logging.info(f"Containers for check: {containers}")

    progress_part = 30
    progress_dividor = len(containers)
    updatable: list[Container] = []
    for c in containers:
        logging.info(f"Checking container: {c.name} {c.short_id}")
        image_spec = c.attrs["Config"]["Image"]
        registry: BaseRegistryClient = choose_registry_client(image_spec)
        local_image: Image = _client.images.get(image_spec)
        local_digest: str | None = get_local_digest(local_image)
        remote_digest: str | None = await registry.get_remote_digest()

        if remote_digest and local_digest != remote_digest:
            logging.info(f"New image found for container: {c.name} {c.short_id}")
            updatable.append(c)

        progress += round(progress_part / progress_dividor)
        _update_check_status(cache_key, {"progress": progress})

    to_update: list[Container] = await filter_containers_for_update(updatable)
    to_update = _sort_containers_by_dependencies(to_update)
    available: list[Container] = [c for c in updatable if c not in to_update]

    _update_check_status(cache_key, {"status": ECheckStatus.UPDATING, "available": len(available)})

    updated: list[Container] = []
    failed = 0
    loop = asyncio.get_running_loop()
    progress_part = 60
    progress_dividor = len(to_update)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        tasks: list[Future[Container]] = [
            loop.run_in_executor(executor, recreate_container, c, c.attrs["Config"]["Image"])
            for c in to_update
        ]

        for coro in asyncio.as_completed(tasks):
            try:
                res = await coro
                updated.append(res)
            except Exception as e:
                failed += 1
                logging.error(f"Failed to update: {e}")
            finally:
                progress += round(progress_part / progress_dividor)
                _update_check_status(
                    cache_key, {"progress": progress, "updated": len(updated), "failed": failed}
                )

    progress = 100
    _update_check_status(
        cache_key,
        {
            "status": ECheckStatus.DONE,
            "updated": len(updated),
            "failed": failed,
            "progress": progress,
        },
    )

    # Notification
    title: str = f"Dockobserver {datetime.now()}"
    body: str = ""
    if updated:
        body += "Updated:\n"
        for c in updated:
            body += f"{c.name} {c.attrs["Config"]["Image"]}\n"
        body += "\n"
    if available:
        body += "Update available for:\n"
        for c in available:
            body += f"{c.name} {c.attrs["Config"]["Image"]}\n"
        body += "\n"
    if body:
        try:
            await send_notification(title, body)
        except Exception as e:
            logging.error(f"Error while sending notification: {e}")
            pass
