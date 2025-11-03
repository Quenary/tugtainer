from typing import (
    Literal,
    Optional,
    Union,
)
from pydantic import BaseModel
from python_on_whales.utils import ValidPath, ValidPortMapping


class GetContainerListBodySchema(BaseModel):
    all: Optional[bool] = True


class CreateContainerRequestBodySchema(BaseModel):
    """
    Create container request body.
    Should match kwargs for docker.container.create.
    """

    image: str
    command: Optional[list[str]] = None
    add_hosts: Optional[tuple[str, str]] = None
    blkio_weight: Optional[int] = None
    blkio_weight_device: Optional[list[str]] = None
    cap_add: Optional[list[str]] = None
    cap_drop: Optional[list[str]] = None
    cgroup_parent: Optional[str] = None
    cgroupns: Optional[str] = None
    cidfile: Optional[ValidPath] = None
    cpu_period: Optional[int] = None
    cpu_quota: Optional[int] = None
    cpu_rt_period: Optional[int] = None
    cpu_rt_runtime: Optional[int] = None
    cpu_shares: Optional[int] = None
    cpus: Optional[float] = None
    cpuset_cpus: Optional[list[int]] = None
    cpuset_mems: Optional[list[int]] = None
    detach: Optional[bool] = None
    devices: Optional[list[str]] = None
    device_cgroup_rules: Optional[list[str]] = None
    device_read_bps: Optional[list[str]] = None
    device_read_iops: Optional[list[str]] = None
    device_write_bps: Optional[list[str]] = None
    device_write_iops: Optional[list[str]] = None
    content_trust: Optional[bool] = None
    dns: Optional[list[str]] = None
    dns_options: Optional[list[str]] = None
    dns_search: Optional[list[str]] = None
    domainname: Optional[str] = None
    entrypoint: Optional[str] = None
    envs: Optional[dict[str, str]] = None
    env_files: Optional[Union[ValidPath, list[ValidPath]]] = None
    env_host: Optional[bool] = None
    expose: Optional[Union[int, list[int]]] = None
    gpus: Optional[Union[int, str]] = None
    groups_add: Optional[list[str]] = None
    healthcheck: Optional[bool] = None
    health_cmd: Optional[str] = None
    health_interval: Optional[int] = None
    health_retries: Optional[int] = None
    health_start_period: Optional[int] = None
    health_timeout: Optional[int] = None
    hostname: Optional[str] = None
    init: Optional[bool] = None
    interactive: Optional[bool] = None
    ip: Optional[str] = None
    ip6: Optional[str] = None
    ipc: Optional[str] = None
    isolation: Optional[str] = None
    kernel_memory: Optional[Union[int, str]] = None
    labels: Optional[dict[str, str]] = None
    label_files: Optional[list[ValidPath]] = None
    link: Optional[list[str]] = None
    link_local_ip: Optional[list[str]] = None
    log_driver: Optional[str] = None
    log_options: Optional[list[str]] = None
    mac_address: Optional[str] = None
    memory: Optional[Union[int, str]] = None
    memory_reservation: Optional[Union[int, str]] = None
    memory_swap: Optional[Union[int, str]] = None
    memory_swappiness: Optional[int] = None
    mounts: Optional[list[list[str]]] = None
    name: Optional[str] = None
    networks: Optional[list[str]] = None
    network_aliases: Optional[list[str]] = None
    oom_kill: Optional[bool] = None
    oom_score_adj: Optional[int] = None
    pid: Optional[str] = None
    pids_limit: Optional[int] = None
    platform: Optional[str] = None
    pod: Optional[str] = None
    privileged: Optional[bool] = None
    publish: Optional[list[ValidPortMapping]] = None
    publish_all: Optional[bool] = None
    pull: Optional[str] = None
    read_only: Optional[bool] = None
    restart: Optional[str] = None
    remove: Optional[bool] = None
    runtime: Optional[str] = None
    security_options: Optional[list[str]] = None
    shm_size: Optional[Union[int, str]] = None
    sig_proxy: Optional[bool] = None
    stop_signal: Optional[Union[int, str]] = None
    stop_timeout: Optional[int] = None
    storage_options: Optional[list[str]] = None
    sysctl: Optional[dict[str, str]] = None
    systemd: Optional[Union[bool, Literal["always"]]] = None
    tmpfs: Optional[list[ValidPath]] = None
    tty: Optional[bool] = None
    tz: Optional[str] = None
    ulimit: Optional[list[str]] = None
    user: Optional[str] = None
    userns: Optional[str] = None
    uts: Optional[str] = None
    volumes: Optional[
        list[
            Union[
                tuple[ValidPath, ValidPath],
                tuple[ValidPath, ValidPath, str],
            ]
        ]
    ] = None
    volume_driver: Optional[str] = None
    volumes_from: Optional[list[str]] = None
    workdir: Optional[ValidPath] = None
