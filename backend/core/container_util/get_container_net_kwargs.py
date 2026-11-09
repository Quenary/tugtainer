from typing import Any, cast

from packaging import version

from shared.runtime.runtime_models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
    NetworkSettings,
)
from shared.schemas.container_schemas import PortMapping
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.network_schemas import NetworkConnectBodySchema
from shared.util.get_docker_client_api_version import (
    get_docker_client_api_version,
)

from .map_port_bindings_to_list import map_port_bindings_to_list


def get_container_net_kwargs(
    container: ContainerInspectResult,
    docker_version: DockerVersionScheme | None,
) -> tuple[dict[str, Any], list[NetworkConnectBodySchema]]:
    """
    Get container networking params dict that matches kwargs for create/run.
    :returns 0: dict of params
    :returns 1: list of secondary NetworkConnectBodySchema items to connect
    """
    SECONDARY_CONNECTS: list[NetworkConnectBodySchema] = []
    ID = container.id or ""
    CONFIG = container.config or ContainerConfig()
    HOST_CONFIG = container.host_config or ContainerHostConfig()
    NETWORK_SETTINGS = container.network_settings or NetworkSettings()
    docker_client_api_version = get_docker_client_api_version(docker_version)

    DNS: list[str] = HOST_CONFIG.dns or []
    DNS_OPTIONS: list[str] = HOST_CONFIG.dns_options or []
    DNS_SEARCH: list[str] = HOST_CONFIG.dns_search or []
    HOSTNAME: str | None = CONFIG.hostname
    IP: str | None = None
    IP6: str | None = None
    LINK: list[str] = HOST_CONFIG.links or []
    MAC_ADDRESS: str | None = None
    GATEWAY_PRIORITY: int | None = None
    NETWORKS: list[str] = []
    NETWORK_ALIASES: list[str] = []
    PUBLISH: list[PortMapping] = map_port_bindings_to_list(HOST_CONFIG.port_bindings)
    PUBLISH_ALL: bool = bool(HOST_CONFIG.publish_all_ports)

    # Possible values: bridge | none | container:<id> | user-defined | host
    NETWORK_MODE = HOST_CONFIG.network_mode

    if NETWORK_SETTINGS.networks:
        NETWORKS_KEYS = list(NETWORK_SETTINGS.networks.keys())
        # Docker lists attachments sorted by name, which is not necessarily
        # the network the container was created with. NetworkMode holds the
        # actual primary network, so prefer it while it is still attached.
        MAIN_KEY = (
            NETWORK_MODE
            if NETWORK_MODE in NETWORK_SETTINGS.networks
            else NETWORKS_KEYS[0]
        )
        MAIN_NETWORK = NETWORK_SETTINGS.networks[MAIN_KEY]
        NETWORKS = [MAIN_KEY]
        NETWORK_ALIASES = MAIN_NETWORK.aliases or []
        # On user-defined networks links live on the endpoint;
        # HostConfig.links is only populated for the legacy bridge.
        LINK = MAIN_NETWORK.links or LINK
        if MAIN_NETWORK.ipam_config:
            IP = MAIN_NETWORK.ipam_config.ipv4_address
            IP6 = MAIN_NETWORK.ipam_config.ipv6_address
            # preserve mac address if static ips used
            # https://github.com/Quenary/tugtainer/issues/126
            MAC_ADDRESS = MAIN_NETWORK.mac_address or CONFIG.mac_address
        GATEWAY_PRIORITY = MAIN_NETWORK.gateway_priority
        for net in NETWORKS_KEYS:
            if net == MAIN_KEY:
                continue
            net_obj = NETWORK_SETTINGS.networks[net]
            aliases = net_obj.aliases or []
            links = net_obj.links or []
            ipam = net_obj.ipam_config
            ipv4 = ipam.ipv4_address if ipam else None
            ipv6 = ipam.ipv6_address if ipam else None
            net_mac = net_obj.mac_address if ipam else None
            gw_prio = getattr(net_obj, "gateway_priority", None)
            SECONDARY_CONNECTS.append(
                NetworkConnectBodySchema(
                    network=net,
                    container=cast(str, container.name),
                    aliases=aliases or None,
                    links=links or None,
                    ipv4_address=ipv4,
                    ipv6_address=ipv6,
                    mac_address=net_mac,
                    gateway_priority=gw_prio,
                )
            )
    elif NETWORK_MODE:
        NETWORKS = [NETWORK_MODE]

    # Do not preserve generated hostname
    if HOSTNAME and HOSTNAME in ID:
        HOSTNAME = None

    # Remove unsupported values
    if NETWORK_MODE and (
        NETWORK_MODE in ["host", "none"] or NETWORK_MODE.startswith("container:")
    ):
        DNS = []
        DNS_OPTIONS = []
        DNS_SEARCH = []
        HOSTNAME = None
        IP = None
        IP6 = None
        MAC_ADDRESS = None
        LINK = []
        NETWORK_ALIASES = []
        PUBLISH = []
        PUBLISH_ALL = False

    if docker_client_api_version and docker_client_api_version < version.parse("1.44"):
        MAC_ADDRESS = None

    return {
        "dns": DNS,
        "dns_options": DNS_OPTIONS,
        "dns_search": DNS_SEARCH,
        "hostname": HOSTNAME,
        "ip": IP,
        "ip6": IP6,
        "link": LINK,
        "mac_address": MAC_ADDRESS,
        "gateway_priority": GATEWAY_PRIORITY,
        "networks": NETWORKS,
        "network_aliases": NETWORK_ALIASES,
        "publish": PUBLISH,
        "publish_all": PUBLISH_ALL,
    }, SECONDARY_CONNECTS
