from typing import Any

from packaging import version

from shared.runtime.runtime_errors import RuntimePreflightError
from shared.schemas.network_schemas import NetworkConnectBodySchema

_GW_PRIORITY_API = "1.48"


def build_endpoint_settings(
    *,
    ipv4_address: str | None = None,
    ipv6_address: str | None = None,
    link_local_ips: list[str] | None = None,
    aliases: list[str] | None = None,
    links: list[str] | None = None,
    mac_address: str | None = None,
    driver_opts: dict[str, str] | None = None,
    gateway_priority: int | None = None,
    api_version: str | None = None,
) -> dict[str, Any]:
    """Engine EndpointSettings shared by create and network connect."""
    if gateway_priority is not None:
        _require_gw_priority(api_version)
    endpoint: dict[str, Any] = {}
    ipam: dict[str, Any] = {}
    _set(ipam, "IPv4Address", ipv4_address)
    _set(ipam, "IPv6Address", ipv6_address)
    _set(ipam, "LinkLocalIPs", link_local_ips)
    if ipam:
        endpoint["IPAMConfig"] = ipam
    _set(endpoint, "Aliases", aliases)
    _set(endpoint, "Links", links)
    _set(endpoint, "MacAddress", mac_address)
    _set(endpoint, "DriverOpts", driver_opts)
    _set(endpoint, "GwPriority", gateway_priority)
    return endpoint


def endpoint_config_from_connect(
    body: NetworkConnectBodySchema,
    api_version: str | None = None,
) -> dict[str, Any] | None:
    """EndpointConfig for POST /networks/{id}/connect."""
    endpoint = build_endpoint_settings(
        ipv4_address=body.ipv4_address,
        ipv6_address=body.ipv6_address,
        link_local_ips=body.link_local_ips,
        aliases=body.aliases,
        links=body.links,
        mac_address=body.mac_address,
        driver_opts=body.driver_opts,
        gateway_priority=body.gateway_priority,
        api_version=api_version,
    )
    return endpoint or None


def _require_gw_priority(api_version: str | None) -> None:
    parsed = None
    if api_version:
        text = api_version.removeprefix("/v").removeprefix("v")
        parsed = version.parse(text)
    if parsed is not None and parsed >= version.parse(_GW_PRIORITY_API):
        return
    got = str(parsed) if parsed is not None else "unknown"
    raise RuntimePreflightError(
        f"GwPriority requires Docker API >= {_GW_PRIORITY_API}, "
        f"but the target API is {got}"
    )


def _set(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, (list, dict)) and len(value) == 0:
        return
    target[key] = value
