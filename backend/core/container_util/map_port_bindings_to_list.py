from shared.runtime.runtime_models import PortBinding
from shared.schemas.container_schemas import PortMapping


def map_port_bindings_to_list(
    bindings: dict[str, list[PortBinding] | None] | None,
) -> list[PortMapping]:
    """Map docker inspect PortBindings to list of PortMapping"""
    result: list[PortMapping] = []

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
                host_ip = entry.host_ip
                if host_ip:
                    # Preserve specific IP binding so the recreated
                    # container binds to the same address.
                    # IPv6 addresses must be wrapped in brackets
                    # (e.g. [::1]:443) per Docker -p syntax.
                    if ":" in host_ip:
                        host_str = f"[{host_ip}]:{host_port}"
                    else:
                        host_str = f"{host_ip}:{host_port}"
                    result.append((host_str, container_port, proto))
                else:
                    result.append((host_port, container_port, proto))
            else:
                continue

    return result
