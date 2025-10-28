from datetime import timedelta
from typing import (
    Iterable,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
)
from pydantic import BaseModel
from python_on_whales.components.volume.cli_wrapper import (
    VolumeDefinition,
)
from python_on_whales.utils import ValidPath, ValidPortMapping


class GetContainerListBodySchema(BaseModel):
    all: Optional[bool] = True


class CreateContainerRequestBodySchema(BaseModel):
    """
    Create container request body.
    Should match kwargs for docker.container.create.
    """

    image: str
    command: Optional[Sequence[str]]
    add_hosts: Optional[tuple[str, str]]
    blkio_weight: Optional[int]
    blkio_weight_device: Optional[Iterable[str]]
    cap_add: Optional[Iterable[str]]
    cap_drop: Optional[Iterable[str]]
    cgroup_parent: Optional[str]
    cgroupns: Optional[str]
    cidfile: Optional[ValidPath]
    cpu_period: Optional[int]
    cpu_quota: Optional[int]
    cpu_rt_period: Optional[int]
    cpu_rt_runtime: Optional[int]
    cpu_shares: Optional[int]
    cpus: Optional[float]
    cpuset_cpus: Optional[list[int]]
    cpuset_mems: Optional[list[int]]
    detach: Optional[bool]
    devices: Optional[Iterable[str]]
    device_cgroup_rules: Optional[Iterable[str]]
    device_read_bps: Optional[Iterable[str]]
    device_read_iops: Optional[Iterable[str]]
    device_write_bps: Optional[Iterable[str]]
    device_write_iops: Optional[Iterable[str]]
    content_trust: Optional[bool]
    dns: Optional[Iterable[str]]
    dns_options: Optional[Iterable[str]]
    dns_search: Optional[Iterable[str]]
    domainname: Optional[str]
    entrypoint: Optional[str]
    envs: Optional[Mapping[str, str]]
    env_files: Optional[Union[ValidPath, Iterable[ValidPath]]]
    env_host: Optional[bool]
    expose: Optional[Union[int, Iterable[int]]]
    gpus: Optional[Union[int, str]]
    groups_add: Optional[Iterable[str]]
    healthcheck: Optional[bool]
    health_cmd: Optional[str]
    health_interval: Optional[Union[int, timedelta]]
    health_retries: Optional[int]
    health_start_period: Optional[Union[int, timedelta]]
    health_timeout: Optional[Union[int, timedelta]]
    hostname: Optional[str]
    init: Optional[bool]
    interactive: Optional[bool]
    ip: Optional[str]
    ip6: Optional[str]
    ipc: Optional[str]
    isolation: Optional[str]
    kernel_memory: Optional[Union[int, str]]
    labels: Optional[Mapping[str, str]]
    label_files: Optional[Iterable[ValidPath]]
    link: Optional[Iterable[str]]
    link_local_ip: Optional[Iterable[str]]
    log_driver: Optional[str]
    log_options: Optional[Iterable[str]]
    mac_address: Optional[str]
    memory: Optional[Union[int, str]]
    memory_reservation: Optional[Union[int, str]]
    memory_swap: Optional[Union[int, str]]
    memory_swappiness: Optional[int]
    mounts: Optional[Iterable[Iterable[str]]]
    name: Optional[str]
    networks: Optional[Iterable[str]]
    network_aliases: Optional[Iterable[str]]
    oom_kill: Optional[bool]
    oom_score_adj: Optional[int]
    pid: Optional[str]
    pids_limit: Optional[int]
    platform: Optional[str]
    pod: Optional[str]
    privileged: Optional[bool]
    publish: Optional[Iterable[ValidPortMapping]]
    publish_all: Optional[bool]
    pull: Optional[str]
    read_only: Optional[bool]
    restart: Optional[str]
    remove: Optional[bool]
    runtime: Optional[str]
    security_options: Optional[Iterable[str]]
    shm_size: Optional[Union[int, str]]
    sig_proxy: Optional[bool]
    stop_signal: Optional[Union[int, str]]
    stop_timeout: Optional[int]
    storage_options: Optional[Iterable[str]]
    sysctl: Optional[Mapping[str, str]]
    systemd: Optional[Union[bool, Literal["always"]]]
    tmpfs: Optional[Iterable[ValidPath]]
    tty: Optional[bool]
    tz: Optional[str]
    ulimit: Optional[Iterable[str]]
    user: Optional[str]
    userns: Optional[str]
    uts: Optional[str]
    volumes: Optional[
        Iterable[
            Union[
                tuple[ValidPath, ValidPath],
                tuple[ValidPath, ValidPath, str],
            ]
        ]
    ]
    volume_driver: Optional[str]
    volumes_from: Optional[Iterable[str]]
    workdir: Optional[ValidPath]
