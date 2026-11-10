import re
from pathlib import Path
from typing import Final

# Docker / Podman bind mounts these files from the container's directory,
# e.g. /var/lib/docker/containers/<id>/hostname or /overlay-containers/<id>/userdata/hosts
_CONTAINER_FILES_RE: Final = re.compile(
    r"(?:containers|overlay-containers)/([0-9a-f]{64})/(?:userdata/)?(?:hostname|hosts|resolv\.conf)\s"
)
_CONTAINERENV_ID_RE: Final = re.compile(r'(?:container_)?id="?([0-9a-f]{64})"?')
_CGROUP_ID_RE: Final = re.compile(r"([0-9a-f]{64})")


def get_self_container_id(
    mountinfo_path: Path = Path("/proc/self/mountinfo"),
    containerenv_path: Path = Path("/run/.containerenv"),
    cgroup_path: Path = Path("/proc/self/cgroup"),
) -> str | None:
    """
    Get the full id of the container this process runs in.
    HOSTNAME is not reliable (custom hostname, host networking),
    so the id is taken from mounts, .containerenv, or cgroups.
    The result must be verified with inspect.
    """
    try:
        content = mountinfo_path.read_text()
        match = _CONTAINER_FILES_RE.search(content)
        if match:
            return match.group(1)
    except OSError:
        pass

    try:
        env_content = containerenv_path.read_text()
        env_match = _CONTAINERENV_ID_RE.search(env_content)
        if env_match:
            return env_match.group(1)
    except OSError:
        pass

    try:
        cg_content = cgroup_path.read_text()
        for line in cg_content.splitlines():
            cg_match = _CGROUP_ID_RE.search(line)
            if cg_match:
                return cg_match.group(1)
    except OSError:
        pass

    return None
