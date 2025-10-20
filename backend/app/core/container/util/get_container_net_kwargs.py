from python_on_whales.components.container.cli_wrapper import (
    Container,
)
from typing import Any
from python_on_whales.utils import ValidPortMapping
from .map_port_bindings_to_list import map_port_bindings_to_list


def get_container_net_kwargs(
    container: Container,
) -> tuple[dict[Any, Any], list[list[str]]]:
    """
    Get container networking params dict that matches kwargs for create/run.
    :returns 0: dict of params
    :returns 1: list of docker commands to be executed after container creation, in list format e.g. ["network", "connect", ...]
    """
    COMMANDS: list[list[str]] = []
    ID = container.id
    CONFIG = container.config
    HOST_CONFIG = container.host_config
    NETWORK_SETTINGS = container.network_settings

    DNS: list[str] = HOST_CONFIG.dns or []
    DNS_OPTIONS: list[str] = HOST_CONFIG.dns_options or []
    DNS_SEARCH: list[str] = HOST_CONFIG.dns_search or []
    HOSTNAME: str | None = CONFIG.hostname
    IP: str | None = None
    IP6: str | None = None
    LINK: list[str] = HOST_CONFIG.links or []
    NETWORKS: list[str] = []
    NETWORK_ALIASES: list[str] = []
    PUBLISH: list[ValidPortMapping] = map_port_bindings_to_list(
        HOST_CONFIG.port_bindings
    )
    PUBLISH_ALL: bool = bool(HOST_CONFIG.publish_all_ports)

    # Possible values: bridge | none | container:<id> | user-defined | host
    NETWORK_MODE = HOST_CONFIG.network_mode

    if NETWORK_SETTINGS.networks:
        NETWORKS_KEYS = list(NETWORK_SETTINGS.networks.keys())
        MAIN_NETWORK = NETWORK_SETTINGS.networks[NETWORKS_KEYS[0]]
        NETWORKS = [NETWORKS_KEYS[0]]
        NETWORK_ALIASES = MAIN_NETWORK.aliases or []
        for net in NETWORKS_KEYS[1:]:
            # Additional networks returned as commands
            # as docker cli doesn't support multiple aliases for multiple networks inline (in create/run)
            _cmd = ["network", "connect"]
            aliases = NETWORK_SETTINGS.networks[net].aliases or []
            for a in aliases:
                _cmd += ["--alias", a]
            _cmd += [net, container.name]
            COMMANDS.append(_cmd)
    elif NETWORK_MODE:
        NETWORKS = [NETWORK_MODE]

    # Do not preserve generated hostname
    if HOSTNAME and HOSTNAME in ID:
        HOSTNAME = None

    # Remove unsupported values
    if NETWORK_MODE and (
        NETWORK_MODE in ["host", "none"]
        or NETWORK_MODE.startswith("container:")
    ):
        DNS = []
        DNS_OPTIONS = []
        DNS_SEARCH = []
        HOSTNAME = None
        IP = None
        IP6 = None
        LINK = []
        NETWORK_ALIASES = []
        PUBLISH = []
        PUBLISH_ALL = False

    return {
        "dns": DNS,
        "dns_options": DNS_OPTIONS,
        "dns_search": DNS_SEARCH,
        "hostname": HOSTNAME,
        "ip": IP,
        "ip6": IP6,
        "link": LINK,
        "networks": NETWORKS,
        "network_aliases": NETWORK_ALIASES,
        "publish": PUBLISH,
        "publish_all": PUBLISH_ALL,
    }, COMMANDS
