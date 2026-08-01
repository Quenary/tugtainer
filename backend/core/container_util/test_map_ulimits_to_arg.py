import pytest
from python_on_whales.components.container.models import (
    ContainerUlimit,
)

from backend.core.container_util.map_ulimits_to_arg import (
    map_ulimits_to_arg,
)


@pytest.mark.parametrize(
    "ulimits, expected_result",
    [
        # Empty inputs
        (None, []),
        ([], []),
        # Docker-style names are kept as-is
        (
            [ContainerUlimit(name="nofile", soft=65536, hard=65536)],
            ["nofile=65536:65536"],
        ),
        # Podman-style names are normalized to the short form
        (
            [ContainerUlimit(name="RLIMIT_NOFILE", soft=65536, hard=65536)],
            ["nofile=65536:65536"],
        ),
        (
            [ContainerUlimit(name="RLIMIT_NPROC", soft=None, hard=4096)],
            ["nproc=0:4096"],
        ),
    ],
)
def test_map_ulimits_to_arg(
    ulimits: list[ContainerUlimit] | None,
    expected_result: list[str],
):
    assert map_ulimits_to_arg(ulimits) == expected_result
