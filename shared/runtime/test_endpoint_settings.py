import pytest

from shared.runtime.endpoint_settings import (
    build_endpoint_settings,
    endpoint_config_from_connect,
)
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.schemas.network_schemas import NetworkConnectBodySchema


def _connect(**kwargs: object) -> NetworkConnectBodySchema:
    return NetworkConnectBodySchema.model_validate(
        {"network": "appnet", "container": "web", **kwargs}
    )


def test_endpoint_settings_use_gw_priority_key() -> None:
    endpoint = build_endpoint_settings(
        ipv4_address="172.20.0.8",
        ipv6_address="fd00::8",
        link_local_ips=["169.254.1.1"],
        aliases=["web"],
        links=["db"],
        mac_address="02:42:ac:14:00:08",
        driver_opts={"com.docker.network.endpoint.ifname": "eth0"},
        gateway_priority=5,
        api_version="1.48",
    )

    assert endpoint["GwPriority"] == 5
    assert "GatewayPriority" not in endpoint
    assert endpoint["DriverOpts"]["com.docker.network.endpoint.ifname"] == "eth0"
    assert endpoint["IPAMConfig"]["LinkLocalIPs"] == ["169.254.1.1"]


@pytest.mark.parametrize("api_version", [None, "1.47"])
def test_gw_priority_below_1_48_fails(api_version: str | None) -> None:
    with pytest.raises(RuntimePreflightError, match="GwPriority"):
        build_endpoint_settings(gateway_priority=1, api_version=api_version)


def test_connect_and_create_share_gw_priority_mapping() -> None:
    body = _connect(
        ipv4_address="172.20.0.9",
        aliases=["api"],
        mac_address="02:42:ac:14:00:09",
        driver_opts={"com.docker.network.endpoint.ifname": "eth1"},
        gateway_priority=3,
        link_local_ips=["169.254.1.2"],
    )
    connected = endpoint_config_from_connect(body, "1.48")
    created = build_endpoint_settings(
        ipv4_address=body.ipv4_address,
        aliases=body.aliases,
        mac_address=body.mac_address,
        driver_opts=body.driver_opts,
        gateway_priority=body.gateway_priority,
        link_local_ips=body.link_local_ips,
        api_version="1.48",
    )

    assert connected == created
    assert connected is not None
    assert connected["GwPriority"] == 3
