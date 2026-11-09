import re
from typing import Any

from shared.runtime.runtime_errors import RuntimePreflightError
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
    PortMapping,
)

_BYTE_UNITS: dict[str, int] = {
    "b": 1,
    "k": 1024,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
}
_SIZE_RE = re.compile(r"^(-?\d+)\s*([kmgt])i?b?$", re.IGNORECASE)
_GPU_PART_RE = re.compile(
    r"(device|count|capabilities|options)=(.*?)(?=,(?:device|count|capabilities|options)=|$)"
)

# CLI-only fields. They never appear in an engine create body.
_UNSUPPORTED_FIELDS: tuple[str, ...] = (
    "cidfile",
    "env_files",
    "label_files",
    "env_host",
    "pod",
    "pull",
    "content_trust",
    "detach",
    "sig_proxy",
    "systemd",
    "tz",
)


def build_create_request(
    body: CreateContainerRequestBodySchema,
) -> tuple[dict[str, Any], str | None]:
    """Map a CLI-shaped create schema to an engine API create body and name."""
    _reject_unsupported(body)
    payload: dict[str, Any] = {"Image": body.image}
    _set(payload, "Cmd", body.command)
    if body.entrypoint:
        payload["Entrypoint"] = [body.entrypoint]
    env = _env(body.envs)
    if env:
        payload["Env"] = env
    _set(payload, "Labels", body.labels)
    exposed = _exposed_ports(body)
    if exposed:
        payload["ExposedPorts"] = exposed
    health = _healthcheck(body)
    if health:
        payload["Healthcheck"] = health
    if body.stop_signal is not None:
        payload["StopSignal"] = str(body.stop_signal)
    _set(payload, "StopTimeout", body.stop_timeout)
    _set(payload, "User", body.user)
    if body.workdir is not None:
        payload["WorkingDir"] = str(body.workdir)
    _set(payload, "Hostname", body.hostname)
    _set(payload, "Domainname", body.domainname)
    _set(payload, "Tty", body.tty)
    if body.interactive:
        payload["OpenStdin"] = True
        payload["AttachStdin"] = True

    host = _host_config(body)
    if host:
        payload["HostConfig"] = host
    endpoint = _endpoint(body)
    if body.networks and endpoint:
        payload["NetworkingConfig"] = {"EndpointsConfig": {body.networks[0]: endpoint}}
    return payload, body.name


def _reject_unsupported(body: CreateContainerRequestBodySchema) -> None:
    present = [name for name in _UNSUPPORTED_FIELDS if _is_set(getattr(body, name))]
    if not present:
        return
    joined = ", ".join(present)
    raise RuntimePreflightError(
        f"Cannot create container; unsupported fields: {joined}"
    )


def _is_set(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _set(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        return
    target[key] = value


def _env(envs: dict[str, str] | None) -> list[str] | None:
    if not envs:
        return None
    return [f"{key}={value}" for key, value in envs.items()]


def _exposed_ports(body: CreateContainerRequestBodySchema) -> dict[str, dict]:
    ports: dict[str, dict] = {}
    expose = body.expose
    numbers = [expose] if isinstance(expose, int) else (expose or [])
    for number in numbers:
        ports[f"{number}/tcp"] = {}
    for mapping in body.publish or []:
        _, _, container_port, proto = _parse_port(mapping)
        ports[f"{container_port}/{proto}"] = {}
    return ports


def _healthcheck(body: CreateContainerRequestBodySchema) -> dict[str, Any] | None:
    if body.healthcheck is False:
        return {"Test": ["NONE"]}
    result: dict[str, Any] = {}
    if body.health_cmd:
        result["Test"] = ["CMD-SHELL", body.health_cmd]
    _set(result, "Interval", _seconds_to_ns(body.health_interval))
    _set(result, "Timeout", _seconds_to_ns(body.health_timeout))
    _set(result, "Retries", body.health_retries)
    _set(result, "StartPeriod", _seconds_to_ns(body.health_start_period))
    _set(result, "StartInterval", _seconds_to_ns(body.health_start_interval))
    if body.healthcheck and "Test" not in result:
        return None
    return result or None


def _seconds_to_ns(value: int | None) -> int | None:
    if value is None:
        return None
    return value * 1_000_000_000


def _host_config(body: CreateContainerRequestBodySchema) -> dict[str, Any]:
    host: dict[str, Any] = {}
    binds = _binds(body.volumes)
    _set(host, "Binds", binds)
    mounts = _mounts(body.mounts)
    _set(host, "Mounts", mounts)
    bindings = _port_bindings(body.publish)
    if bindings:
        host["PortBindings"] = bindings
    _set(host, "PublishAllPorts", body.publish_all)
    if body.restart:
        host["RestartPolicy"] = _restart(body.restart)
    if body.log_driver or body.log_options:
        host["LogConfig"] = {
            "Type": body.log_driver or "json-file",
            "Config": _pairs(body.log_options),
        }
    devices = _devices(body.devices)
    _set(host, "Devices", devices)
    requests = _device_requests(body.gpus)
    _set(host, "DeviceRequests", requests)
    ulimits = _ulimits(body.ulimit)
    _set(host, "Ulimits", ulimits)
    tmpfs = _tmpfs(body.tmpfs)
    if tmpfs:
        host["Tmpfs"] = tmpfs
    _set(host, "CapAdd", body.cap_add)
    _set(host, "CapDrop", body.cap_drop)
    _set(host, "SecurityOpt", body.security_options)
    _set(host, "Sysctls", body.sysctl)
    extra_hosts = _extra_hosts(body.add_hosts)
    _set(host, "ExtraHosts", extra_hosts)
    _set(host, "Memory", _bytes(body.memory))
    _set(host, "MemoryReservation", _bytes(body.memory_reservation))
    _set(host, "MemorySwap", _bytes(body.memory_swap))
    _set(host, "MemorySwappiness", body.memory_swappiness)
    _set(host, "KernelMemory", _bytes(body.kernel_memory))
    if body.cpus is not None:
        host["NanoCpus"] = round(body.cpus * 1_000_000_000)
    _set(host, "CpuPeriod", body.cpu_period)
    _set(host, "CpuQuota", body.cpu_quota)
    _set(host, "CpuRealtimePeriod", body.cpu_rt_period)
    _set(host, "CpuRealtimeRuntime", body.cpu_rt_runtime)
    _set(host, "CpuShares", body.cpu_shares)
    _set(host, "CpusetCpus", _cpu_set(body.cpuset_cpus))
    _set(host, "CpusetMems", _cpu_set(body.cpuset_mems))
    _set(host, "BlkioWeight", body.blkio_weight)
    _set(host, "BlkioWeightDevice", _blkio_devices(body.blkio_weight_device, "Weight"))
    _set(host, "BlkioDeviceReadBps", _blkio_devices(body.device_read_bps, "Rate"))
    _set(host, "BlkioDeviceReadIOps", _blkio_devices(body.device_read_iops, "Rate"))
    _set(host, "BlkioDeviceWriteBps", _blkio_devices(body.device_write_bps, "Rate"))
    _set(host, "BlkioDeviceWriteIOps", _blkio_devices(body.device_write_iops, "Rate"))
    _set(host, "PidMode", body.pid)
    _set(host, "IpcMode", body.ipc)
    _set(host, "UTSMode", body.uts)
    _set(host, "UsernsMode", body.userns)
    _set(host, "CgroupnsMode", body.cgroupns)
    if body.networks:
        host["NetworkMode"] = body.networks[0]
    _set(host, "Init", body.init)
    _set(host, "Privileged", body.privileged)
    _set(host, "ReadonlyRootfs", body.read_only)
    _set(host, "Runtime", body.runtime)
    _set(host, "ShmSize", _bytes(body.shm_size))
    storage = _storage(body.storage_options)
    if storage:
        host["StorageOpt"] = storage
    _set(host, "VolumeDriver", body.volume_driver)
    _set(host, "VolumesFrom", body.volumes_from)
    _set(host, "Isolation", body.isolation)
    if body.oom_kill is False:
        host["OomKillDisable"] = True
    elif body.oom_kill is True:
        host["OomKillDisable"] = False
    _set(host, "OomScoreAdj", body.oom_score_adj)
    _set(host, "PidsLimit", body.pids_limit)
    _set(host, "GroupAdd", body.groups_add)
    _set(host, "DeviceCgroupRules", body.device_cgroup_rules)
    _set(host, "Dns", body.dns)
    _set(host, "DnsOptions", body.dns_options)
    _set(host, "DnsSearch", body.dns_search)
    _set(host, "CgroupParent", body.cgroup_parent)
    if body.link and (not body.networks or body.networks[0] in {"bridge", "default"}):
        host["Links"] = body.link
    if body.remove:
        host["AutoRemove"] = True
    return host


def _endpoint(body: CreateContainerRequestBodySchema) -> dict[str, Any]:
    endpoint: dict[str, Any] = {}
    ipam: dict[str, Any] = {}
    _set(ipam, "IPv4Address", body.ip)
    _set(ipam, "IPv6Address", body.ip6)
    _set(ipam, "LinkLocalIPs", body.link_local_ip)
    if ipam:
        endpoint["IPAMConfig"] = ipam
    _set(endpoint, "Aliases", body.network_aliases)
    if body.link and body.networks and body.networks[0] not in {"bridge", "default"}:
        endpoint["Links"] = body.link
    _set(endpoint, "MacAddress", body.mac_address)
    _set(endpoint, "GwPriority", body.gateway_priority)
    return endpoint


def _binds(
    volumes: list[tuple[str | Any, str | Any] | tuple[str | Any, str | Any, str]]
    | None,
) -> list[str] | None:
    if not volumes:
        return None
    binds: list[str] = []
    for volume in volumes:
        source, target = str(volume[0]), str(volume[1])
        if len(volume) == 3:
            binds.append(f"{source}:{target}:{volume[2]}")
        else:
            binds.append(f"{source}:{target}")
    return binds


def _mounts(mounts: list[list[str]] | None) -> list[dict[str, Any]] | None:
    if not mounts:
        return None
    result: list[dict[str, Any]] = []
    for parts in mounts:
        mount: dict[str, Any] = {}
        for part in parts:
            if part == "readonly":
                mount["ReadOnly"] = True
                continue
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.lower()
            if key == "type":
                mount["Type"] = value
            elif key in {"dst", "destination", "target"}:
                mount["Target"] = value
            elif key in {"source", "src"}:
                mount["Source"] = value
            elif key == "consistency":
                mount["Consistency"] = value
            elif key == "bind-propagation":
                mount.setdefault("BindOptions", {})["Propagation"] = value
            elif key == "volume-driver":
                mount.setdefault("VolumeOptions", {})["DriverConfig"] = {"Name": value}
        if mount:
            result.append(mount)
    return result or None


def _port_bindings(
    publish: list[PortMapping] | None,
) -> dict[str, list[dict[str, str]]]:
    bindings: dict[str, list[dict[str, str]]] = {}
    for mapping in publish or []:
        host_ip, host_port, container_port, proto = _parse_port(mapping)
        key = f"{container_port}/{proto}"
        bindings.setdefault(key, []).append({"HostIp": host_ip, "HostPort": host_port})
    return bindings


def _parse_port(mapping: PortMapping) -> tuple[str, str, str, str]:
    if isinstance(mapping, int):
        return "", str(mapping), str(mapping), "tcp"
    if isinstance(mapping, str):
        return _parse_port_string(mapping)
    if len(mapping) == 2:
        host_ip, host_port = _split_host(str(mapping[0]))
        return host_ip, host_port, str(mapping[1]), "tcp"
    host_ip, host_port = _split_host(str(mapping[0]))
    return host_ip, host_port, str(mapping[1]), str(mapping[2] or "tcp")


def _parse_port_string(value: str) -> tuple[str, str, str, str]:
    proto = "tcp"
    text = value
    if "/" in text:
        text, proto = text.split("/", 1)
    parts = text.split(":")
    if len(parts) == 1:
        return "", parts[0], parts[0], proto
    if len(parts) == 2:
        return "", parts[0], parts[1], proto
    return parts[0], parts[1], parts[2], proto


def _split_host(host: str) -> tuple[str, str]:
    if host.startswith("["):
        end = host.find("]")
        ip = host[1:end]
        port = host[end + 2 :] if end >= 0 and host[end + 1 : end + 2] == ":" else ""
        return ip, port
    if host.count(":") == 1 and not host.split(":", 1)[0].isdigit():
        ip, port = host.split(":", 1)
        return ip, port
    return "", host


def _restart(value: str) -> dict[str, Any]:
    name, sep, count = value.partition(":")
    policy: dict[str, Any] = {"Name": name}
    if sep and count:
        policy["MaximumRetryCount"] = int(count)
    return policy


def _pairs(options: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for option in options or []:
        key, sep, value = option.partition("=")
        if sep:
            result[key] = value
    return result


def _devices(devices: list[str] | None) -> list[dict[str, str]] | None:
    if not devices:
        return None
    result: list[dict[str, str]] = []
    for device in devices:
        parts = device.split(":")
        if len(parts) < 2:
            raise RuntimePreflightError(f"Cannot parse device: {device}")
        result.append(
            {
                "PathOnHost": parts[0],
                "PathInContainer": parts[1],
                "CgroupPermissions": parts[2] if len(parts) > 2 else "rwm",
            }
        )
    return result


def _device_requests(gpus: int | str | None) -> list[dict[str, Any]] | None:
    if gpus is None:
        return None
    if isinstance(gpus, int):
        return [
            {
                "Driver": "nvidia",
                "Count": gpus,
                "Capabilities": [["gpu"]],
            }
        ]
    text = gpus.strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    if text == "all":
        return [{"Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}]
    request: dict[str, Any] = {"Driver": "nvidia"}
    for key, value in _GPU_PART_RE.findall(text):
        if key == "device":
            if value == "all":
                request["Count"] = -1
            else:
                request["DeviceIDs"] = [item for item in value.split(",") if item]
        elif key == "count":
            request["Count"] = int(value)
        elif key == "capabilities":
            request["Capabilities"] = [[item for item in value.split(",") if item]]
        elif key == "options":
            request["Options"] = _pairs(value.split(","))
    request.setdefault("Capabilities", [["gpu"]])
    return [request]


def _ulimits(ulimits: list[str] | None) -> list[dict[str, Any]] | None:
    if not ulimits:
        return None
    result: list[dict[str, Any]] = []
    for item in ulimits:
        name, sep, limits = item.partition("=")
        if not sep:
            raise RuntimePreflightError(f"Cannot parse ulimit: {item}")
        soft_text, sep, hard_text = limits.partition(":")
        soft = int(soft_text)
        hard = int(hard_text) if sep else soft
        result.append({"Name": name, "Soft": soft, "Hard": hard})
    return result


def _tmpfs(entries: list[str | Any] | None) -> dict[str, str] | None:
    if not entries:
        return None
    result: dict[str, str] = {}
    for entry in entries:
        text = str(entry)
        path, sep, options = text.partition(":")
        result[path] = options if sep else ""
    return result


def _extra_hosts(hosts: list[tuple[str, str]] | None) -> list[str] | None:
    if not hosts:
        return None
    return [f"{host}:{address}" for host, address in hosts]


def _bytes(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    match = _SIZE_RE.fullmatch(text)
    if not match:
        raise RuntimePreflightError(f"Cannot parse size: {value}")
    return int(match.group(1)) * _BYTE_UNITS[match.group(2).lower()]


def _cpu_set(value: list[int] | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return ",".join(str(item) for item in value)


def _blkio_devices(
    items: list[str] | None,
    value_key: str,
) -> list[dict[str, Any]] | None:
    if not items:
        return None
    result: list[dict[str, Any]] = []
    for item in items:
        path, sep, raw = item.rpartition(":")
        if not sep:
            raise RuntimePreflightError(f"Cannot parse block device limit: {item}")
        result.append({"Path": path, value_key: int(raw)})
    return result


def _storage(options: list[str] | None) -> dict[str, str] | None:
    if not options:
        return None
    return _pairs(options)
