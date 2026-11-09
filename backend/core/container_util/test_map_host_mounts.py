import pytest

from backend.core.container_util.map_mounts_to_arg import map_host_mounts
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import Mount
from shared.schemas.container_schemas import CreateMount


def test_bind_string_keeps_selinux_and_propagation():
    binds, mounts = map_host_mounts(
        None,
        ["/srv/app:/config:ro,Z,rslave", "/data:/data:z"],
        [
            Mount(
                type="bind",
                source="/srv/app",
                destination="/config",
                mode="Z",
                rw=False,
            )
        ],
    )

    assert binds == ["/srv/app:/config:ro,Z,rslave", "/data:/data:z"]
    assert mounts == []


def test_host_mount_beats_duplicate_bind_and_runtime_mount():
    binds, mounts = map_host_mounts(
        [
            Mount(
                type="bind",
                target="/config",
                source="/srv/app",
                read_only=True,
                consistency="cached",
                bind_options={
                    "Propagation": "rprivate",
                    "NonRecursive": True,
                    "CreateMountpoint": True,
                },
            )
        ],
        ["/srv/app:/config:ro"],
        [Mount(type="bind", source="/other", destination="/config")],
    )

    assert binds == []
    assert mounts == [
        CreateMount(
            type="bind",
            target="/config",
            source="/srv/app",
            read_only=True,
            consistency="cached",
            bind_options={
                "Propagation": "rprivate",
                "NonRecursive": True,
                "CreateMountpoint": True,
            },
        )
    ]


def test_anonymous_volume_name_comes_from_runtime_mount():
    _binds, mounts = map_host_mounts(
        [Mount(type="volume", target="/var/lib/app", source="")],
        None,
        [
            Mount(
                type="volume",
                name="anon-volume",
                source="/var/lib/docker/volumes/anon-volume/_data",
                destination="/var/lib/app",
            )
        ],
    )

    assert mounts[0].source == "anon-volume"
    assert mounts[0].target == "/var/lib/app"


def test_runtime_mount_missing_from_host_config_is_kept():
    _binds, mounts = map_host_mounts(
        None,
        None,
        [
            Mount(
                type="volume",
                name="app-data",
                destination="/data",
                driver="rexray",
                volume_options={
                    "NoCopy": True,
                    "Labels": {"backup": "daily"},
                    "DriverConfig": {"Name": "rexray", "Options": {"size": "10"}},
                    "Subpath": "pg",
                },
            )
        ],
    )

    assert mounts == [
        CreateMount(
            type="volume",
            target="/data",
            source="app-data",
            volume_options={
                "NoCopy": True,
                "Labels": {"backup": "daily"},
                "DriverConfig": {"Name": "rexray", "Options": {"size": "10"}},
                "Subpath": "pg",
            },
        )
    ]


def test_tmpfs_and_image_options_are_copied():
    _binds, mounts = map_host_mounts(
        [
            Mount(
                type="tmpfs",
                target="/run",
                tmpfs_options={"SizeBytes": 1024, "Mode": 0o755, "Options": ["noexec"]},
            ),
            Mount(
                type="image",
                target="/opt",
                source="app:1",
                image_options={"Subpath": "bin"},
            ),
        ],
        None,
        None,
    )

    assert mounts[0].tmpfs_options == {
        "SizeBytes": 1024,
        "Mode": 0o755,
        "Options": ["noexec"],
    }
    assert mounts[1].image_options == {"Subpath": "bin"}
    assert mounts[1].source == "app:1"


def test_selinux_on_a_mount_without_a_bind_fails():
    with pytest.raises(RuntimePreflightError, match="SELinux"):
        map_host_mounts(
            None,
            None,
            [Mount(type="bind", source="/src", destination="/dst", mode="z")],
        )


def test_unparseable_bind_fails():
    with pytest.raises(RuntimePreflightError, match="Cannot represent bind"):
        map_host_mounts(None, ["not-a-bind"], None)
