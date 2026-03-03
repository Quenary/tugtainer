from typing import Union, List
from python_on_whales.components.container.models import (
    ContainerDeviceRequest,
)


def map_device_requests_to_gpus(
    device_requests: List[ContainerDeviceRequest] | None,
) -> Union[int, str, None]:
    """Map docker inspect device requests to gpus param"""
    if not device_requests:
        return None

    req = device_requests[0]
    if (
        req.driver != "nvidia"
        or "gpu" not in (req.capabilities or [[]])[0]
    ):
        return None

    if req.count == -1 or not req.device_ids:
        return "all"
    return "device=" + ",".join(req.device_ids)
