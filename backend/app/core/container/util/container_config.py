from typing import Any

from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.app.helpers.subtract_dict import subtract_dict
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from .map_ulimits_to_arg import map_ulimits_to_arg
from .map_ulimits_to_arg import map_ulimits_to_arg
from .map_healthcheck_to_kwargs import map_healthcheck_to_kwargs
from .map_log_config_to_kwargs import map_log_config_to_kwargs
from .map_mounts_to_arg import map_mounts_to_arg
from .map_port_bindings_to_list import map_port_bindings_to_list
from .map_devices_to_list import map_devices_to_list
from .get_container_restart_policy_str import (
    get_container_restart_policy_str,
)
from .normalize_path import normalize_path
from .map_tmpfs_dict_to_list import map_tmpfs_dict_to_list
from .filter_valid_docker_labels import filter_valid_docker_labels
from .map_device_requests_to_gpus import map_device_requests_to_gpus
from .map_env_to_dict import map_env_to_dict
from .get_container_net_kwargs import get_container_net_kwargs
import logging


def _drop_empty_keys(cfg: dict) -> dict:
    """
    Drops 'empty' values from dict:
    - None
    - Empty containers (list, dict, tuple, set)
    - Empty strings or strings with only spaces
    """

    def is_empty(v):
        if v is None:
            return True
        if isinstance(v, (list, dict, tuple, set)) and len(v) == 0:
            return True
        if isinstance(v, str) and not v.strip():
            return True
        return False

    return {k: v for k, v in cfg.items() if not is_empty(v)}


def merge_container_config_with_image(
    _cfg: CreateContainerRequestBodySchema, image: ImageInspectResult
) -> CreateContainerRequestBodySchema:
    """
    Merge container config with some values from image config.
    Returns config dict that matches kwargs for create/run.
    """
    if not image.config:
        return _cfg
    cfg = _cfg.model_dump()
    cfg_envs: dict = cfg.get("envs", {})
    image_envs: dict = map_env_to_dict(image.config.env)
    merged_envs: dict = subtract_dict(cfg_envs, image_envs) or {}
    cfg_labels: dict = cfg.get("labels", {})
    image_labels: dict = image.config.labels or {}
    merged_labels: dict = (
        subtract_dict(
            cfg_labels,
            image_labels,
        )
        or {}
    )
    merged_labels, invalid_labels = filter_valid_docker_labels(
        merged_labels
    )
    if invalid_labels:
        logging.warning(
            f"Invalid labels were dropped while preparing config: {invalid_labels}"
        )
    if image.config.entrypoint:
        cfg.pop("entrypoint", None)
    if image.config.cmd:
        cfg.pop("command", None)
    if image.config.working_dir:
        cfg.pop("workdir", None)
    merged_config = {
        **cfg,
        "envs": merged_envs,
        "labels": merged_labels,
    }
    merged_config = _drop_empty_keys(merged_config)

    return CreateContainerRequestBodySchema(**merged_config)


def get_container_config(
    container: ContainerInspectResult,
) -> tuple[CreateContainerRequestBodySchema, list[list[str]]]:
    """
    Get container config dict that matches kwargs for create/run.
    :returns 0: config dict
    :returns 1: list of docker commands to be executed after container creation, in list format e.g. ["network", "connect", ...]
    """
    COMMANDS: list[list[str]] = []
    CONFIG = container.config or ContainerConfig()
    HOST_CONFIG = container.host_config or ContainerHostConfig()

    ENVS = map_env_to_dict(CONFIG.env)

    NET_KWARGS, NET_COMMANDS = get_container_net_kwargs(container)
    if NET_COMMANDS:
        COMMANDS += NET_COMMANDS

    VALID_LABELS, INVALID_LABELS = filter_valid_docker_labels(
        CONFIG.labels or {}
    )
    if INVALID_LABELS:
        logging.warning(
            f"Invalid labels were dropped while preparing config: {INVALID_LABELS}"
        )

    CONFIG = {
        "image": CONFIG.image,
        "name": container.name,
        "blkio_weight": HOST_CONFIG.blkio_weight,
        "blkio_weight_device": HOST_CONFIG.blkio_weight_device,
        "command": CONFIG.cmd,
        "cap_add": HOST_CONFIG.cap_add,
        "cap_drop": HOST_CONFIG.cap_drop,
        "cgroup_parent": normalize_path(HOST_CONFIG.cgroup_parent),
        "cgroupns": HOST_CONFIG.cgroupns_mode,
        "cpu_period": HOST_CONFIG.cpu_period,
        "cpu_quota": HOST_CONFIG.cpu_quota,
        "cpu_rt_period": HOST_CONFIG.cpu_realtime_period,
        "cpu_rt_runtime": HOST_CONFIG.cpu_realtime_runtime,
        "cpu_shares": HOST_CONFIG.cpu_shares,
        "cpus": HOST_CONFIG.cpu_count,
        "cpuset_cpus": HOST_CONFIG.cpuset_cpus,
        "cpuset_mems": HOST_CONFIG.cpuset_mems,
        "devices": map_devices_to_list(HOST_CONFIG.devices),
        "device_cgroup_rules": HOST_CONFIG.device_cgroup_rules,
        "device_read_bps": HOST_CONFIG.blkio_device_read_bps,
        "device_read_iops": HOST_CONFIG.blkio_device_read_iops,
        "device_write_bps": HOST_CONFIG.blkio_device_write_bps,
        "device_write_iops": HOST_CONFIG.blkio_device_write_iops,
        **NET_KWARGS,
        "domainname": CONFIG.domainname,
        "entrypoint": CONFIG.entrypoint,
        "envs": ENVS,
        "gpus": map_device_requests_to_gpus(
            HOST_CONFIG.device_requests
        ),
        "groups_add": HOST_CONFIG.group_add,
        **map_healthcheck_to_kwargs(CONFIG.healthcheck),
        "ipc": HOST_CONFIG.ipc_mode,
        "isolation": HOST_CONFIG.isolation,
        "kernel_memory": HOST_CONFIG.kernel_memory,
        "labels": VALID_LABELS,
        **map_log_config_to_kwargs(HOST_CONFIG.log_config),
        # Add setting to keep mac?
        # "mac_address": NETWORK_SETTINGS.mac_address,
        "memory": HOST_CONFIG.memory,
        "memory_reservation": HOST_CONFIG.memory_reservation,
        "memory_swap": HOST_CONFIG.memory_swap,
        "memory_swappiness": HOST_CONFIG.memory_swappiness,
        "mounts": map_mounts_to_arg(container.mounts),
        "oom_kill": bool(not HOST_CONFIG.oom_kill_disable),
        "oom_score_adj": HOST_CONFIG.oom_score_adj,
        "pids_limit": HOST_CONFIG.pids_limit,
        "privileged": HOST_CONFIG.privileged,
        "read_only": HOST_CONFIG.readonly_rootfs,
        "restart": get_container_restart_policy_str(
            HOST_CONFIG.restart_policy
        ),
        "runtime": HOST_CONFIG.runtime,
        "security_options": HOST_CONFIG.security_opt,
        "shm_size": HOST_CONFIG.shm_size,
        "stop_signal": CONFIG.stop_signal,
        "stop_timeout": CONFIG.stop_timeout,
        "storage_options": HOST_CONFIG.storage_opt,
        "sysctl": HOST_CONFIG.sysctls,
        "systemd": CONFIG.systemd_mode,
        "tmpfs": map_tmpfs_dict_to_list(HOST_CONFIG.tmpfs),
        "ulimit": map_ulimits_to_arg(HOST_CONFIG.ulimits),
        "user": CONFIG.user,
        "userns": HOST_CONFIG.userns_mode,
        "uts": HOST_CONFIG.uts_mode,
        "volume_driver": HOST_CONFIG.volume_driver,
        "volumes_from": HOST_CONFIG.volumes_from,
        "workdir": normalize_path(CONFIG.working_dir),
    }
    CONFIG = _drop_empty_keys(CONFIG)

    return CreateContainerRequestBodySchema(**CONFIG), COMMANDS
