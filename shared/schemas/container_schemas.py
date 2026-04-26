from datetime import datetime, timedelta
from typing import (
    Literal,
)

from pydantic import BaseModel
from python_on_whales.utils import ValidPath, ValidPortMapping


class GetContainerListBodySchema(BaseModel):
    all: bool | None = True


class CreateContainerRequestBodySchema(BaseModel):
    """
    Create container request body.
    Should match kwargs for docker.container.create.
    """

    image: str
    command: list[str] | None = None
    add_hosts: tuple[str, str] | None = None
    blkio_weight: int | None = None
    blkio_weight_device: list[str] | None = None
    cap_add: list[str] | None = None
    cap_drop: list[str] | None = None
    cgroup_parent: str | None = None
    cgroupns: str | None = None
    cidfile: ValidPath | None = None
    cpu_period: int | None = None
    cpu_quota: int | None = None
    cpu_rt_period: int | None = None
    cpu_rt_runtime: int | None = None
    cpu_shares: int | None = None
    cpus: float | None = None
    cpuset_cpus: list[int] | None = None
    cpuset_mems: list[int] | None = None
    detach: bool | None = None
    devices: list[str] | None = None
    device_cgroup_rules: list[str] | None = None
    device_read_bps: list[str] | None = None
    device_read_iops: list[str] | None = None
    device_write_bps: list[str] | None = None
    device_write_iops: list[str] | None = None
    content_trust: bool | None = None
    dns: list[str] | None = None
    dns_options: list[str] | None = None
    dns_search: list[str] | None = None
    domainname: str | None = None
    entrypoint: str | None = None
    envs: dict[str, str] | None = None
    env_files: ValidPath | list[ValidPath] | None = None
    env_host: bool | None = None
    expose: int | list[int] | None = None
    gpus: int | str | None = None
    groups_add: list[str] | None = None
    healthcheck: bool | None = None
    health_cmd: str | None = None
    health_interval: int | None = None
    health_retries: int | None = None
    health_start_period: int | None = None
    health_timeout: int | None = None
    hostname: str | None = None
    init: bool | None = None
    interactive: bool | None = None
    ip: str | None = None
    ip6: str | None = None
    ipc: str | None = None
    isolation: str | None = None
    kernel_memory: int | str | None = None
    labels: dict[str, str] | None = None
    label_files: list[ValidPath] | None = None
    link: list[str] | None = None
    link_local_ip: list[str] | None = None
    log_driver: str | None = None
    log_options: list[str] | None = None
    mac_address: str | None = None
    memory: int | str | None = None
    memory_reservation: int | str | None = None
    memory_swap: int | str | None = None
    memory_swappiness: int | None = None
    mounts: list[list[str]] | None = None
    name: str | None = None
    networks: list[str] | None = None
    network_aliases: list[str] | None = None
    oom_kill: bool | None = None
    oom_score_adj: int | None = None
    pid: str | None = None
    pids_limit: int | None = None
    platform: str | None = None
    pod: str | None = None
    privileged: bool | None = None
    publish: list[ValidPortMapping] | None = None
    publish_all: bool | None = None
    pull: str | None = None
    read_only: bool | None = None
    restart: str | None = None
    remove: bool | None = None
    runtime: str | None = None
    security_options: list[str] | None = None
    shm_size: int | str | None = None
    sig_proxy: bool | None = None
    stop_signal: int | str | None = None
    stop_timeout: int | None = None
    storage_options: list[str] | None = None
    sysctl: dict[str, str] | None = None
    systemd: bool | Literal["always"] | None = None
    tmpfs: list[ValidPath] | None = None
    tty: bool | None = None
    tz: str | None = None
    ulimit: list[str] | None = None
    user: str | None = None
    userns: str | None = None
    uts: str | None = None
    volumes: list[tuple[ValidPath, ValidPath] | tuple[ValidPath, ValidPath, str]] | None = None
    volume_driver: str | None = None
    volumes_from: list[str] | None = None
    workdir: ValidPath | None = None


class GetContainerLogsRequestBody(BaseModel):
    since: datetime | timedelta | None = None
    until: datetime | timedelta | None = None
    tail: int | None = None
    details: bool = False
    timestamps: bool = False
