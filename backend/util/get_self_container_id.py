import re
from pathlib import Path
from typing import Final

# Docker bind mounts these files from the container's directory,
# e.g. /var/lib/docker/containers/<id>/hostname
_CONTAINER_FILES_RE: Final = re.compile(
    r"containers/([0-9a-f]{64})/(?:userdata/)?(?:hostname|hosts|resolv\.conf)\s"
)


def get_self_container_id(
    mountinfo_path: Path = Path("/proc/self/mountinfo"),
) -> str | None:
    """
    Get the full id of the container this process runs in.
    HOSTNAME is not reliable (custom hostname, host networking),
    so the id is taken from the mounts that the runtime creates.
    The result must be verified with inspect.
    """
    try:
        content = mountinfo_path.read_text()
    except OSError:
        return None
    match = _CONTAINER_FILES_RE.search(content)
    return match.group(1) if match else None
