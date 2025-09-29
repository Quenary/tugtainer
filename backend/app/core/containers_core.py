from datetime import datetime
from docker import client
from docker.models.containers import Container
from docker.models.images import Image
from docker.types import DriverConfig, Mount
import logging
from typing import Any, Literal, NotRequired, TypedDict
from sqlalchemy import and_, select
import time
import asyncio
import concurrent.futures
from cachetools import TTLCache
from app.db import (
    ContainersModel,
    async_session_maker,
    insert_or_update_container,
)
from app.core.registries import (
    choose_registry_client,
    BaseRegistryClient,
)
from app.core.notifications_core import send_notification
from app.enums.check_status_enum import ECheckStatus
from app.helpers import (
    is_self_container,
    now,
    env_to_dict,
    subtract_dict,
)
import traceback


_DOCKER = client.from_env()
_ROLLBACK_TIMEOUT = 60

_STATUS_CACHE = TTLCache(maxsize=10, ttl=600)
_ALL_CONTAINERS_STATUS_KEY = "check_and_update_all_containers"


class CheckStatusDict(TypedDict):
    status: NotRequired[ECheckStatus]  # status code
    available: NotRequired[
        int
    ]  # Count of not updated containers (check only)
    updated: NotRequired[int]  # count of updated containers
    rolledback: NotRequired[int]  # count of rolled-back after fail
    failed: NotRequired[int]  # count of failed updates


def _set_check_status(key: str, value: CheckStatusDict):
    """Set new check status"""
    _STATUS_CACHE[key] = value


def _update_check_status(key: str, value: CheckStatusDict):
    """Update existing check status"""
    current = _STATUS_CACHE.get(key) or {}
    _STATUS_CACHE[key] = {
        **current,
        **value,
    }


def get_check_status(key: str) -> CheckStatusDict | None:
    """Get check status"""
    return _STATUS_CACHE.get(key)


def _get_local_digest(image: Image) -> str | None:
    repo_digests = image.attrs.get("RepoDigests", [])
    if repo_digests:
        return repo_digests[0].split("@")[1]
    return None


async def db_update_container(name: str, data: dict):
    """
    Helper for updating container data in db
    """
    async with async_session_maker() as session:
        await insert_or_update_container(session, name, data)


async def filter_containers_for_check(
    containers: list[Container],
) -> list[Container]:
    """
    Filter containers marked for check only
    as well as self container
    """
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == False,
            )
        )
        result = await session.execute(stmt)
        names = result.scalars().all()
        res: list[Container] = []
        for c in containers:
            if c.name in names or is_self_container(c):
                res.append(c)
        return res


async def filter_containers_for_update(
    containers: list[Container],
) -> list[Container]:
    """Filter containers marked for check and auto update"""
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == True,
            )
        )
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
    depends_on_label: str = labels.get(
        "com.docker.compose.depends_on", ""
    )

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.split(":")
        if parts:  # Берем только имя сервиса (первую часть)
            dependencies.append(parts[0])

    return dependencies


def _sort_containers_by_dependencies(
    containers: list[Container],
) -> list[Container]:
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


def _get_container_image_spec(c: Container) -> str:
    return c.attrs.get("Config", {}).get("Image", "")


def merge_env(old_env: dict, new_env: dict) -> dict:
    """Сливает переменные окружения, приоритет за старыми (пользовательскими)."""
    result = dict(new_env)  # берем дефолты из образа
    result.update(old_env)  # перезаписываем пользовательскими
    return result


def _raw_mounts_to_cfg(
    mounts_config: list[dict[str, Any]],
) -> list[Mount]:
    """
    Map raw mounts from HostConfig to ones that can be used to create container
    """
    docker_mounts = []

    for mount in mounts_config:
        mount_type = mount.get("Type", "volume")
        source = mount.get("Source", "")
        target = mount.get("Destination", "")
        read_only = not mount.get("RW", True)

        mount_kwargs = {
            "target": target,
            "source": source,
            "type": mount_type,
            "read_only": read_only,
        }

        mode = mount.get("Mode", "")
        mode_parts = mode.split(",") if mode else []

        if mount_type == "bind":
            for consistency_mode in [
                "delegated",
                "cached",
                "consistent",
            ]:
                if consistency_mode in mode_parts:
                    mount_kwargs["consistency"] = consistency_mode
                    break
            propagation = mount.get("Propagation", "")
            if propagation:
                mount_kwargs["propagation"] = propagation

        if mount_type == "volume":
            name = mount.get("Name")
            if name:
                mount_kwargs["source"] = name
            driver = mount.get("Driver", "local")
            driver_options = mount.get("DriverOptions", {})

            volume_options = {}
            if driver != "local":
                volume_options["driver"] = driver
            if driver_options:
                volume_options["driver_config"] = driver_options

            if volume_options:
                mount_kwargs["volume_options"] = volume_options

        mount_obj = Mount(**mount_kwargs)
        docker_mounts.append(mount_obj)

    return docker_mounts


def _raw_ports_to_cfg(ports: dict) -> dict:
    """
    Map raw ports from network settings to ones that can be used to create container
    """
    _ports = {}
    if ports:
        for container_port, bindings in ports.items():
            if bindings:
                host_ports = [
                    int(b["HostPort"])
                    for b in bindings
                    if b.get("HostPort")
                ]
                if host_ports:
                    # There may be several different ports binded
                    # But also there may be two same ports (for imv4 and ipv6)
                    host_ports = list(set(host_ports))
                    _ports[container_port] = (
                        host_ports
                        if len(host_ports) > 1
                        else host_ports[0]
                    )
    return _ports


def get_container_config(
    container: Container,
) -> tuple[dict[str, Any], list[Any]]:
    """
    Get container config ready to be used for recreation.
    :returns 0: container config dict
    :returns 1: additional networks to connect after creation
    """
    ID = container.short_id
    ATTRS: dict[str, Any] = container.attrs
    CONFIG: dict[str, Any] = ATTRS["Config"]
    HOST_CONFIG: dict[str, Any] = ATTRS["HostConfig"]
    NETWORK_SETTINGS: dict[str, Any] = ATTRS.get(
        "NetworkSettings", {}
    )

    HOSTNAME: str | None = CONFIG.get("Hostname")
    if HOSTNAME == ID:
        HOSTNAME = None

    MOUNTS = _raw_mounts_to_cfg(ATTRS.get("Mounts", []))

    ENVIRONMENT = env_to_dict(CONFIG.get("Env", []))

    PORTS = _raw_ports_to_cfg(NETWORK_SETTINGS.get("Ports", {}))

    # Networks
    NETWORKS: list[str] = list(
        NETWORK_SETTINGS.get("Networks", {}).keys()
    )
    # Possible values: bridge | none | container:<name|id> (named network) | host
    NETWORK_MODE: str | None = HOST_CONFIG.get("NetworkMode")
    if NETWORK_MODE == "default":
        NETWORK_MODE = None
    NETWORK: str | None = None
    if not NETWORK_MODE and NETWORKS:
        NETWORK = NETWORKS[0]

    # Remove any ports coz those are not supported in host network mode
    if NETWORK_MODE == "host":
        PORTS = None

    # Extra networks to connect later
    NETWORKS_TO_CONNECT = NETWORKS[1:]

    CONFIG = {
        "name": container.name,
        "detach": True,
        "auto_remove": HOST_CONFIG.get("AutoRemove") or None,
        "blkio_weight_device": HOST_CONFIG.get("BlkioWeightDevice")
        or None,
        "blkio_weight": HOST_CONFIG.get("BlkioWeight") or None,
        "command": CONFIG.get("Cmd") or None,
        "cap_add": HOST_CONFIG.get("CapAdd") or None,
        "cap_drop": HOST_CONFIG.get("CapDrop") or None,
        "cgroup_parent": HOST_CONFIG.get("CgroupParent") or None,
        "cgroupns": HOST_CONFIG.get("CgroupnsMode") or None,
        "cpu_count": HOST_CONFIG.get("CpuCount") or None,
        "cpu_percent": HOST_CONFIG.get("CpuPercent") or None,
        "cpu_period": HOST_CONFIG.get("CpuPeriod") or None,
        "cpu_quota": HOST_CONFIG.get("CpuQuota") or None,
        "cpu_rt_period": HOST_CONFIG.get("CpuRealtimePeriod") or None,
        "cpu_rt_runtime": HOST_CONFIG.get("CpuRealtimeRuntime")
        or None,
        "cpu_shares": HOST_CONFIG.get("CpuShares") or None,
        "cpuset_cpus": HOST_CONFIG.get("CpusetCpus") or None,
        "cpuset_mems": HOST_CONFIG.get("CpusetMems") or None,
        "device_cgroup_rules": HOST_CONFIG.get("DeviceCgroupRules")
        or None,
        "device_read_bps": HOST_CONFIG.get("BlkioDeviceReadBps")
        or None,
        "device_read_iops": HOST_CONFIG.get("BlkioDeviceReadIOps")
        or None,
        "device_write_bps": HOST_CONFIG.get("BlkioDeviceWriteBps")
        or None,
        "device_write_iops": HOST_CONFIG.get("BlkioDeviceWriteIOps")
        or None,
        "devices": HOST_CONFIG.get("Devices") or None,
        "device_requests": HOST_CONFIG.get("DeviceRequests") or None,
        "dns": HOST_CONFIG.get("Dns") or None,
        "dns_opt": HOST_CONFIG.get("DnsOptions") or None,
        "dns_search": HOST_CONFIG.get("DnsSearch") or None,
        "domainname": CONFIG.get("Domainname") or None,
        "entrypoint": CONFIG.get("Entrypoint") or None,
        "environment": ENVIRONMENT or None,
        "extra_hosts": HOST_CONFIG.get("ExtraHosts") or None,
        "group_add": HOST_CONFIG.get("GroupAdd") or None,
        "healthcheck": CONFIG.get("Healthcheck") or None,
        # Check if it is short_id or something else (and keep)?
        "hostname": HOSTNAME or None,
        "ipc_mode": HOST_CONFIG.get("IpcMode") or None,
        "isolation": HOST_CONFIG.get("Isolation") or None,
        "labels": CONFIG.get("Labels") or None,
        "links": HOST_CONFIG.get("Links") or None,
        "log_config": HOST_CONFIG.get("LogConfig") or None,
        # Add setting to keep mac?
        # "mac_address": network_settings.get("MacAddress") or None,
        "mem_limit": HOST_CONFIG.get("Memory") or None,
        "mem_reservation": HOST_CONFIG.get("MemoryReservation")
        or None,
        "mem_swappiness": HOST_CONFIG.get("MemorySwappiness") or None,
        "memswap_limit": HOST_CONFIG.get("MemorySwap") or None,
        "mounts": MOUNTS or None,
        "nano_cpus": HOST_CONFIG.get("NanoCpus") or None,
        "network": NETWORK,
        "network_mode": NETWORK_MODE,
        "oom_kill_disable": HOST_CONFIG.get("OomKillDisable") or None,
        "oom_score_adj": HOST_CONFIG.get("OomScoreAdj") or None,
        "pid_mode": HOST_CONFIG.get("PidMode") or None,
        "pids_limit": HOST_CONFIG.get("PidsLimit") or None,
        "ports": PORTS or None,
        "privileged": HOST_CONFIG.get("Privileged", False) or None,
        "publish_all_ports": HOST_CONFIG.get("PublishAllPorts")
        or None,
        "read_only": HOST_CONFIG.get("ReadonlyRootfs") or None,
        "restart_policy": HOST_CONFIG.get("RestartPolicy") or None,
        "runtime": HOST_CONFIG.get("Runtime") or None,
        "security_opt": HOST_CONFIG.get("SecurityOpt") or None,
        "shm_size": HOST_CONFIG.get("ShmSize") or None,
        "tmpfs": HOST_CONFIG.get("Tmpfs") or None,
        "ulimits": HOST_CONFIG.get("Ulimits") or None,
        "user": CONFIG.get("User") or None,
        "userns_mode": HOST_CONFIG.get("userns_mode") or None,
        "uts_mode": HOST_CONFIG.get("UTSMode") or None,
        "volume_driver": HOST_CONFIG.get("VolumeDriver") or None,
        "volumes_from": HOST_CONFIG.get("VolumesFrom") or None,
        "working_dir": CONFIG.get("WorkingDir") or None,
    }
    CONFIG = {k: v for k, v in CONFIG.items() if v is not None}

    return (
        CONFIG,
        NETWORKS_TO_CONNECT,
    )


def _get_container_status_str(c: Container) -> str:
    return c.attrs.get("State", {}).get("Status", "")


async def _wait_for_container_healthy(
    container: Container, timeout: int = _ROLLBACK_TIMEOUT
) -> bool:
    """Wait for container healthy status or timeout"""
    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        health = container.health
        if health == "healthy":
            return True
        await asyncio.sleep(5)
    container.reload()
    health = container.health
    status = container.attrs.get("State", {}).get("Status", "")
    # On last attempt assume unknown is also healthy
    if status == "running" and health in ["healthy", "unknown"]:
        return True
    return False


def _connect_to_networks(
    container: Container, networks_to_connect: list[Any]
) -> None:
    """Connects container to several networks"""
    for net in networks_to_connect:
        logging.info(
            f"Connecting container {container.name} to several networks..."
        )
        try:
            _DOCKER.networks.get(net).connect(container)
        except Exception as e:
            logging.warning(
                f"Failed to connect container {container.name} to network {net}"
            )


async def _recreate_container(
    existing_container: Container,
) -> tuple[Container, bool]:
    """
    Recreate container with new image.
    :param container: container object
    :param new_image: new image name
    :returns 0: Container object (new or rolled-back)
    :returns 1: Updated flag (that is, not rolled-back)
    Could raise an exception if recreate and rallback fails.
    """

    IMAGE_SPEC = _get_container_image_spec(existing_container)
    OLD_IMAGE = _DOCKER.images.get(IMAGE_SPEC)
    CFG, NETWORKS_TO_CONNECT = get_container_config(
        existing_container
    )
    SHOULD_START = (
        _get_container_status_str(existing_container) == "running"
    )
    CFG_ENV: dict = CFG.pop("environment", {})
    CFG_LABELS: dict = CFG.pop("labels", {})
    NAME = CFG["name"]

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=1
    ) as executor:
        try:
            logging.info(f"Stopping container {NAME}...")
            await loop.run_in_executor(
                executor, existing_container.stop
            )

            logging.info(f"Removing container {NAME}...")
            await loop.run_in_executor(
                executor, existing_container.remove
            )

            logging.info(f"Pulling new image {IMAGE_SPEC}...")
            image = await loop.run_in_executor(
                executor, lambda: _DOCKER.images.pull(IMAGE_SPEC)
            )

            logging.info(f"Merging container and new image values")
            image_cfg: dict = image.attrs.get("Config", {})
            image_env: dict = env_to_dict(image_cfg.get("Env", []))
            image_labels = image_cfg.get("Labels", {})
            environment = subtract_dict(CFG_ENV, image_env) or None
            labels = subtract_dict(CFG_LABELS, image_labels) or None

            logging.info(f"Creating new container {NAME}...")
            new_container = await loop.run_in_executor(
                executor,
                lambda: _DOCKER.containers.create(
                    IMAGE_SPEC,
                    environment=environment,
                    labels=labels,
                    **CFG,
                ),
            )
            _connect_to_networks(new_container, NETWORKS_TO_CONNECT)

            if not SHOULD_START:
                logging.info(
                    f"Container {NAME} was not running before update, so leave it as is..."
                )
                return (new_container, True)

            logging.info(f"Starting new container {NAME}...")
            await loop.run_in_executor(executor, new_container.start)

            logging.info(f"Waiting for healthchecks of {NAME}")
            if await _wait_for_container_healthy(new_container):
                logging.info(
                    f"Container {NAME} is healthy. Update successful."
                )
                return (new_container, True)

            logging.warning(
                f"Container {NAME} failed healthcheck. Rolling back..."
            )
            await loop.run_in_executor(executor, new_container.stop)
            await loop.run_in_executor(executor, new_container.remove)
            raise RuntimeError("Healthcheck failed")
        except Exception as e:
            logging.warning(e)
            logging.warning(
                f"Rolling back {NAME} with previous image"
            )
            try:
                # In case failed container was not removed
                failed_cont = _DOCKER.containers.get(NAME)
                if failed_cont:
                    await loop.run_in_executor(
                        executor, failed_cont.stop
                    )
                    await loop.run_in_executor(
                        executor, failed_cont.remove
                    )
            except:
                pass

            logging.warning(
                f"Tagging previous image with spec: {IMAGE_SPEC}"
            )
            await loop.run_in_executor(
                executor, lambda: OLD_IMAGE.tag(IMAGE_SPEC)
            )
            logging.warning(f"Creating container with previous image")
            rolled_back = await loop.run_in_executor(
                executor,
                lambda: _DOCKER.containers.create(
                    image=IMAGE_SPEC,
                    environment=CFG_ENV,
                    labels=CFG_LABELS,
                    **CFG,
                ),
            )
            _connect_to_networks(rolled_back, NETWORKS_TO_CONNECT)
            if SHOULD_START:
                logging.info(f"Starting rolled-back container")
                await loop.run_in_executor(
                    executor, rolled_back.start
                )
            logging.info(f"Rollback complete for {NAME}.")
            return (rolled_back, False)


async def _is_container_update_available(c: Container) -> bool:
    """
    Compare digests and define is there new image
    """
    image_spec = _get_container_image_spec(c)
    registry: BaseRegistryClient = choose_registry_client(image_spec)
    local_image: Image = _DOCKER.images.get(image_spec)
    local_digest: str | None = _get_local_digest(local_image)
    remote_digest: str | None = await registry.get_remote_digest()
    return bool(remote_digest and local_digest != remote_digest)


async def check_container(
    name: str, update: bool = False
) -> tuple[Container | None, bool, bool, Exception | None]:
    """
    Check and update one container.
    Should not raises errors, only logging.
    :param name: name or id
    :param update: wether to update container (only check if false)
    :returns 0: Container if there is new one (updated or rolled-back after fail)
    :returns 1: Available flag (new image, but not updated)
    :returns 2: Updated flag (that is, not rolled-back)
    :returns 3: Exception if there was any
    """
    status = get_check_status(name)
    allow_statuses = [ECheckStatus.DONE, ECheckStatus.ERROR]
    if status and status.get("status") not in allow_statuses:
        logging.warning(
            f"Check and update of container {name} is already running"
        )
        return (None, False, False, None)

    _set_check_status(name, {"status": ECheckStatus.PREPARING})

    container = _DOCKER.containers.get(name)
    if not container:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.warning(
            f"While checking for update, container '{name}' not found"
        )
        return (None, False, False, None)

    _update_check_status(name, {"status": ECheckStatus.CHECKING})
    logging.info(f"Start checking for updates of container '{name}'")
    update_available: bool = await _is_container_update_available(
        container
    )
    await db_update_container(
        str(name),
        {
            "update_available": update_available,
            "checked_at": now(),
        },
    )

    if not update_available:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.info(
            f"No new image was found for the container '{name}'"
        )
        return (None, False, False, None)

    is_self = is_self_container(container)
    if is_self:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.warning(
            f"Update is available, but self container cannot be updated with that func"
        )
        return (None, True, False, None)

    if not update:
        _update_check_status(name, {"status": ECheckStatus.DONE})
        logging.info(f"Check of container '{name}' complete")
        return (None, True, False, None)

    _update_check_status(name, {"status": ECheckStatus.UPDATING})
    logging.info(f"New image found for container '{name}'")

    try:
        container, updated = await _recreate_container(
            container,
        )
        if updated:
            await db_update_container(
                str(name),
                {
                    "update_available": False,
                    "updated_at": now(),
                },
            )
        _update_check_status(name, {"status": ECheckStatus.DONE})
        return (container, False, updated, None)
    except Exception as e:
        logging.error(f"Failed to update container {name}: {e}")
        _update_check_status(name, {"status": ECheckStatus.ERROR})
        return (None, True, False, e)


async def check_and_update_all_containers():
    """
    Check and update containers
    marked for it, as well as self container (check only).
    Should not raises errors, only logging.
    """
    status = get_check_status(_ALL_CONTAINERS_STATUS_KEY)
    allow_statuses = [ECheckStatus.DONE, ECheckStatus.ERROR]
    if status and status.get("status") not in allow_statuses:
        logging.warning(
            "Check and update process is already running."
        )
        return

    _set_check_status(
        _ALL_CONTAINERS_STATUS_KEY,
        {"status": ECheckStatus.PREPARING},
    )
    logging.info("Start checking for updates of all containers")
    containers: list[Container] = _DOCKER.containers.list(all=True)

    for_check = await filter_containers_for_check(containers)
    for_update = await filter_containers_for_update(containers)
    for_update = _sort_containers_by_dependencies(for_update)

    _update_check_status(
        _ALL_CONTAINERS_STATUS_KEY,
        {"status": ECheckStatus.CHECKING},
    )

    available: list[Container] = []
    updated: list[Container] = []
    rolledback: list[Container] = []
    failed: list[Container] = []
    errors: list[Exception] = []

    for item in for_check:
        _cont, _available, _updated, _exp = await check_container(
            str(item.name), False
        )
        if _available:
            available.append(item)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    _update_check_status(
        _ALL_CONTAINERS_STATUS_KEY,
        {
            "status": ECheckStatus.UPDATING,
            "available": len(available),
        },
    )

    for item in for_update:
        _cont, _available, _updated, _exp = await check_container(
            str(item.name), True
        )
        if _cont:
            if _updated:
                updated.append(_cont)
            else:
                rolledback.append(_cont)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    _update_check_status(
        _ALL_CONTAINERS_STATUS_KEY,
        {
            "status": ECheckStatus.DONE,
            "updated": len(updated),
            "failed": len(failed),
            "rolledback": len(rolledback),
        },
    )

    # Notification
    try:
        title: str = f"Tugtainer {datetime.now()}"
        body: str = ""
        if updated:
            body += "Updated:\n"
            for c in updated:
                body += f"{c.name} {_get_container_image_spec(c)}\n"
            body += "\n"
        if available:
            body += "Update available for:\n"
            for c in available:
                body += f"{c.name} {_get_container_image_spec(c)}\n"
            body += "\n"
        if rolledback:
            body += "Rolled-back after fail:\n"
            for c in rolledback:
                body += f"{c.name} {_get_container_image_spec(c)}\n"
        if failed:
            body += f"Failed and not rolled-back:\n"
            for c in failed:
                body += f"{c.name} {_get_container_image_spec(c)}\n\n"
        if errors:
            body += f"Several errors occured:\n"
            for e in errors:
                tb_lines = traceback.format_exception(
                    type(e), e, e.__traceback__
                )
                last_lines = tb_lines[-3:]
                body += "".join(last_lines) + "\n"
        if body:
            await send_notification(title, body)
    except Exception as e:
        logging.error(f"Error while sending notification: {e}")
