from packaging import version
from packaging.version import Version

from shared.schemas.docker_version_scheme import DockerVersionScheme


def get_docker_client_api_version(
    docker_version: DockerVersionScheme | None,
) -> Version | None:
    try:
        return (
            version.parse(docker_version.client.api_version)
            if docker_version
            and docker_version.client
            and docker_version.client.api_version
            else None
        )
    except version.InvalidVersion:
        return None
