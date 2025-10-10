from typing import Any
from python_on_whales import Container, Image
from app.helpers import (
    env_to_dict,
)
from app.helpers import subtract_dict
from . import (
    map_ulimits_to_arg,
    map_healthcheck_to_kwargs,
    map_log_config_to_kwargs,
    map_mounts_to_arg,
    map_port_bindings_to_list,
    map_devices_to_list,
    get_container_restart_policy_str,
    normalize_path,
    map_tmpfs_dict_to_list,
    filter_valid_docker_labels,
)
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
    cfg: dict, image: Image
) -> dict:
    """
    Merge container config with some values from image config.
    Returns config dict that matches kwargs for create/run.
    """
    cfg_envs: dict = cfg.get("envs", {})
    image_envs: dict = env_to_dict(image.config.env)
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

    return merged_config


def get_container_config(
    container: Container,
) -> tuple[dict[Any, Any], list[list[str]]]:
    """
    Get container config dict that matches kwargs for create/run.
    :returns 0: config dict
    :returns 1: list of docker commands to be executed after container creation, in list format e.g. ["network", "connect", ...]
    """
    COMMANDS: list[list[str]] = []
    ID = container.id
    CONFIG = container.config
    HOST_CONFIG = container.host_config
    NETWORK_SETTINGS = container.network_settings

    # Do not preserve generated hostname
    HOSTNAME = CONFIG.hostname
    if HOSTNAME and HOSTNAME in ID:
        HOSTNAME = None
    HOST_CONFIG.mounts

    ENVS = env_to_dict(CONFIG.env)

    PUBLISH = map_port_bindings_to_list(HOST_CONFIG.port_bindings)
    # Possible values: bridge | none | container:<name|id> (named network) | host
    NETWORK_MODE = HOST_CONFIG.network_mode
    # Remove any ports coz those are not supported in host network mode
    if NETWORK_MODE in ["host", "none"]:
        PUBLISH = None

    # Networks
    NETWORKS: list[str] = []
    NETWORK_ALIASES: list[str] = []
    if NETWORK_SETTINGS.networks:
        NETWORKS_KEYS = list(NETWORK_SETTINGS.networks.keys())
        MAIN_NETWORK = NETWORK_SETTINGS.networks[NETWORKS_KEYS[0]]
        NETWORKS = [NETWORKS_KEYS[0]]
        NETWORK_ALIASES = MAIN_NETWORK.aliases or []
        for net in NETWORKS_KEYS[1:]:
            # Additional networks returned as commands as python_on_whales doesnt support multiple aliases yet
            _cmd = ["network", "connect"]
            aliases = NETWORK_SETTINGS.networks[net].aliases or []
            for a in aliases:
                _cmd += ["--alias", a]
            _cmd += [net, container.name]
            COMMANDS.append(_cmd)
    elif NETWORK_MODE:
        NETWORKS = [NETWORK_MODE]

    VALID_LABELS, INVALID_LABELS = filter_valid_docker_labels(
        CONFIG.labels or {}
    )
    if INVALID_LABELS:
        logging.warning(
            f"Invalid labels were dropped while preparing config: {INVALID_LABELS}"
        )

    CONFIG = {
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
        "dns": HOST_CONFIG.dns,
        "dns_options": HOST_CONFIG.dns_options,
        "dns_search": HOST_CONFIG.dns_search,
        "domainname": CONFIG.domainname,
        "entrypoint": CONFIG.entrypoint,
        "envs": ENVS,
        "groups_add": HOST_CONFIG.group_add,
        **map_healthcheck_to_kwargs(CONFIG.healthcheck),
        "hostname": HOSTNAME,
        "ipc": HOST_CONFIG.ipc_mode,
        "isolation": HOST_CONFIG.isolation,
        "kernel_memory": HOST_CONFIG.kernel_memory,
        "labels": VALID_LABELS,
        "link": HOST_CONFIG.links,
        **map_log_config_to_kwargs(HOST_CONFIG.log_config),
        # Add setting to keep mac?
        # "mac_address": NETWORK_SETTINGS.mac_address,
        "memory": HOST_CONFIG.memory,
        "memory_reservation": HOST_CONFIG.memory_reservation,
        "memory_swap": HOST_CONFIG.memory_swap,
        "memory_swappiness": HOST_CONFIG.memory_swappiness,
        "mounts": map_mounts_to_arg(container.mounts),
        "networks": NETWORKS,
        "network_aliases": NETWORK_ALIASES,
        "oom_kill": bool(not HOST_CONFIG.oom_kill_disable),
        "oom_score_adj": HOST_CONFIG.oom_score_adj,
        "pids_limit": HOST_CONFIG.pids_limit,
        "privileged": HOST_CONFIG.privileged,
        "publish": PUBLISH,
        "publish_all": HOST_CONFIG.publish_all_ports,
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

    return CONFIG, COMMANDS
