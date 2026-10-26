from pathlib import Path

import pytest

from backend.util.get_self_container_id import get_self_container_id

ID = "a" * 54 + "0123456789"


@pytest.mark.parametrize(
    "line",
    [
        f"612 590 8:32 /var/lib/docker/containers/{ID}/hostname /etc/hostname rw,relatime - ext4 /dev/sdc rw",
        f"612 590 8:32 /docker/containers/{ID}/resolv.conf /etc/resolv.conf rw - ext4 /dev/sdc rw",
        f"612 590 0:52 /containers/storage/overlay-containers/{ID}/userdata/hosts /etc/hosts rw - tmpfs tmpfs rw",
    ],
)
def test_finds_id_in_mountinfo(tmp_path: Path, line: str) -> None:
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        "590 1 0:44 / / rw,relatime - overlay overlay rw\n" + line + "\n"
    )

    assert get_self_container_id(mountinfo) == ID


def test_ignores_other_container_paths(tmp_path: Path) -> None:
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        f"612 590 8:32 /var/lib/docker/containers/{ID}/mounts/shm /dev/shm rw - ext4 /dev/sdc rw\n"
    )

    assert get_self_container_id(mountinfo) is None


def test_returns_none_outside_container(tmp_path: Path) -> None:
    assert get_self_container_id(tmp_path / "missing") is None
