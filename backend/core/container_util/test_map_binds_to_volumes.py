import pytest
from python_on_whales.components.container.models import Mount

from backend.core.container_util.map_binds_to_volumes import (
    map_binds_to_volumes,
)

# Mounts as docker inspect reports them
CONFIG = Mount(
    type="bind",
    source="/srv/app",
    destination="/config",
    mode="",
    rw=True,
    propagation="rprivate",
)
DATA = Mount(
    type="volume",
    name="app-data",
    source="/var/lib/docker/volumes/app-data/_data",
    destination="/data",
    driver="local",
    mode="z",
    rw=True,
    propagation="",
)
CACHE = Mount(
    type="bind",
    source="/srv/cache",
    destination="/cache",
    mode="",
    rw=True,
    propagation="rprivate",
)
ANONYMOUS = Mount(
    type="volume",
    name="0f1c2d3e4b5a",
    source="/var/lib/docker/volumes/0f1c2d3e4b5a/_data",
    destination="/var/lib/app",
    driver="local",
    mode="",
    rw=True,
    propagation="",
)


@pytest.mark.parametrize(
    "case_name, binds, mounts, expected_volumes, expected_mounts",
    [
        ("Should handle empty", None, None, [], []),
        (
            "Should keep bind as volume",
            ["/srv/app:/config"],
            [CONFIG],
            [("/srv/app", "/config")],
            [],
        ),
        (
            "Should keep bind options",
            ["/srv/app:/config:ro,rslave"],
            [CONFIG],
            [("/srv/app", "/config", "ro,rslave")],
            [],
        ),
        (
            "Should keep named volume as volume",
            ["app-data:/data"],
            [DATA],
            [("app-data", "/data")],
            [],
        ),
        (
            "Should keep mounts without binds as mounts",
            None,
            [CACHE, ANONYMOUS],
            [],
            [CACHE, ANONYMOUS],
        ),
        (
            "Should split binds from other mounts",
            ["/srv/app:/config", "app-data:/data"],
            [CONFIG, DATA, CACHE, ANONYMOUS],
            [("/srv/app", "/config"), ("app-data", "/data")],
            [CACHE, ANONYMOUS],
        ),
        (
            "Should match normalized destination",
            ["/srv/app:/config/"],
            [CONFIG],
            [("/srv/app", "/config/")],
            [],
        ),
        (
            "Should keep mount if bind has a Windows path",
            ["C:\\srv\\app:/config"],
            [CONFIG],
            [],
            [CONFIG],
        ),
        (
            "Should skip bind without inspect mount",
            ["/srv/app:/other"],
            [CONFIG],
            [],
            [CONFIG],
        ),
    ],
)
def test_map_binds_to_volumes(
    case_name, binds, mounts, expected_volumes, expected_mounts
):
    volumes, rest = map_binds_to_volumes(binds, mounts)

    assert volumes == expected_volumes, case_name
    assert rest == expected_mounts, case_name
