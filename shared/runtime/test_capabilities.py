import pytest

from shared.runtime.capabilities import RuntimeCapabilities
from shared.runtime.container_create_payload import build_create_request
from shared.runtime.endpoint_settings import build_endpoint_settings
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import RuntimeVersion
from shared.schemas.container_schemas import CreateContainerRequestBodySchema


def _podman(compat: str, engine: str) -> RuntimeCapabilities:
    return RuntimeCapabilities.from_version(
        RuntimeVersion(
            runtime_type="podman",
            api_version=compat,
            version=engine,
            libpod_api_version=engine,
        )
    )


PODMAN_57 = _podman("1.41", "5.7.0")
PODMAN_6 = _podman("1.44", "6.0.0")
PODMAN_49 = _podman("1.40", "4.9.3")


def test_docker_gw_priority_uses_negotiated_api() -> None:
    with pytest.raises(RuntimePreflightError, match="Docker API >= 1.48"):
        build_endpoint_settings(gateway_priority=1, api_version="1.47")

    endpoint = build_endpoint_settings(gateway_priority=1, api_version="1.48")
    assert endpoint["GwPriority"] == 1


@pytest.mark.parametrize("caps", [PODMAN_57, PODMAN_6])
def test_podman_rejects_gw_priority_without_a_docker_gate(
    caps: RuntimeCapabilities,
) -> None:
    with pytest.raises(RuntimePreflightError, match="not supported on Podman") as exc:
        build_endpoint_settings(gateway_priority=1, capabilities=caps)
    assert "Docker API" not in str(exc.value)


@pytest.mark.parametrize("caps", [PODMAN_57, PODMAN_6])
def test_podman_keeps_mac(caps: RuntimeCapabilities) -> None:
    endpoint = build_endpoint_settings(
        ipv4_address="172.20.0.8",
        mac_address="02:42:ac:14:00:08",
        capabilities=caps,
    )
    assert endpoint["MacAddress"] == "02:42:ac:14:00:08"


def test_old_podman_mac_fails_closed() -> None:
    with pytest.raises(RuntimePreflightError, match="Podman 5.0") as exc:
        build_endpoint_settings(
            mac_address="02:42:ac:14:00:08",
            capabilities=PODMAN_49,
        )
    assert "Docker API" not in str(exc.value)


def test_podman_rejects_image_mount_and_subpath() -> None:
    body = CreateContainerRequestBodySchema.model_validate(
        {
            "image": "app",
            "mounts": [
                {
                    "type": "image",
                    "target": "/opt",
                    "source": "app:1",
                }
            ],
        }
    )
    with pytest.raises(RuntimePreflightError, match="Image mounts") as exc:
        build_create_request(body, capabilities=PODMAN_6)
    assert "Docker API" not in str(exc.value)


@pytest.mark.parametrize("caps", [PODMAN_57, PODMAN_6])
def test_podman_allows_older_bind_flags(caps: RuntimeCapabilities) -> None:
    body = CreateContainerRequestBodySchema.model_validate(
        {
            "image": "app",
            "mounts": [
                {
                    "type": "bind",
                    "target": "/dst",
                    "source": "/src",
                    "bind_options": {
                        "NonRecursive": True,
                        "CreateMountpoint": True,
                    },
                }
            ],
        }
    )
    payload, _ = build_create_request(body, capabilities=caps)
    bind = payload["HostConfig"]["Mounts"][0]["BindOptions"]
    assert bind["NonRecursive"] is True
    assert bind["CreateMountpoint"] is True


def test_old_podman_rejects_nonrecursive_bind() -> None:
    body = CreateContainerRequestBodySchema.model_validate(
        {
            "image": "app",
            "mounts": [
                {
                    "type": "bind",
                    "target": "/dst",
                    "source": "/src",
                    "bind_options": {"NonRecursive": True},
                }
            ],
        }
    )
    old = _podman("1.40", "3.4.0")
    with pytest.raises(RuntimePreflightError, match="NonRecursive"):
        build_create_request(body, capabilities=old)
