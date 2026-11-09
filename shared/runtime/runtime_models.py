from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuntimeBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class PortBinding(RuntimeBaseModel):
    host_ip: str | None = Field(default=None, alias="HostIp")
    host_port: str | None = Field(default=None, alias="HostPort")


class Mount(RuntimeBaseModel):
    target: str | None = Field(default=None, alias="Target")
    destination: str | None = Field(default=None, alias="Destination")
    source: str | None = Field(default=None, alias="Source")
    type: str | None = Field(default="volume", alias="Type")
    read_only: bool | None = Field(default=None, alias="ReadOnly")
    rw: bool | None = Field(default=None, alias="RW")
    consistency: str | None = Field(default=None, alias="Consistency")
    bind_options: dict[str, Any] | None = Field(default=None, alias="BindOptions")
    volume_options: dict[str, Any] | None = Field(default=None, alias="VolumeOptions")
    tmpfs_options: dict[str, Any] | None = Field(default=None, alias="TmpfsOptions")
    name: str | None = Field(default=None, alias="Name")
    driver: str | None = Field(default=None, alias="Driver")
    mode: str | None = Field(default=None, alias="Mode")
    propagation: str | None = Field(default=None, alias="Propagation")

    @field_validator("destination", mode="before")
    @classmethod
    def populate_destination_from_target(cls, v: Any, info: Any) -> Any:
        return v


class ContainerHealthCheck(RuntimeBaseModel):
    test: list[str] | None = Field(default=None, alias="Test")
    interval: int | None = Field(default=None, alias="Interval")
    timeout: int | None = Field(default=None, alias="Timeout")
    retries: int | None = Field(default=None, alias="Retries")
    start_period: int | None = Field(default=None, alias="StartPeriod")
    start_interval: int | None = Field(default=None, alias="StartInterval")


class ContainerConfig(RuntimeBaseModel):
    hostname: str | None = Field(default=None, alias="Hostname")
    domainname: str | None = Field(default=None, alias="Domainname")
    user: str | None = Field(default=None, alias="User")
    attach_stdin: bool | None = Field(default=None, alias="AttachStdin")
    attach_stdout: bool | None = Field(default=None, alias="AttachStdout")
    attach_stderr: bool | None = Field(default=None, alias="AttachStderr")
    tty: bool | None = Field(default=None, alias="Tty")
    open_stdin: bool | None = Field(default=None, alias="OpenStdin")
    stdin_once: bool | None = Field(default=None, alias="StdinOnce")
    env: list[str] | None = Field(default=None, alias="Env")
    cmd: list[str] | None = Field(default=None, alias="Cmd")
    healthcheck: ContainerHealthCheck | None = Field(default=None, alias="Healthcheck")
    args_escaped: bool | None = Field(default=None, alias="ArgsEscaped")
    image: str | None = Field(default=None, alias="Image")
    volumes: dict[str, Any] | None = Field(default=None, alias="Volumes")
    working_dir: str | None = Field(default=None, alias="WorkingDir")
    entrypoint: list[str] | str | None = Field(default=None, alias="Entrypoint")
    network_disabled: bool | None = Field(default=None, alias="NetworkDisabled")
    mac_address: str | None = Field(default=None, alias="MacAddress")
    on_build: list[str] | None = Field(default=None, alias="OnBuild")
    labels: dict[str, str] | None = Field(default=None, alias="Labels")
    stop_signal: str | None = Field(default=None, alias="StopSignal")
    stop_timeout: int | None = Field(default=None, alias="StopTimeout")
    shell: list[str] | None = Field(default=None, alias="Shell")
    exposed_ports: dict[str, Any] | None = Field(default=None, alias="ExposedPorts")
    systemd_mode: str | bool | None = Field(default=None, alias="SystemdMode")


class ContainerDeviceRequest(RuntimeBaseModel):
    driver: str | None = Field(default=None, alias="Driver")
    count: int | None = Field(default=None, alias="Count")
    device_ids: list[str] | None = Field(default=None, alias="DeviceIDs")
    capabilities: list[list[str]] | list[str] | None = Field(
        default=None, alias="Capabilities"
    )
    options: dict[str, str] | None = Field(default=None, alias="Options")


class ContainerUlimit(RuntimeBaseModel):
    name: str | None = Field(default=None, alias="Name")
    soft: int | None = Field(default=None, alias="Soft")
    hard: int | None = Field(default=None, alias="Hard")


class ContainerLogConfig(RuntimeBaseModel):
    type: str | None = Field(default=None, alias="Type")
    config: dict[str, str] | None = Field(default=None, alias="Config")


class ContainerRestartPolicy(RuntimeBaseModel):
    name: str | None = Field(default=None, alias="Name")
    maximum_retry_count: int | None = Field(default=None, alias="MaximumRetryCount")


class ContainerHostConfig(RuntimeBaseModel):
    binds: list[str] | None = Field(default=None, alias="Binds")
    container_id_file: str | None = Field(default=None, alias="ContainerIDFile")
    log_config: ContainerLogConfig | None = Field(default=None, alias="LogConfig")
    network_mode: str | None = Field(default=None, alias="NetworkMode")
    port_bindings: dict[str, list[PortBinding] | None] | None = Field(
        default=None, alias="PortBindings"
    )
    restart_policy: ContainerRestartPolicy | None = Field(
        default=None, alias="RestartPolicy"
    )
    auto_remove: bool | None = Field(default=None, alias="AutoRemove")
    volume_driver: str | None = Field(default=None, alias="VolumeDriver")
    volumes_from: list[str] | None = Field(default=None, alias="VolumesFrom")
    cap_add: list[str] | None = Field(default=None, alias="CapAdd")
    cap_drop: list[str] | None = Field(default=None, alias="CapDrop")
    cgroupns_mode: str | None = Field(default=None, alias="CgroupnsMode")
    dns: list[str] | None = Field(default=None, alias="Dns")
    dns_options: list[str] | None = Field(default=None, alias="DnsOptions")
    dns_search: list[str] | None = Field(default=None, alias="DnsSearch")
    extra_hosts: list[str] | None = Field(default=None, alias="ExtraHosts")
    group_add: list[str] | None = Field(default=None, alias="GroupAdd")
    ipc_mode: str | None = Field(default=None, alias="IpcMode")
    cgroup: str | None = Field(default=None, alias="Cgroup")
    links: list[str] | None = Field(default=None, alias="Links")
    oom_score_adj: int | None = Field(default=None, alias="OomScoreAdj")
    pid_mode: str | None = Field(default=None, alias="PidMode")
    privileged: bool | None = Field(default=None, alias="Privileged")
    publish_all_ports: bool | None = Field(default=None, alias="PublishAllPorts")
    readonly_rootfs: bool | None = Field(default=None, alias="ReadonlyRootfs")
    security_opt: list[str] | None = Field(default=None, alias="SecurityOpt")
    storage_opt: dict[str, str] | None = Field(default=None, alias="StorageOpt")
    tmpfs: dict[str, str] | None = Field(default=None, alias="Tmpfs")
    uts_mode: str | None = Field(default=None, alias="UTSMode")
    userns_mode: str | None = Field(default=None, alias="UsernsMode")
    shm_size: int | None = Field(default=None, alias="ShmSize")
    sysctls: dict[str, str] | None = Field(default=None, alias="Sysctls")
    runtime: str | None = Field(default=None, alias="Runtime")
    isolation: str | None = Field(default=None, alias="Isolation")
    cpu_shares: int | None = Field(default=None, alias="CpuShares")
    memory: int | None = Field(default=None, alias="Memory")
    nano_cpus: int | None = Field(default=None, alias="NanoCpus")
    cgroup_parent: str | None = Field(default=None, alias="CgroupParent")
    blkio_weight: int | None = Field(default=None, alias="BlkioWeight")
    blkio_weight_device: list[Any] | None = Field(
        default=None, alias="BlkioWeightDevice"
    )
    blkio_device_read_bps: list[Any] | None = Field(
        default=None, alias="BlkioDeviceReadBps"
    )
    blkio_device_write_bps: list[Any] | None = Field(
        default=None, alias="BlkioDeviceWriteBps"
    )
    blkio_device_read_iops: list[Any] | None = Field(
        default=None, alias="BlkioDeviceReadIOps"
    )
    blkio_device_write_iops: list[Any] | None = Field(
        default=None, alias="BlkioDeviceWriteIOps"
    )
    cpu_period: int | None = Field(default=None, alias="CpuPeriod")
    cpu_quota: int | None = Field(default=None, alias="CpuQuota")
    cpu_realtime_period: int | None = Field(default=None, alias="CpuRealtimePeriod")
    cpu_realtime_runtime: int | None = Field(default=None, alias="CpuRealtimeRuntime")
    cpuset_cpus: str | list[int] | None = Field(default=None, alias="CpusetCpus")
    cpuset_mems: str | list[int] | None = Field(default=None, alias="CpusetMems")
    devices: list[Any] | None = Field(default=None, alias="Devices")
    device_cgroup_rules: list[str] | None = Field(
        default=None, alias="DeviceCgroupRules"
    )
    device_requests: list[ContainerDeviceRequest] | None = Field(
        default=None, alias="DeviceRequests"
    )
    memory_reservation: int | None = Field(default=None, alias="MemoryReservation")
    memory_swap: int | None = Field(default=None, alias="MemorySwap")
    memory_swappiness: int | None = Field(default=None, alias="MemorySwappiness")
    oom_kill_disable: bool | None = Field(default=None, alias="OomKillDisable")
    pids_limit: int | None = Field(default=None, alias="PidsLimit")
    ulimits: list[ContainerUlimit] | None = Field(default=None, alias="Ulimits")
    cpu_count: int | None = Field(default=None, alias="CpuCount")
    cpu_percent: int | None = Field(default=None, alias="CpuPercent")
    io_maximum_iops: int | None = Field(default=None, alias="IOMaximumIOps")
    io_maximum_bandwidth: int | None = Field(default=None, alias="IOMaximumBandwidth")
    mounts: list[Mount] | None = Field(default=None, alias="Mounts")
    init: bool | None = Field(default=None, alias="Init")
    kernel_memory: int | None = Field(default=None, alias="KernelMemory")


class ContainerHealthState(RuntimeBaseModel):
    status: str | None = Field(default=None, alias="Status")
    failing_streak: int | None = Field(default=None, alias="FailingStreak")
    log: list[Any] | None = Field(default=None, alias="Log")


class ContainerState(RuntimeBaseModel):
    status: str | None = Field(default=None, alias="Status")
    running: bool | None = Field(default=None, alias="Running")
    paused: bool | None = Field(default=None, alias="Paused")
    restarting: bool | None = Field(default=None, alias="Restarting")
    oom_killed: bool | None = Field(default=None, alias="OOMKilled")
    dead: bool | None = Field(default=None, alias="Dead")
    pid: int | None = Field(default=None, alias="Pid")
    exit_code: int | None = Field(default=None, alias="ExitCode")
    error: str | None = Field(default=None, alias="Error")
    started_at: datetime | str | None = Field(default=None, alias="StartedAt")
    finished_at: datetime | str | None = Field(default=None, alias="FinishedAt")
    health: ContainerHealthState | None = Field(default=None, alias="Health")


class NetworkEndpointIPAMConfig(RuntimeBaseModel):
    ipv4_address: str | None = Field(default=None, alias="IPv4Address")
    ipv6_address: str | None = Field(default=None, alias="IPv6Address")
    link_local_ips: list[str] | None = Field(default=None, alias="LinkLocalIPs")


class NetworkEndpointSettings(RuntimeBaseModel):
    ipam_config: NetworkEndpointIPAMConfig | None = Field(
        default=None, alias="IPAMConfig"
    )
    links: list[str] | None = Field(default=None, alias="Links")
    aliases: list[str] | None = Field(default=None, alias="Aliases")
    network_id: str | None = Field(default=None, alias="NetworkID")
    endpoint_id: str | None = Field(default=None, alias="EndpointID")
    gateway: str | None = Field(default=None, alias="Gateway")
    ip_address: str | None = Field(default=None, alias="IPAddress")
    ip_prefix_len: int | None = Field(default=None, alias="IPPrefixLen")
    ipv6_gateway: str | None = Field(default=None, alias="IPv6Gateway")
    global_ipv6_address: str | None = Field(default=None, alias="GlobalIPv6Address")
    global_ipv6_prefix_len: int | None = Field(
        default=None, alias="GlobalIPv6PrefixLen"
    )
    mac_address: str | None = Field(default=None, alias="MacAddress")
    driver_opts: dict[str, str] | None = Field(default=None, alias="DriverOpts")
    gateway_priority: int | None = Field(default=None, alias="GatewayPriority")


class NetworkSettings(RuntimeBaseModel):
    bridge: str | None = Field(default=None, alias="Bridge")
    sandbox_id: str | None = Field(default=None, alias="SandboxID")
    hairpin_mode: bool | None = Field(default=None, alias="HairpinMode")
    link_local_ipv6_address: str | None = Field(
        default=None, alias="LinkLocalIPv6Address"
    )
    link_local_ipv6_prefix_len: int | None = Field(
        default=None, alias="LinkLocalIPv6PrefixLen"
    )
    ports: dict[str, list[PortBinding] | None] | None = Field(
        default=None, alias="Ports"
    )
    sandbox_key: str | None = Field(default=None, alias="SandboxKey")
    secondary_ip_addresses: list[Any] | None = Field(
        default=None, alias="SecondaryIPAddresses"
    )
    secondary_ipv6_addresses: list[Any] | None = Field(
        default=None, alias="SecondaryIPv6Addresses"
    )
    endpoint_id: str | None = Field(default=None, alias="EndpointID")
    gateway: str | None = Field(default=None, alias="Gateway")
    global_ipv6_address: str | None = Field(default=None, alias="GlobalIPv6Address")
    global_ipv6_prefix_len: int | None = Field(
        default=None, alias="GlobalIPv6PrefixLen"
    )
    ip_address: str | None = Field(default=None, alias="IPAddress")
    ip_prefix_len: int | None = Field(default=None, alias="IPPrefixLen")
    ipv6_gateway: str | None = Field(default=None, alias="IPv6Gateway")
    mac_address: str | None = Field(default=None, alias="MacAddress")
    networks: dict[str, NetworkEndpointSettings] | None = Field(
        default=None, alias="Networks"
    )


class ContainerInspectResult(RuntimeBaseModel):
    id: str = Field(alias="Id")
    created: datetime | str | None = Field(default=None, alias="Created")
    path: str | None = Field(default=None, alias="Path")
    args: list[str] | None = Field(default=None, alias="Args")
    state: ContainerState | None = Field(default=None, alias="State")
    image: str | None = Field(default=None, alias="Image")
    resolv_conf_path: str | None = Field(default=None, alias="ResolvConfPath")
    hostname_path: str | None = Field(default=None, alias="HostnamePath")
    hosts_path: str | None = Field(default=None, alias="HostsPath")
    log_path: str | None = Field(default=None, alias="LogPath")
    name: str | None = Field(default=None, alias="Name")
    restart_count: int | None = Field(default=None, alias="RestartCount")
    driver: str | None = Field(default=None, alias="Driver")
    platform: str | None = Field(default=None, alias="Platform")
    mount_label: str | None = Field(default=None, alias="MountLabel")
    process_label: str | None = Field(default=None, alias="ProcessLabel")
    app_armor_profile: str | None = Field(default=None, alias="AppArmorProfile")
    exec_ids: list[str] | None = Field(default=None, alias="ExecIDs")
    host_config: ContainerHostConfig | None = Field(default=None, alias="HostConfig")
    graph_driver: dict[str, Any] | None = Field(default=None, alias="GraphDriver")
    size_rw: int | None = Field(default=None, alias="SizeRw")
    size_root_fs: int | None = Field(default=None, alias="SizeRootFs")
    mounts: list[Mount] | None = Field(default=None, alias="Mounts")
    config: ContainerConfig | None = Field(default=None, alias="Config")
    network_settings: NetworkSettings | None = Field(
        default=None, alias="NetworkSettings"
    )
    pod: str | None = Field(default=None, alias="Pod")

    @field_validator("name", mode="after")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v and v.startswith("/"):
            return v[1:]
        return v


class ImageInspectResult(RuntimeBaseModel):
    id: str | None = Field(default=None, alias="Id")
    repo_tags: list[str] | None = Field(default=None, alias="RepoTags")
    repo_digests: list[str] | None = Field(default=None, alias="RepoDigests")
    parent: str | None = Field(default=None, alias="Parent")
    comment: str | None = Field(default=None, alias="Comment")
    created: datetime | str | None = Field(default=None, alias="Created")
    container: str | None = Field(default=None, alias="Container")
    container_config: ContainerConfig | None = Field(
        default=None, alias="ContainerConfig"
    )
    docker_version: str | None = Field(default=None, alias="DockerVersion")
    author: str | None = Field(default=None, alias="Author")
    config: ContainerConfig | None = Field(default=None, alias="Config")
    architecture: str | None = Field(default=None, alias="Architecture")
    os: str | None = Field(default=None, alias="Os")
    size: int | None = Field(default=None, alias="Size")
    virtual_size: int | None = Field(default=None, alias="VirtualSize")
    graph_driver: dict[str, Any] | None = Field(default=None, alias="GraphDriver")
    root_fs: dict[str, Any] | None = Field(default=None, alias="RootFS")
    metadata: dict[str, Any] | None = Field(default=None, alias="Metadata")


class RuntimeVersion(RuntimeBaseModel):
    version: str | None = Field(default=None, alias="Version")
    api_version: str | None = Field(default=None, alias="ApiVersion")
    min_api_version: str | None = Field(default=None, alias="MinAPIVersion")
    git_commit: str | None = Field(default=None, alias="GitCommit")
    go_version: str | None = Field(default=None, alias="GoVersion")
    os: str | None = Field(default=None, alias="Os")
    arch: str | None = Field(default=None, alias="Arch")
    kernel_version: str | None = Field(default=None, alias="KernelVersion")
    components: list[dict[str, Any]] | None = Field(default=None, alias="Components")
    platform: dict[str, Any] | None = Field(default=None, alias="Platform")
    runtime_type: str = "docker"
    negotiated_api: str | None = None
    libpod_api_version: str | None = None
