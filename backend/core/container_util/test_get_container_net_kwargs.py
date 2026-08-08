from python_on_whales.components.container.models import (
    ContainerEndpointIPAMConfig,
    ContainerHostConfig,
    ContainerInspectResult,
    NetworkInspectResult,
    NetworkSettings,
)

from backend.core.container_util.get_container_net_kwargs import (
    get_container_net_kwargs,
)


def _container(
    networks: dict[str, NetworkInspectResult],
    network_mode: str | None = None,
    links: list[str] | None = None,
) -> ContainerInspectResult:
    return ContainerInspectResult(
        name="app",
        host_config=ContainerHostConfig(network_mode=network_mode, links=links),
        network_settings=NetworkSettings(networks=networks),
    )


# Docker lists attachments sorted by name, so the alphabetically first one
# is not necessarily the primary network of the container.
def test_primary_network_taken_from_network_mode():
    container = _container(
        networks={
            "a_secondary": NetworkInspectResult(aliases=["alt"]),
            "z_primary": NetworkInspectResult(aliases=["main"]),
        },
        network_mode="z_primary",
    )

    kwargs, commands = get_container_net_kwargs(container, None)

    assert kwargs["networks"] == ["z_primary"]
    assert kwargs["network_aliases"] == ["main"]
    assert commands == [["network", "connect", "--alias", "alt", "a_secondary", "app"]]


def test_primary_network_falls_back_to_first_when_mode_not_attached():
    container = _container(
        networks={
            "bridge": NetworkInspectResult(aliases=["only"]),
        },
        network_mode="default",
    )

    kwargs, commands = get_container_net_kwargs(container, None)

    assert kwargs["networks"] == ["bridge"]
    assert commands == []


def test_primary_network_static_ip_follows_network_mode():
    container = _container(
        networks={
            "a_secondary": NetworkInspectResult(
                ipam_config=ContainerEndpointIPAMConfig(ipv4_address="172.31.1.5"),
            ),
            "z_primary": NetworkInspectResult(
                ipam_config=ContainerEndpointIPAMConfig(ipv4_address="172.31.0.5"),
            ),
        },
        network_mode="z_primary",
    )

    kwargs, commands = get_container_net_kwargs(container, None)

    assert kwargs["ip"] == "172.31.0.5"
    assert commands == [
        [
            "network",
            "connect",
            "--ip",
            "172.31.1.5",
            "a_secondary",
            "app",
        ]
    ]


# Links of user-defined networks are stored per endpoint,
# HostConfig.Links stays empty there.
def test_primary_endpoint_links_are_preserved():
    container = _container(
        networks={"mynet": NetworkInspectResult(links=["db:database"])},
        network_mode="mynet",
    )

    kwargs, _ = get_container_net_kwargs(container, None)

    assert kwargs["link"] == ["db:database"]


def test_secondary_endpoint_links_are_preserved_as_connect_args():
    container = _container(
        networks={
            "primary": NetworkInspectResult(),
            "secondary": NetworkInspectResult(
                aliases=["svc"], links=["db:database", "cache:redis"]
            ),
        },
        network_mode="primary",
    )

    _, commands = get_container_net_kwargs(container, None)

    assert commands == [
        [
            "network",
            "connect",
            "--alias",
            "svc",
            "--link",
            "db:database",
            "--link",
            "cache:redis",
            "secondary",
            "app",
        ]
    ]


def test_legacy_host_config_links_still_used_without_endpoint_links():
    container = _container(
        networks={"bridge": NetworkInspectResult()},
        network_mode="bridge",
        links=["/db:/app/database"],
    )

    kwargs, _ = get_container_net_kwargs(container, None)

    assert kwargs["link"] == ["/db:/app/database"]
