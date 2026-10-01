import pytest
from python_on_whales.components.container.models import PortBinding

from backend.core.container_util.map_port_bindings_to_list import (
    map_port_bindings_to_list,
)


@pytest.mark.parametrize(
    ("bindings", "expected"),
    [
        (None, []),
        ({}, []),
        (
            {"8000/tcp": [PortBinding(host_ip="127.0.0.1", host_port="8000")]},
            [("127.0.0.1:8000", "8000", "tcp")],
        ),
        (
            {"443/tcp": [PortBinding(host_ip="::1", host_port="443")]},
            [("[::1]:443", "443", "tcp")],
        ),
        (
            {"53/udp": [PortBinding(host_port="53")]},
            [("53", "53", "udp")],
        ),
        (
            {"8000": [PortBinding(host_ip="10.0.0.1", host_port="80")]},
            [("10.0.0.1:80", "8000", "tcp")],
        ),
        (
            {
                "90/tcp": [PortBinding(host_ip="1.1.1.1", host_port="")],
                "91/tcp": None,
            },
            [],
        ),
    ],
)
def test_map_port_bindings_to_list(bindings, expected) -> None:
    assert map_port_bindings_to_list(bindings) == expected
