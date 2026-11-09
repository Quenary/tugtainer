from shared.runtime.runtime_models import (
    ContainerInspectResult,
    ImageInspectResult,
    RuntimeVersion,
)


def test_container_inspect_result_alias_and_name_cleaning():
    data = {
        "Id": "c1234567890abcdef",
        "Name": "/my-app",
        "Created": "2026-01-01T00:00:00Z",
        "State": {
            "Status": "running",
            "ExitCode": 0,
            "Health": {"Status": "healthy"},
        },
        "Config": {
            "Image": "nginx:alpine",
            "Labels": {"app": "test"},
            "Env": ["PORT=80"],
            "Healthcheck": {
                "Test": ["CMD-SHELL", "curl -f http://localhost/ || exit 1"],
                "Interval": 30000000000,
                "StartInterval": 5000000000,
            },
        },
        "HostConfig": {
            "Binds": ["/data:/data:ro"],
            "PortBindings": {
                "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}],
            },
        },
        "Mounts": [
            {
                "Type": "volume",
                "Name": "anon-volume-64-hex",
                "Destination": "/data",
                "Source": "/var/lib/docker/volumes/anon-volume-64-hex/_data",
            }
        ],
    }

    result = ContainerInspectResult.model_validate(data)
    assert result.id == "c1234567890abcdef"
    # Leading slash must be stripped
    assert result.name == "my-app"
    assert result.state is not None
    assert result.state.status == "running"
    assert result.state.exit_code == 0
    assert result.state.health is not None
    assert result.state.health.status == "healthy"

    assert result.config is not None
    assert result.config.image == "nginx:alpine"
    assert result.config.labels == {"app": "test"}
    assert result.config.healthcheck is not None
    assert result.config.healthcheck.test == [
        "CMD-SHELL",
        "curl -f http://localhost/ || exit 1",
    ]
    assert result.config.healthcheck.interval == 30000000000
    assert result.config.healthcheck.start_interval == 5000000000

    assert result.host_config is not None
    assert result.host_config.binds == ["/data:/data:ro"]
    assert result.host_config.port_bindings is not None
    bindings = result.host_config.port_bindings.get("80/tcp")
    assert bindings is not None
    assert len(bindings) == 1
    assert bindings[0].host_port == "8080"

    assert result.mounts is not None
    assert len(result.mounts) == 1
    assert result.mounts[0].name == "anon-volume-64-hex"
    assert result.mounts[0].destination == "/data"


def test_image_inspect_result_parsing():
    data = {
        "Id": "sha256:image123",
        "RepoTags": ["myrepo/app:1.0.0", "myrepo/app:latest"],
        "RepoDigests": ["myrepo/app@sha256:digest456"],
        "Size": 1024000,
        "Created": "2026-02-01T12:00:00Z",
        "Config": {
            "Labels": {"org.opencontainers.image.version": "1.0.0"},
            "Env": ["NODE_ENV=production"],
        },
    }

    img = ImageInspectResult.model_validate(data)
    assert img.id == "sha256:image123"
    assert img.repo_tags == ["myrepo/app:1.0.0", "myrepo/app:latest"]
    assert img.repo_digests == ["myrepo/app@sha256:digest456"]
    assert img.size == 1024000
    assert img.config is not None
    assert img.config.labels == {"org.opencontainers.image.version": "1.0.0"}


def test_runtime_version_parsing():
    data = {
        "Version": "28.0.1",
        "ApiVersion": "1.48",
        "MinAPIVersion": "1.24",
        "Components": [{"Name": "Engine", "Version": "28.0.1"}],
    }

    ver = RuntimeVersion.model_validate(data)
    assert ver.version == "28.0.1"
    assert ver.api_version == "1.48"
    assert ver.min_api_version == "1.24"
    assert ver.runtime_type == "docker"
