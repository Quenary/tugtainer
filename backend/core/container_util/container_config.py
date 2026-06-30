from typing import Final

from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.util.drop_empty_keys import drop_empty_keys
from backend.util.subtract_dict import subtract_dict
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from shared.schemas.docker_version_scheme import DockerVersionScheme

from .get_container_entrypoint_str import get_container_entrypoint_str
from .get_container_net_kwargs import get_container_net_kwargs
from .get_container_restart_policy_str import (
    get_container_restart_policy_str,
)
from .map_device_requests_to_gpus import map_device_requests_to_gpus
from .map_devices_to_list import map_devices_to_list
from .map_env_to_dict import map_env_to_dict
from .map_healthcheck_to_kwargs import map_healthcheck_to_kwargs
from .map_log_config_to_kwargs import map_log_config_to_kwargs
from .map_mounts_to_arg import map_mounts_to_arg
from .map_tmpfs_dict_to_list import map_tmpfs_dict_to_list
from .map_ulimits_to_arg import map_ulimits_to_arg
from .normalize_path import normalize_path


def diff_container_config_with_images(
    cfg: CreateContainerRequestBodySchema,
    remote_image: ImageInspectResult,
    local_image: ImageInspectResult,
) -> CreateContainerRequestBodySchema:
    """
    Prepare container config considering remote and local images
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

        if local_image.config:
            # Drop values if not explicitly overridden
            if (
                local_image.config.entrypoint == cfg_dict.get("entrypoint")
                and remote_image.config.entrypoint
            ):
                cfg_dict.pop("entrypoint", None)

            if (
                local_image.config.cmd == cfg_dict.get("command")
                and remote_image.config.cmd
            ):
                cfg_dict.pop("command", None)

            if (
                local_image.config.working_dir == cfg_dict.get("workdir")
                and remote_image.config.working_dir
            ):
                cfg_dict.pop("workdir", None)

        cfg_dict = drop_empty_keys(cfg_dict)

        return CreateContainerRequestBodySchema.model_validate(cfg_dict)

    return cfg


def get_container_config(
    container: ContainerInspectResult,
    docker_version: DockerVersionScheme | None,
) -> tuple[CreateContainerRequestBodySchema, list[list[str]]]:
    """
    Get container config and commands (e.g. network connect)
    :returns 0: config dict
    :returns 1: list of docker commands to be executed after container creation, in list format e.g. ["network", "connect", ...]
    """
    commands: list[list[str]] = []
    config: Final = container.config or ContainerConfig()
    host_config: Final = container.host_config or ContainerHostConfig()

    ENVS = map_env_to_dict(config.env)

    NET_KWARGS, NET_COMMANDS = get_container_net_kwargs(container, docker_version)
    if NET_COMMANDS:
        commands += NET_COMMANDS

    config_dict = {
        "image": config.image,
        "name": container.name,
        "blkio_weight": host_config.blkio_weight,
        "blkio_weight_device": host_config.blkio_weight_device,
        "command": config.cmd,
        "cap_add": host_config.cap_add,
        "cap_drop": host_config.cap_drop,
        "cgroup_parent": normalize_path(host_config.cgroup_parent),
        "cgroupns": host_config.cgroupns_mode,
        "cpu_period": host_config.cpu_period,
        "cpu_quota": host_config.cpu_quota,
        "cpu_rt_period": host_config.cpu_realtime_period,
        "cpu_rt_runtime": host_config.cpu_realtime_runtime,
        "cpu_shares": host_config.cpu_shares,
        "cpus": host_config.cpu_count,
        "cpuset_cpus": host_config.cpuset_cpus,
        "cpuset_mems": host_config.cpuset_mems,
        "devices": map_devices_to_list(host_config.devices),
        "device_cgroup_rules": host_config.device_cgroup_rules,
        "device_read_bps": host_config.blkio_device_read_bps,
        "device_read_iops": host_config.blkio_device_read_iops,
        "device_write_bps": host_config.blkio_device_write_bps,
        "device_write_iops": host_config.blkio_device_write_iops,
        **NET_KWARGS,
        "domainname": config.domainname,
        "entrypoint": get_container_entrypoint_str(config.entrypoint),
        "envs": ENVS,
        "gpus": map_device_requests_to_gpus(host_config.device_requests),
        "groups_add": host_config.group_add,
        **map_healthcheck_to_kwargs(config.healthcheck),
        "ipc": host_config.ipc_mode,
        "isolation": host_config.isolation,
        "kernel_memory": host_config.kernel_memory,
        "labels": config.labels,
        **map_log_config_to_kwargs(host_config.log_config),
        "memory": host_config.memory,
        "memory_reservation": host_config.memory_reservation,
        "memory_swap": host_config.memory_swap,
        "memory_swappiness": host_config.memory_swappiness,
        "mounts": map_mounts_to_arg(container.mounts),
        "oom_kill": bool(not host_config.oom_kill_disable),
        "oom_score_adj": host_config.oom_score_adj,
        "pids_limit": host_config.pids_limit,
        "privileged": host_config.privileged,
        "read_only": host_config.readonly_rootfs,
        "restart": get_container_restart_policy_str(host_config.restart_policy),
        "runtime": host_config.runtime,
        "security_options": host_config.security_opt,
        "shm_size": host_config.shm_size,
        "stop_signal": config.stop_signal,
        "stop_timeout": config.stop_timeout,
        "storage_options": host_config.storage_opt,
        "sysctl": host_config.sysctls,
        "systemd": config.systemd_mode,
        "tmpfs": map_tmpfs_dict_to_list(host_config.tmpfs),
        "ulimit": map_ulimits_to_arg(host_config.ulimits),
        "user": config.user,
        "userns": host_config.userns_mode,
        "uts": host_config.uts_mode,
        "volume_driver": host_config.volume_driver,
        "volumes_from": host_config.volumes_from,
        "workdir": normalize_path(config.working_dir),
    }
    config_dict = drop_empty_keys(config_dict)

    return (
        CreateContainerRequestBodySchema.model_validate(config_dict),
        commands,
    )
