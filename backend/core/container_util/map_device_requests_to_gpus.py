from typing import Final

from python_on_whales.components.container.models import (
    ContainerDeviceRequest,
)


def map_device_requests_to_gpus(
    device_requests: list[ContainerDeviceRequest] | None,
) -> str | None:
    """Map docker inspect device requests strictly to nvidia --gpus param"""
    if not device_requests:
        return None

    # Docker CLI --gpus flag only supports nvidia driver stack for now.
    # CDI devices, even if they represent a GPU, cannot be used with --gpus.
    gpu_req: ContainerDeviceRequest | None = next(
        (dr for dr in device_requests if dr.driver and dr.driver.lower() == "nvidia"),
        None,
    )

    if not gpu_req:
        return None

    parts: Final[list[str]] = []

    # Device / count
    if gpu_req.device_ids:
        parts.append(f"device={','.join(gpu_req.device_ids)}")
    elif gpu_req.count is not None and gpu_req.count > 0:
        parts.append(f"count={gpu_req.count}")
    else:
        parts.append("device=all")

    # Capabilities
    if gpu_req.capabilities:
        caps: Final[list[str]] = []
        # Docker API supports capability groups ([][]str),
        # but --gpus accepts only a flat capabilities list.
        # Flatten all groups during conversion.
        for cap_group in gpu_req.capabilities:
            if isinstance(cap_group, list):
                caps.extend(cap_group)
            elif isinstance(cap_group, str):
                caps.append(cap_group)

        unique_caps: Final[list[str]] = list(
            dict.fromkeys(c.lower() for c in caps if isinstance(c, str) and c)
        )

        if unique_caps:
            parts.append(f"capabilities={','.join(unique_caps)}")

    # Options
    if gpu_req.options:
        opts: Final[list[str]] = [f"{k}={v}" for k, v in gpu_req.options.items()]
        parts.append(f"options={','.join(opts)}")

    res = ",".join(parts)

    # Optimized generic request without custom caps and options
    if res in "device=all,capabilities=gpu":
        return "all"

    return f'"{res}"'
