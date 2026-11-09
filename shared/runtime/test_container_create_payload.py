import pytest

from shared.runtime.container_create_payload import build_create_request
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.schemas.container_schemas import CreateContainerRequestBodySchema


def _body(**kwargs: object) -> CreateContainerRequestBodySchema:
    return CreateContainerRequestBodySchema.model_validate({"image": "nginx", **kwargs})


def _host(payload: dict) -> dict:
    return payload["HostConfig"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"command": ["nginx", "-g"]}, {"Cmd": ["nginx", "-g"]}),
        ({"entrypoint": "/entry"}, {"Entrypoint": ["/entry"]}),
        ({"envs": {"FOO": "bar"}}, {"Env": ["FOO=bar"]}),
        ({"labels": {"app": "web"}}, {"Labels": {"app": "web"}}),
        ({"user": "app"}, {"User": "app"}),
        ({"workdir": "/srv"}, {"WorkingDir": "/srv"}),
        ({"hostname": "web"}, {"Hostname": "web"}),
        ({"domainname": "internal"}, {"Domainname": "internal"}),
        ({"tty": True}, {"Tty": True}),
        ({"stop_signal": "SIGTERM"}, {"StopSignal": "SIGTERM"}),
        ({"stop_timeout": 15}, {"StopTimeout": 15}),
        ({"expose": [80, 443]}, {"ExposedPorts": {"80/tcp": {}, "443/tcp": {}}}),
        (
            {"healthcheck": False},
            {"Healthcheck": {"Test": ["NONE"]}},
        ),
        (
            {"health_cmd": "true", "health_interval": 10, "health_retries": 3},
            {
                "Healthcheck": {
                    "Test": ["CMD-SHELL", "true"],
                    "Interval": 10_000_000_000,
                    "Retries": 3,
                }
            },
        ),
    ],
)
def test_create_payload_top_level_fields(kwargs: dict, expected: dict) -> None:
    payload, _ = build_create_request(_body(**kwargs))
    for key, value in expected.items():
        assert payload[key] == value


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {"volumes": [("/src", "/dst", "ro")]},
            {"Binds": ["/src:/dst:ro"]},
        ),
        (
            {"mounts": [["type=tmpfs", "dst=/run", "readonly"]]},
            {"Mounts": [{"Type": "tmpfs", "Target": "/run", "ReadOnly": True}]},
        ),
        (
            {"publish": [("127.0.0.1:8080", "80", "tcp")]},
            {"PortBindings": {"80/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}},
        ),
        ({"publish_all": True}, {"PublishAllPorts": True}),
        (
            {"restart": "on-failure:3"},
            {"RestartPolicy": {"Name": "on-failure", "MaximumRetryCount": 3}},
        ),
        (
            {"log_driver": "json-file", "log_options": ["max-size=10m"]},
            {"LogConfig": {"Type": "json-file", "Config": {"max-size": "10m"}}},
        ),
        (
            {"devices": ["/dev/sda:/dev/sda:rw"]},
            {
                "Devices": [
                    {
                        "PathOnHost": "/dev/sda",
                        "PathInContainer": "/dev/sda",
                        "CgroupPermissions": "rw",
                    }
                ]
            },
        ),
        (
            {"gpus": "all"},
            {
                "DeviceRequests": [
                    {"Driver": "nvidia", "Count": -1, "Capabilities": [["gpu"]]}
                ]
            },
        ),
        (
            {"ulimit": ["nofile=1024:2048"]},
            {"Ulimits": [{"Name": "nofile", "Soft": 1024, "Hard": 2048}]},
        ),
        ({"tmpfs": ["/run:rw,noexec"]}, {"Tmpfs": {"/run": "rw,noexec"}}),
        ({"cap_add": ["NET_ADMIN"]}, {"CapAdd": ["NET_ADMIN"]}),
        ({"cap_drop": ["MKNOD"]}, {"CapDrop": ["MKNOD"]}),
        (
            {"security_options": ["no-new-privileges"]},
            {"SecurityOpt": ["no-new-privileges"]},
        ),
        (
            {"sysctl": {"net.ipv4.ip_forward": "1"}},
            {"Sysctls": {"net.ipv4.ip_forward": "1"}},
        ),
        ({"add_hosts": [("db", "10.0.0.5")]}, {"ExtraHosts": ["db:10.0.0.5"]}),
        ({"memory": "512m"}, {"Memory": 512 * 1024 * 1024}),
        ({"memory_reservation": 1024}, {"MemoryReservation": 1024}),
        ({"memory_swap": "1g"}, {"MemorySwap": 1024**3}),
        ({"cpus": 1.5}, {"NanoCpus": 1_500_000_000}),
        ({"cpu_shares": 512}, {"CpuShares": 512}),
        ({"cpuset_cpus": "0-1"}, {"CpusetCpus": "0-1"}),
        ({"blkio_weight": 200}, {"BlkioWeight": 200}),
        (
            {"blkio_weight_device": ["/dev/sda:100"]},
            {"BlkioWeightDevice": [{"Path": "/dev/sda", "Weight": 100}]},
        ),
        (
            {"device_read_bps": ["/dev/sda:1048576"]},
            {"BlkioDeviceReadBps": [{"Path": "/dev/sda", "Rate": 1048576}]},
        ),
        ({"pid": "host"}, {"PidMode": "host"}),
        ({"ipc": "private"}, {"IpcMode": "private"}),
        ({"uts": "host"}, {"UTSMode": "host"}),
        ({"userns": "host"}, {"UsernsMode": "host"}),
        ({"cgroupns": "host"}, {"CgroupnsMode": "host"}),
        ({"networks": ["appnet"]}, {"NetworkMode": "appnet"}),
        ({"init": True}, {"Init": True}),
        ({"privileged": True}, {"Privileged": True}),
        ({"read_only": True}, {"ReadonlyRootfs": True}),
        ({"runtime": "runc"}, {"Runtime": "runc"}),
        ({"shm_size": "64m"}, {"ShmSize": 64 * 1024 * 1024}),
        ({"storage_options": ["size=1G"]}, {"StorageOpt": {"size": "1G"}}),
        ({"volume_driver": "local"}, {"VolumeDriver": "local"}),
        ({"volumes_from": ["other"]}, {"VolumesFrom": ["other"]}),
        ({"isolation": "default"}, {"Isolation": "default"}),
        ({"oom_kill": False}, {"OomKillDisable": True}),
        ({"oom_score_adj": 100}, {"OomScoreAdj": 100}),
        ({"pids_limit": 64}, {"PidsLimit": 64}),
        ({"groups_add": ["audio"]}, {"GroupAdd": ["audio"]}),
        ({"device_cgroup_rules": ["c 1:3 r"]}, {"DeviceCgroupRules": ["c 1:3 r"]}),
        ({"dns": ["1.1.1.1"]}, {"Dns": ["1.1.1.1"]}),
        ({"dns_search": ["example"]}, {"DnsSearch": ["example"]}),
        ({"cgroup_parent": "/app"}, {"CgroupParent": "/app"}),
    ],
)
def test_create_payload_host_config_fields(kwargs: dict, expected: dict) -> None:
    payload, _ = build_create_request(_body(**kwargs))
    host = _host(payload)
    for key, value in expected.items():
        assert host[key] == value


def test_create_payload_primary_network_endpoint() -> None:
    payload, name = build_create_request(
        _body(
            name="web",
            networks=["appnet"],
            network_aliases=["web"],
            ip="172.20.0.8",
            ip6="fd00::8",
            mac_address="02:42:ac:14:00:08",
            gateway_priority=5,
            link=["db"],
        )
    )

    assert name == "web"
    endpoint = payload["NetworkingConfig"]["EndpointsConfig"]["appnet"]
    assert endpoint["Aliases"] == ["web"]
    assert endpoint["IPAMConfig"] == {
        "IPv4Address": "172.20.0.8",
        "IPv6Address": "fd00::8",
    }
    assert endpoint["MacAddress"] == "02:42:ac:14:00:08"
    assert endpoint["GwPriority"] == 5
    assert endpoint["Links"] == ["db"]


def test_create_payload_single_network_has_no_empty_endpoint() -> None:
    payload, _ = build_create_request(_body(networks=["appnet"]))

    assert payload["HostConfig"]["NetworkMode"] == "appnet"
    assert "NetworkingConfig" not in payload


def test_create_payload_attaches_every_network() -> None:
    payload, _ = build_create_request(
        _body(
            networks=["main", "extra", "main"],
            ip="172.20.0.8",
            network_aliases=["web"],
        )
    )

    assert payload["HostConfig"]["NetworkMode"] == "main"
    endpoints = payload["NetworkingConfig"]["EndpointsConfig"]
    assert list(endpoints) == ["main", "extra"]
    assert endpoints["main"]["IPAMConfig"]["IPv4Address"] == "172.20.0.8"
    assert endpoints["main"]["Aliases"] == ["web"]
    assert endpoints["extra"] == {}


def test_create_payload_quoted_gpu_request() -> None:
    payload, _ = build_create_request(
        _body(gpus='"device=gpu0,capabilities=gpu,compute"')
    )

    request = _host(payload)["DeviceRequests"][0]
    assert request["DeviceIDs"] == ["gpu0"]
    assert request["Capabilities"] == [["gpu", "compute"]]


@pytest.mark.parametrize(
    "field",
    [
        "cidfile",
        "env_files",
        "label_files",
        "env_host",
        "pod",
        "pull",
        "systemd",
        "tz",
    ],
)
def test_create_payload_rejects_unsupported_fields(field: str) -> None:
    values: dict[str, object] = {
        "env_host": True,
        "label_files": ["labels.txt"],
        "env_files": ["env.txt"],
        "systemd": "always",
    }
    with pytest.raises(RuntimePreflightError, match=field):
        build_create_request(_body(**{field: values.get(field, "value")}))
