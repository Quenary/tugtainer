from typing import Any, Final

from backend.util.drop_empty_keys import drop_empty_keys
from backend.util.subtract_dict import subtract_dict, subtract_dict_items
from shared.runtime.capabilities import RuntimeCapabilities
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
    ImageInspectResult,
)
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.network_schemas import NetworkConnectBodySchema

from .get_container_net_kwargs import get_container_net_kwargs
from .get_container_restart_policy_str import (
    get_container_restart_policy_str,
)
from .map_device_requests_to_gpus import map_device_requests_to_gpus
from .map_devices_to_list import map_devices_to_list
from .map_env_to_dict import map_env_to_dict
from .map_healthcheck_to_kwargs import map_healthcheck_to_kwargs
from .map_log_config_to_kwargs import map_log_config_to_kwargs
from .map_mounts_to_arg import map_host_mounts
from .map_tmpfs_dict_to_list import map_tmpfs_dict_to_list
from .map_ulimits_to_arg import map_ulimits_to_arg
from .normalize_ns_mode import normalize_ns_mode
from .normalize_path import normalize_path
from .parse_extra_hosts import parse_extra_hosts
from .systemd_managed import systemd_managed_reason


def validate_recreation_preflight(
    container: ContainerInspectResult,
    docker_version: DockerVersionScheme | None,
) -> None:
    """Validate that all create-relevant settings can be preserved on the target daemon."""
    config = container.config or ContainerConfig()
    host_config = container.host_config or ContainerHostConfig()
    if host_config.container_id_file:
        raise RuntimePreflightError(
            f"Container {container.name} uses cidfile, which cannot be preserved "
            "through the engine API."
        )
    managed = systemd_managed_reason(config.labels, config.env)
    if managed:
        raise RuntimePreflightError(f"Container {container.name} {managed}")

    caps = RuntimeCapabilities.from_version(docker_version)
    # An unknown Docker daemon is checked again when the create body is built.
    if caps.runtime_type != "podman" and not caps.api_version:
        return

    inspect_mounts = list(container.mounts or [])
    if host_config.mounts:
        inspect_mounts.extend(host_config.mounts)
    for m in inspect_mounts:
        if m.type == "image":
            caps.require("Image mounts")

    if container.network_settings and container.network_settings.networks:
        for net_endpoint in container.network_settings.networks.values():
            if getattr(net_endpoint, "gateway_priority", None) is not None:
                caps.require("GwPriority")
                break


def diff_container_config_with_image(
    cfg: CreateContainerRequestBodySchema,
    remote_image: ImageInspectResult,
) -> CreateContainerRequestBodySchema:
    """
    Prepare container config considering remote image
    """
    if remote_image.config:
        cfg_dict = cfg.model_dump()

        cfg_dict["labels"] = (
            subtract_dict(
                cfg_dict.get("labels", {}),
                remote_image.config.labels or {},
            )
            or {}
        )

        cfg_dict = drop_empty_keys(cfg_dict)

        return CreateContainerRequestBodySchema.model_validate(cfg_dict)

    return cfg


def get_container_config(
    container: ContainerInspectResult,
    image: ImageInspectResult | None,
    docker_version: DockerVersionScheme | None,
) -> tuple[CreateContainerRequestBodySchema, list[NetworkConnectBodySchema]]:
    """
    Get container config and secondary network connects.
    :returns 0: config dict
    :returns 1: list of secondary NetworkConnectBodySchema items to connect
    """
    validate_recreation_preflight(container, docker_version)

    config: Final = container.config or ContainerConfig()
    host_config: Final = container.host_config or ContainerHostConfig()

    # Docker stores image ENV merged with user env in container config.
    # Drop values equal to the old image defaults, so the new image
    # provides its own defaults, while user overrides (different value) stay.
    ENVS = subtract_dict_items(
        map_env_to_dict(config.env),
        map_env_to_dict(image.config.env) if (image and image.config) else None,
    )

    NET_KWARGS, SECONDARY_CONNECTS = get_container_net_kwargs(container)

    # Preserve only values that differ from image defaults.
    command: list[str] | None = None
    entrypoint: str | None = None

    def _to_list(val: list[str] | str | None) -> list[str]:
        if not val:
            return []
        return [val] if isinstance(val, str) else list(val)

    current_entrypoint: Final = _to_list(config.entrypoint)
    current_cmd: Final = _to_list(config.cmd)

    image_entrypoint: Final = (
        _to_list(image.config.entrypoint) if (image and image.config) else []
    )
    image_cmd: Final = _to_list(image.config.cmd) if (image and image.config) else []

    if current_entrypoint != image_entrypoint or current_cmd != image_cmd:
        if current_entrypoint:
            entrypoint = current_entrypoint[0]
            command = current_entrypoint[1:] + current_cmd
        else:
            command = current_cmd

    workdir: str | None = None
    if image and image.config and image.config.working_dir != config.working_dir:
        workdir = normalize_path(config.working_dir)

    BINDS, MOUNTS = map_host_mounts(
        host_config.mounts, host_config.binds, container.mounts
    )

    # Drop labels inherited unchanged from the old image
    LABELS = subtract_dict_items(
        config.labels,
        image.config.labels if (image and image.config) else None,
    )

    config_dict = {
        "image": config.image,
        "name": container.name,
        "add_hosts": parse_extra_hosts(host_config.extra_hosts),
        "blkio_weight": host_config.blkio_weight,
        "blkio_weight_device": _device_limits(
            host_config.blkio_weight_device, "Weight"
        ),
        "command": command,
        "cap_add": host_config.cap_add,
        "cap_drop": host_config.cap_drop,
        "cgroup_parent": normalize_path(host_config.cgroup_parent),
        "cgroupns": host_config.cgroupns_mode,
        "cpu_period": host_config.cpu_period,
        "cpu_quota": host_config.cpu_quota,
        "cpu_rt_period": host_config.cpu_realtime_period,
        "cpu_rt_runtime": host_config.cpu_realtime_runtime,
        "cpu_shares": host_config.cpu_shares,
        "cpus": (
            host_config.nano_cpus / 1_000_000_000 if host_config.nano_cpus else None
        ),
        "cpuset_cpus": host_config.cpuset_cpus,
        "cpuset_mems": host_config.cpuset_mems,
        "devices": map_devices_to_list(host_config.devices),
        "device_cgroup_rules": host_config.device_cgroup_rules,
        "device_read_bps": _device_limits(host_config.blkio_device_read_bps, "Rate"),
        "device_read_iops": _device_limits(host_config.blkio_device_read_iops, "Rate"),
        "device_write_bps": _device_limits(host_config.blkio_device_write_bps, "Rate"),
        "device_write_iops": _device_limits(
            host_config.blkio_device_write_iops, "Rate"
        ),
        **NET_KWARGS,
        "domainname": config.domainname,
        "entrypoint": entrypoint,
        "envs": ENVS,
        "gpus": map_device_requests_to_gpus(host_config.device_requests),
        "groups_add": host_config.group_add,
        **map_healthcheck_to_kwargs(
            config.healthcheck,
            image.config.healthcheck if (image and image.config) else None,
            inherit_matching=bool(image and image.config),
        ),
        "init": host_config.init,
        "ipc": host_config.ipc_mode,
        "isolation": host_config.isolation,
        "kernel_memory": host_config.kernel_memory,
        "labels": LABELS,
        **map_log_config_to_kwargs(host_config.log_config),
        "memory": host_config.memory,
        "memory_reservation": host_config.memory_reservation,
        "memory_swap": host_config.memory_swap,
        "memory_swappiness": host_config.memory_swappiness,
        "binds": BINDS or None,
        "mounts": MOUNTS or None,
        "oom_kill": (
            None
            if host_config.oom_kill_disable is None
            else not host_config.oom_kill_disable
        ),
        "oom_score_adj": host_config.oom_score_adj,
        "pid": normalize_ns_mode(host_config.pid_mode),
        "pids_limit": host_config.pids_limit,
        "privileged": host_config.privileged,
        "read_only": host_config.readonly_rootfs,
        "restart": get_container_restart_policy_str(host_config.restart_policy),
        "runtime": host_config.runtime,
        "security_options": host_config.security_opt,
        "shm_size": host_config.shm_size,
        "stop_signal": config.stop_signal,
        "stop_timeout": config.stop_timeout,
        "storage_options": _storage_options(host_config.storage_opt),
        "sysctl": host_config.sysctls,
        "tty": config.tty,
        "expose": _exposed_tcp_ports(config.exposed_ports),
        "tmpfs": map_tmpfs_dict_to_list(host_config.tmpfs),
        "ulimit": map_ulimits_to_arg(host_config.ulimits),
        "user": config.user,
        "userns": normalize_ns_mode(host_config.userns_mode),
        "uts": normalize_ns_mode(host_config.uts_mode),
        "volume_driver": host_config.volume_driver,
        "volumes_from": host_config.volumes_from,
        "workdir": workdir,
    }
    config_dict = drop_empty_keys(config_dict)

    return (
        CreateContainerRequestBodySchema.model_validate(config_dict),
        SECONDARY_CONNECTS,
    )


def _device_limits(items: list[Any] | None, value_key: str) -> list[str] | None:
    if not items:
        return None
    specs: list[str] = []
    for item in items:
        if isinstance(item, str):
            specs.append(item)
            continue
        path = item.get("Path") or item.get("path") or ""
        value = item.get(value_key)
        if value is None:
            value = item.get(value_key.lower())
        specs.append(f"{path}:{value}")
    return specs


def _storage_options(options: dict[str, str] | None) -> list[str] | None:
    if not options:
        return None
    return [f"{key}={value}" for key, value in options.items()]


def _exposed_tcp_ports(ports: dict[str, Any] | None) -> list[int] | None:
    if not ports:
        return None
    numbers: list[int] = []
    for key in ports:
        port, _, proto = key.partition("/")
        if proto in ("", "tcp") and port.isdigit():
            numbers.append(int(port))
    return numbers or None
