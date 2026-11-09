from packaging import version
from packaging.version import Version

from shared.schemas.docker_version_scheme import DockerVersionScheme


def get_docker_client_api_version(
    docker_version: DockerVersionScheme | None,
) -> Version | None:
    if not docker_version:
        return None
    api_str = docker_version.negotiated_api or docker_version.api_version
    if not api_str:
        return None
    try:
        return version.parse(api_str)
    except version.InvalidVersion:
        return None
