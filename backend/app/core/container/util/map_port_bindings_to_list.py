from typing import Dict, List
from python_on_whales.components.container.models import PortBinding
from python_on_whales.utils import ValidPortMapping


def map_port_bindings_to_list(
    bindings: Dict[str, List[PortBinding] | None] | None,
) -> list[ValidPortMapping]:
    """Map docker inspect PortBindings to list of ValidPortMapping"""
    result: List[ValidPortMapping] = []

    if not bindings:
        return result

    for container_port_proto, entries in bindings.items():
        # container_port_proto: "8000/tcp"
        if not entries:
            continue
        if "/" in container_port_proto:
            container_port, proto = container_port_proto.split("/", 1)
        else:
            container_port, proto = container_port_proto, "tcp"
        for entry in entries:
            host_port = entry.host_port
            if host_port:
                result.append((host_port, container_port, proto))
            else:
                continue

    return result
