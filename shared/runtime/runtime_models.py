from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class RuntimeBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
    )


class PortBinding(RuntimeBaseModel):
    host_ip: str | None = Field(
        default=None, validation_alias=AliasChoices("HostIp", "host_ip")
    )
    host_port: str | None = Field(
        default=None, validation_alias=AliasChoices("HostPort", "host_port")
    )


class Mount(RuntimeBaseModel):
    target: str | None = Field(
        default=None, validation_alias=AliasChoices("Target", "target")
    )
    destination: str | None = Field(
        default=None, validation_alias=AliasChoices("Destination", "destination")
    )
    source: str | None = Field(
        default=None, validation_alias=AliasChoices("Source", "source")
    )
    type: str | None = Field(
        default="volume", validation_alias=AliasChoices("Type", "type")
    )
    read_only: bool | None = Field(
        default=None, validation_alias=AliasChoices("ReadOnly", "read_only")
    )
    rw: bool | None = Field(default=None, validation_alias=AliasChoices("RW", "rw"))
    consistency: str | None = Field(
        default=None, validation_alias=AliasChoices("Consistency", "consistency")
    )
    bind_options: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("BindOptions", "bind_options")
    )
    volume_options: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("VolumeOptions", "volume_options")
    )
    tmpfs_options: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("TmpfsOptions", "tmpfs_options")
    )
    image_options: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("ImageOptions", "image_options")
    )
    name: str | None = Field(
        default=None, validation_alias=AliasChoices("Name", "name")
    )
    driver: str | None = Field(
        default=None, validation_alias=AliasChoices("Driver", "driver")
    )
    mode: str | None = Field(
        default=None, validation_alias=AliasChoices("Mode", "mode")
    )
    propagation: str | None = Field(
        default=None, validation_alias=AliasChoices("Propagation", "propagation")
    )

    @field_validator("destination", mode="before")
    @classmethod
    def populate_destination_from_target(cls, v: Any, info: Any) -> Any:
        return v


class ContainerHealthCheck(RuntimeBaseModel):
    test: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Test", "test")
    )
    interval: int | None = Field(
        default=None, validation_alias=AliasChoices("Interval", "interval")
    )
    timeout: int | None = Field(
        default=None, validation_alias=AliasChoices("Timeout", "timeout")
    )
    retries: int | None = Field(
        default=None, validation_alias=AliasChoices("Retries", "retries")
    )
    start_period: int | None = Field(
        default=None, validation_alias=AliasChoices("StartPeriod", "start_period")
    )
    start_interval: int | None = Field(
        default=None, validation_alias=AliasChoices("StartInterval", "start_interval")
    )


class ContainerConfig(RuntimeBaseModel):
    hostname: str | None = Field(
        default=None, validation_alias=AliasChoices("Hostname", "hostname")
    )
    domainname: str | None = Field(
        default=None, validation_alias=AliasChoices("Domainname", "domainname")
    )
    user: str | None = Field(
        default=None, validation_alias=AliasChoices("User", "user")
    )
    attach_stdin: bool | None = Field(
        default=None, validation_alias=AliasChoices("AttachStdin", "attach_stdin")
    )
    attach_stdout: bool | None = Field(
        default=None, validation_alias=AliasChoices("AttachStdout", "attach_stdout")
    )
    attach_stderr: bool | None = Field(
        default=None, validation_alias=AliasChoices("AttachStderr", "attach_stderr")
    )
    tty: bool | None = Field(default=None, validation_alias=AliasChoices("Tty", "tty"))
    open_stdin: bool | None = Field(
        default=None, validation_alias=AliasChoices("OpenStdin", "open_stdin")
    )
    stdin_once: bool | None = Field(
        default=None, validation_alias=AliasChoices("StdinOnce", "stdin_once")
    )
    env: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Env", "env")
    )
    cmd: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Cmd", "cmd")
    )
    healthcheck: ContainerHealthCheck | None = Field(
        default=None, validation_alias=AliasChoices("Healthcheck", "healthcheck")
    )
    args_escaped: bool | None = Field(
        default=None, validation_alias=AliasChoices("ArgsEscaped", "args_escaped")
    )
    image: str | None = Field(
        default=None, validation_alias=AliasChoices("Image", "image")
    )
    volumes: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("Volumes", "volumes")
    )
    working_dir: str | None = Field(
        default=None, validation_alias=AliasChoices("WorkingDir", "working_dir")
    )
    entrypoint: list[str] | str | None = Field(
        default=None, validation_alias=AliasChoices("Entrypoint", "entrypoint")
    )
    network_disabled: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("NetworkDisabled", "network_disabled"),
    )
    mac_address: str | None = Field(
        default=None, validation_alias=AliasChoices("MacAddress", "mac_address")
    )
    on_build: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("OnBuild", "on_build")
    )
    labels: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("Labels", "labels")
    )
    stop_signal: str | None = Field(
        default=None, validation_alias=AliasChoices("StopSignal", "stop_signal")
    )
    stop_timeout: int | None = Field(
        default=None, validation_alias=AliasChoices("StopTimeout", "stop_timeout")
    )
    shell: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Shell", "shell")
    )
    exposed_ports: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("ExposedPorts", "exposed_ports")
    )
    systemd_mode: str | bool | None = Field(
        default=None, validation_alias=AliasChoices("SystemdMode", "systemd_mode")
    )


class ContainerDevice(RuntimeBaseModel):
    path_on_host: str | None = Field(
        default=None, validation_alias=AliasChoices("PathOnHost", "path_on_host")
    )
    path_in_container: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PathInContainer", "path_in_container"),
    )
    cgroup_permissions: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CgroupPermissions", "cgroup_permissions"),
    )


class ContainerDeviceRequest(RuntimeBaseModel):
    driver: str | None = Field(
        default=None, validation_alias=AliasChoices("Driver", "driver")
    )
    count: int | None = Field(
        default=None, validation_alias=AliasChoices("Count", "count")
    )
    device_ids: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("DeviceIDs", "device_ids")
    )
    capabilities: list[list[str]] | list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Capabilities", "capabilities")
    )
    options: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("Options", "options")
    )


class ContainerUlimit(RuntimeBaseModel):
    name: str | None = Field(
        default=None, validation_alias=AliasChoices("Name", "name")
    )
    soft: int | None = Field(
        default=None, validation_alias=AliasChoices("Soft", "soft")
    )
    hard: int | None = Field(
        default=None, validation_alias=AliasChoices("Hard", "hard")
    )


class ContainerLogConfig(RuntimeBaseModel):
    type: str | None = Field(
        default=None, validation_alias=AliasChoices("Type", "type")
    )
    config: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("Config", "config")
    )


class ContainerRestartPolicy(RuntimeBaseModel):
    name: str | None = Field(
        default=None, validation_alias=AliasChoices("Name", "name")
    )
    maximum_retry_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("MaximumRetryCount", "maximum_retry_count"),
    )


class ContainerHostConfig(RuntimeBaseModel):
    binds: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Binds", "binds")
    )
    container_id_file: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ContainerIDFile", "container_id_file"),
    )
    log_config: ContainerLogConfig | None = Field(
        default=None, validation_alias=AliasChoices("LogConfig", "log_config")
    )
    network_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("NetworkMode", "network_mode")
    )
    port_bindings: dict[str, list[PortBinding] | None] | None = Field(
        default=None, validation_alias=AliasChoices("PortBindings", "port_bindings")
    )
    restart_policy: ContainerRestartPolicy | None = Field(
        default=None, validation_alias=AliasChoices("RestartPolicy", "restart_policy")
    )
    auto_remove: bool | None = Field(
        default=None, validation_alias=AliasChoices("AutoRemove", "auto_remove")
    )
    volume_driver: str | None = Field(
        default=None, validation_alias=AliasChoices("VolumeDriver", "volume_driver")
    )
    volumes_from: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("VolumesFrom", "volumes_from")
    )
    cap_add: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("CapAdd", "cap_add")
    )
    cap_drop: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("CapDrop", "cap_drop")
    )
    cgroupns_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("CgroupnsMode", "cgroupns_mode")
    )
    dns: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Dns", "dns")
    )
    dns_options: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("DnsOptions", "dns_options")
    )
    dns_search: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("DnsSearch", "dns_search")
    )
    extra_hosts: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("ExtraHosts", "extra_hosts")
    )
    group_add: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("GroupAdd", "group_add")
    )
    ipc_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("IpcMode", "ipc_mode")
    )
    cgroup: str | None = Field(
        default=None, validation_alias=AliasChoices("Cgroup", "cgroup")
    )
    links: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Links", "links")
    )
    oom_score_adj: int | None = Field(
        default=None, validation_alias=AliasChoices("OomScoreAdj", "oom_score_adj")
    )
    pid_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("PidMode", "pid_mode")
    )
    privileged: bool | None = Field(
        default=None, validation_alias=AliasChoices("Privileged", "privileged")
    )
    publish_all_ports: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("PublishAllPorts", "publish_all_ports"),
    )
    readonly_rootfs: bool | None = Field(
        default=None, validation_alias=AliasChoices("ReadonlyRootfs", "readonly_rootfs")
    )
    security_opt: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("SecurityOpt", "security_opt")
    )
    storage_opt: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("StorageOpt", "storage_opt")
    )
    tmpfs: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("Tmpfs", "tmpfs")
    )
    uts_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("UTSMode", "uts_mode")
    )
    userns_mode: str | None = Field(
        default=None, validation_alias=AliasChoices("UsernsMode", "userns_mode")
    )
    shm_size: int | None = Field(
        default=None, validation_alias=AliasChoices("ShmSize", "shm_size")
    )
    sysctls: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("Sysctls", "sysctls")
    )
    runtime: str | None = Field(
        default=None, validation_alias=AliasChoices("Runtime", "runtime")
    )
    isolation: str | None = Field(
        default=None, validation_alias=AliasChoices("Isolation", "isolation")
    )
    cpu_shares: int | None = Field(
        default=None, validation_alias=AliasChoices("CpuShares", "cpu_shares")
    )
    memory: int | None = Field(
        default=None, validation_alias=AliasChoices("Memory", "memory")
    )
    nano_cpus: int | None = Field(
        default=None, validation_alias=AliasChoices("NanoCpus", "nano_cpus")
    )
    cgroup_parent: str | None = Field(
        default=None, validation_alias=AliasChoices("CgroupParent", "cgroup_parent")
    )
    blkio_weight: int | None = Field(
        default=None, validation_alias=AliasChoices("BlkioWeight", "blkio_weight")
    )
    blkio_weight_device: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("BlkioWeightDevice", "blkio_weight_device"),
    )
    blkio_device_read_bps: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("BlkioDeviceReadBps", "blkio_device_read_bps"),
    )
    blkio_device_write_bps: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("BlkioDeviceWriteBps", "blkio_device_write_bps"),
    )
    blkio_device_read_iops: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("BlkioDeviceReadIOps", "blkio_device_read_iops"),
    )
    blkio_device_write_iops: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BlkioDeviceWriteIOps", "blkio_device_write_iops"
        ),
    )
    cpu_period: int | None = Field(
        default=None, validation_alias=AliasChoices("CpuPeriod", "cpu_period")
    )
    cpu_quota: int | None = Field(
        default=None, validation_alias=AliasChoices("CpuQuota", "cpu_quota")
    )
    cpu_realtime_period: int | None = Field(
        default=None,
        validation_alias=AliasChoices("CpuRealtimePeriod", "cpu_realtime_period"),
    )
    cpu_realtime_runtime: int | None = Field(
        default=None,
        validation_alias=AliasChoices("CpuRealtimeRuntime", "cpu_realtime_runtime"),
    )
    cpuset_cpus: str | list[int] | None = Field(
        default=None, validation_alias=AliasChoices("CpusetCpus", "cpuset_cpus")
    )
    cpuset_mems: str | list[int] | None = Field(
        default=None, validation_alias=AliasChoices("CpusetMems", "cpuset_mems")
    )
    devices: list[ContainerDevice] | None = Field(
        default=None, validation_alias=AliasChoices("Devices", "devices")
    )
    device_cgroup_rules: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("DeviceCgroupRules", "device_cgroup_rules"),
    )
    device_requests: list[ContainerDeviceRequest] | None = Field(
        default=None, validation_alias=AliasChoices("DeviceRequests", "device_requests")
    )
    memory_reservation: int | None = Field(
        default=None,
        validation_alias=AliasChoices("MemoryReservation", "memory_reservation"),
    )
    memory_swap: int | None = Field(
        default=None, validation_alias=AliasChoices("MemorySwap", "memory_swap")
    )
    memory_swappiness: int | None = Field(
        default=None,
        validation_alias=AliasChoices("MemorySwappiness", "memory_swappiness"),
    )
    oom_kill_disable: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("OomKillDisable", "oom_kill_disable"),
    )
    pids_limit: int | None = Field(
        default=None, validation_alias=AliasChoices("PidsLimit", "pids_limit")
    )
    ulimits: list[ContainerUlimit] | None = Field(
        default=None, validation_alias=AliasChoices("Ulimits", "ulimits")
    )
    cpu_count: int | None = Field(
        default=None, validation_alias=AliasChoices("CpuCount", "cpu_count")
    )
    cpu_percent: int | None = Field(
        default=None, validation_alias=AliasChoices("CpuPercent", "cpu_percent")
    )
    io_maximum_iops: int | None = Field(
        default=None, validation_alias=AliasChoices("IOMaximumIOps", "io_maximum_iops")
    )
    io_maximum_bandwidth: int | None = Field(
        default=None,
        validation_alias=AliasChoices("IOMaximumBandwidth", "io_maximum_bandwidth"),
    )
    mounts: list[Mount] | None = Field(
        default=None, validation_alias=AliasChoices("Mounts", "mounts")
    )
    init: bool | None = Field(
        default=None, validation_alias=AliasChoices("Init", "init")
    )
    kernel_memory: int | None = Field(
        default=None, validation_alias=AliasChoices("KernelMemory", "kernel_memory")
    )


class ContainerHealthState(RuntimeBaseModel):
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("Status", "status")
    )
    failing_streak: int | None = Field(
        default=None, validation_alias=AliasChoices("FailingStreak", "failing_streak")
    )
    log: list[Any] | None = Field(
        default=None, validation_alias=AliasChoices("Log", "log")
    )


class ContainerState(RuntimeBaseModel):
    status: str | None = Field(
        default=None, validation_alias=AliasChoices("Status", "status")
    )
    running: bool | None = Field(
        default=None, validation_alias=AliasChoices("Running", "running")
    )
    paused: bool | None = Field(
        default=None, validation_alias=AliasChoices("Paused", "paused")
    )
    restarting: bool | None = Field(
        default=None, validation_alias=AliasChoices("Restarting", "restarting")
    )
    oom_killed: bool | None = Field(
        default=None, validation_alias=AliasChoices("OOMKilled", "oom_killed")
    )
    dead: bool | None = Field(
        default=None, validation_alias=AliasChoices("Dead", "dead")
    )
    pid: int | None = Field(default=None, validation_alias=AliasChoices("Pid", "pid"))
    exit_code: int | None = Field(
        default=None, validation_alias=AliasChoices("ExitCode", "exit_code")
    )
    error: str | None = Field(
        default=None, validation_alias=AliasChoices("Error", "error")
    )
    started_at: datetime | None = Field(
        default=None, validation_alias=AliasChoices("StartedAt", "started_at")
    )
    finished_at: datetime | None = Field(
        default=None, validation_alias=AliasChoices("FinishedAt", "finished_at")
    )
    health: ContainerHealthState | None = Field(
        default=None, validation_alias=AliasChoices("Health", "health")
    )


class NetworkEndpointIPAMConfig(RuntimeBaseModel):
    ipv4_address: str | None = Field(
        default=None, validation_alias=AliasChoices("IPv4Address", "ipv4_address")
    )
    ipv6_address: str | None = Field(
        default=None, validation_alias=AliasChoices("IPv6Address", "ipv6_address")
    )
    link_local_ips: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("LinkLocalIPs", "link_local_ips")
    )


class NetworkEndpointSettings(RuntimeBaseModel):
    ipam_config: NetworkEndpointIPAMConfig | None = Field(
        default=None, validation_alias=AliasChoices("IPAMConfig", "ipam_config")
    )
    links: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Links", "links")
    )
    aliases: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Aliases", "aliases")
    )
    network_id: str | None = Field(
        default=None, validation_alias=AliasChoices("NetworkID", "network_id")
    )
    endpoint_id: str | None = Field(
        default=None, validation_alias=AliasChoices("EndpointID", "endpoint_id")
    )
    gateway: str | None = Field(
        default=None, validation_alias=AliasChoices("Gateway", "gateway")
    )
    ip_address: str | None = Field(
        default=None, validation_alias=AliasChoices("IPAddress", "ip_address")
    )
    ip_prefix_len: int | None = Field(
        default=None, validation_alias=AliasChoices("IPPrefixLen", "ip_prefix_len")
    )
    ipv6_gateway: str | None = Field(
        default=None, validation_alias=AliasChoices("IPv6Gateway", "ipv6_gateway")
    )
    global_ipv6_address: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GlobalIPv6Address", "global_ipv6_address"),
    )
    global_ipv6_prefix_len: int | None = Field(
        default=None,
        validation_alias=AliasChoices("GlobalIPv6PrefixLen", "global_ipv6_prefix_len"),
    )
    mac_address: str | None = Field(
        default=None, validation_alias=AliasChoices("MacAddress", "mac_address")
    )
    driver_opts: dict[str, str] | None = Field(
        default=None, validation_alias=AliasChoices("DriverOpts", "driver_opts")
    )
    gateway_priority: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GwPriority", "GatewayPriority", "gateway_priority"
        ),
    )


class NetworkSettings(RuntimeBaseModel):
    bridge: str | None = Field(
        default=None, validation_alias=AliasChoices("Bridge", "bridge")
    )
    sandbox_id: str | None = Field(
        default=None, validation_alias=AliasChoices("SandboxID", "sandbox_id")
    )
    hairpin_mode: bool | None = Field(
        default=None, validation_alias=AliasChoices("HairpinMode", "hairpin_mode")
    )
    link_local_ipv6_address: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LinkLocalIPv6Address", "link_local_ipv6_address"
        ),
    )
    link_local_ipv6_prefix_len: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LinkLocalIPv6PrefixLen", "link_local_ipv6_prefix_len"
        ),
    )
    ports: dict[str, list[PortBinding] | None] | None = Field(
        default=None, validation_alias=AliasChoices("Ports", "ports")
    )
    sandbox_key: str | None = Field(
        default=None, validation_alias=AliasChoices("SandboxKey", "sandbox_key")
    )
    secondary_ip_addresses: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("SecondaryIPAddresses", "secondary_ip_addresses"),
    )
    secondary_ipv6_addresses: list[Any] | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SecondaryIPv6Addresses", "secondary_ipv6_addresses"
        ),
    )
    endpoint_id: str | None = Field(
        default=None, validation_alias=AliasChoices("EndpointID", "endpoint_id")
    )
    gateway: str | None = Field(
        default=None, validation_alias=AliasChoices("Gateway", "gateway")
    )
    global_ipv6_address: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GlobalIPv6Address", "global_ipv6_address"),
    )
    global_ipv6_prefix_len: int | None = Field(
        default=None,
        validation_alias=AliasChoices("GlobalIPv6PrefixLen", "global_ipv6_prefix_len"),
    )
    ip_address: str | None = Field(
        default=None, validation_alias=AliasChoices("IPAddress", "ip_address")
    )
    ip_prefix_len: int | None = Field(
        default=None, validation_alias=AliasChoices("IPPrefixLen", "ip_prefix_len")
    )
    ipv6_gateway: str | None = Field(
        default=None, validation_alias=AliasChoices("IPv6Gateway", "ipv6_gateway")
    )
    mac_address: str | None = Field(
        default=None, validation_alias=AliasChoices("MacAddress", "mac_address")
    )
    networks: dict[str, NetworkEndpointSettings] | None = Field(
        default=None, validation_alias=AliasChoices("Networks", "networks")
    )


class ContainerInspectResult(RuntimeBaseModel):
    id: str | None = Field(default=None, validation_alias=AliasChoices("Id", "id"))
    created: datetime | None = Field(
        default=None, validation_alias=AliasChoices("Created", "created")
    )
    path: str | None = Field(
        default=None, validation_alias=AliasChoices("Path", "path")
    )
    args: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("Args", "args")
    )
    state: ContainerState | None = Field(
        default=None, validation_alias=AliasChoices("State", "state")
    )
    image: str | None = Field(
        default=None, validation_alias=AliasChoices("Image", "image")
    )
    resolv_conf_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ResolvConfPath", "resolv_conf_path"),
    )
    hostname_path: str | None = Field(
        default=None, validation_alias=AliasChoices("HostnamePath", "hostname_path")
    )
    hosts_path: str | None = Field(
        default=None, validation_alias=AliasChoices("HostsPath", "hosts_path")
    )
    log_path: str | None = Field(
        default=None, validation_alias=AliasChoices("LogPath", "log_path")
    )
    name: str | None = Field(
        default=None, validation_alias=AliasChoices("Name", "name")
    )
    restart_count: int | None = Field(
        default=None, validation_alias=AliasChoices("RestartCount", "restart_count")
    )
    driver: str | None = Field(
        default=None, validation_alias=AliasChoices("Driver", "driver")
    )
    platform: str | None = Field(
        default=None, validation_alias=AliasChoices("Platform", "platform")
    )
    mount_label: str | None = Field(
        default=None, validation_alias=AliasChoices("MountLabel", "mount_label")
    )
    process_label: str | None = Field(
        default=None, validation_alias=AliasChoices("ProcessLabel", "process_label")
    )
    app_armor_profile: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AppArmorProfile", "app_armor_profile"),
    )
    exec_ids: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("ExecIDs", "exec_ids")
    )
    host_config: ContainerHostConfig | None = Field(
        default=None, validation_alias=AliasChoices("HostConfig", "host_config")
    )
    graph_driver: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("GraphDriver", "graph_driver")
    )
    size_rw: int | None = Field(
        default=None, validation_alias=AliasChoices("SizeRw", "size_rw")
    )
    size_root_fs: int | None = Field(
        default=None, validation_alias=AliasChoices("SizeRootFs", "size_root_fs")
    )
    mounts: list[Mount] | None = Field(
        default=None, validation_alias=AliasChoices("Mounts", "mounts")
    )
    config: ContainerConfig | None = Field(
        default=None, validation_alias=AliasChoices("Config", "config")
    )
    network_settings: NetworkSettings | None = Field(
        default=None,
        validation_alias=AliasChoices("NetworkSettings", "network_settings"),
    )
    pod: str | None = Field(default=None, validation_alias=AliasChoices("Pod", "pod"))

    @field_validator("name", mode="after")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        if v and v.startswith("/"):
            return v[1:]
        return v


class ImageInspectResult(RuntimeBaseModel):
    id: str | None = Field(default=None, validation_alias=AliasChoices("Id", "id"))
    repo_tags: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("RepoTags", "repo_tags")
    )
    repo_digests: list[str] | None = Field(
        default=None, validation_alias=AliasChoices("RepoDigests", "repo_digests")
    )
    parent: str | None = Field(
        default=None, validation_alias=AliasChoices("Parent", "parent")
    )
    comment: str | None = Field(
        default=None, validation_alias=AliasChoices("Comment", "comment")
    )
    created: datetime | None = Field(
        default=None, validation_alias=AliasChoices("Created", "created")
    )
    container: str | None = Field(
        default=None, validation_alias=AliasChoices("Container", "container")
    )
    container_config: ContainerConfig | None = Field(
        default=None,
        validation_alias=AliasChoices("ContainerConfig", "container_config"),
    )
    docker_version: str | None = Field(
        default=None, validation_alias=AliasChoices("DockerVersion", "docker_version")
    )
    author: str | None = Field(
        default=None, validation_alias=AliasChoices("Author", "author")
    )
    config: ContainerConfig | None = Field(
        default=None, validation_alias=AliasChoices("Config", "config")
    )
    architecture: str | None = Field(
        default=None, validation_alias=AliasChoices("Architecture", "architecture")
    )
    os: str | None = Field(default=None, validation_alias=AliasChoices("Os", "os"))
    variant: str | None = Field(
        default=None, validation_alias=AliasChoices("Variant", "variant")
    )
    size: int | None = Field(
        default=None, validation_alias=AliasChoices("Size", "size")
    )
    virtual_size: int | None = Field(
        default=None, validation_alias=AliasChoices("VirtualSize", "virtual_size")
    )
    graph_driver: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("GraphDriver", "graph_driver")
    )
    root_fs: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("RootFS", "root_fs")
    )
    metadata: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("Metadata", "metadata")
    )


class RuntimeVersion(RuntimeBaseModel):
    version: str | None = Field(
        default=None, validation_alias=AliasChoices("Version", "version")
    )
    api_version: str | None = Field(
        default=None, validation_alias=AliasChoices("ApiVersion", "api_version")
    )
    min_api_version: str | None = Field(
        default=None, validation_alias=AliasChoices("MinAPIVersion", "min_api_version")
    )
    git_commit: str | None = Field(
        default=None, validation_alias=AliasChoices("GitCommit", "git_commit")
    )
    go_version: str | None = Field(
        default=None, validation_alias=AliasChoices("GoVersion", "go_version")
    )
    os: str | None = Field(default=None, validation_alias=AliasChoices("Os", "os"))
    variant: str | None = Field(
        default=None, validation_alias=AliasChoices("Variant", "variant")
    )
    arch: str | None = Field(
        default=None, validation_alias=AliasChoices("Arch", "arch")
    )
    kernel_version: str | None = Field(
        default=None, validation_alias=AliasChoices("KernelVersion", "kernel_version")
    )
    components: list[dict[str, Any]] | None = Field(
        default=None, validation_alias=AliasChoices("Components", "components")
    )
    platform: dict[str, Any] | None = Field(
        default=None, validation_alias=AliasChoices("Platform", "platform")
    )
    runtime_type: str = "docker"
    negotiated_api: str | None = None
    libpod_api_version: str | None = None


NetworkInspectResult = NetworkEndpointSettings
ContainerEndpointIPAMConfig = NetworkEndpointIPAMConfig
