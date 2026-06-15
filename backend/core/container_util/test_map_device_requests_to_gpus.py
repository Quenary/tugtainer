import pytest
from python_on_whales.components.container.models import (
    ContainerDeviceRequest,
)

from backend.core.container_util.map_device_requests_to_gpus import (
    map_device_requests_to_gpus,
)


@pytest.mark.parametrize(
    "device_requests, expected_result",
    [
        # Empty inputs
        (None, None),
        ([], None),
        # Not valid inputs
        (
            [ContainerDeviceRequest(driver="cdi", count=-1, capabilities=[["gpu"]])],
            None,
        ),
        (
            [
                ContainerDeviceRequest(
                    driver="cdi",
                    device_ids=["vendor.com/gpu=all"],
                    capabilities=[["vendor.com/gpu=all"]],
                )
            ],
            None,
        ),
        # Nvidia cases
        ([ContainerDeviceRequest(driver="nvidia", count=-1)], "all"),
        (
            [ContainerDeviceRequest(driver="nvidia", device_ids=["0", "1"])],
            "driver=nvidia,device=0,1",
        ),
        (
            [
                ContainerDeviceRequest(
                    driver="nvidia", count=2, capabilities=[["compute", "utility"]]
                )
            ],
            "driver=nvidia,count=2,capabilities=compute,utility",
        ),
        (
            [
                ContainerDeviceRequest(
                    driver="nvidia",
                    count=-1,
                    capabilities=[
                        ["compute"],
                        ["video", "compute"],
                    ],  # Nested and duplicated
                    options={"foo": "bar"},
                )
            ],
            "driver=nvidia,device=all,capabilities=compute,video,options=foo=bar",
        ),
    ],
)
def test_map_device_requests_to_gpus(
    device_requests: list[ContainerDeviceRequest] | None,
    expected_result: str | None,
):
    assert map_device_requests_to_gpus(device_requests) == expected_result
