from packaging import version
from packaging.version import Version

from shared.schemas.docker_version_scheme import DockerVersionScheme


def get_docker_client_api_version(
    docker_version: DockerVersionScheme | None,
) -> Version | None:
    if not docker_version:
        return None
    api_str = getattr(docker_version, "negotiated_api", None) or getattr(
        docker_version, "api_version", None
    )
    if not api_str and hasattr(docker_version, "client") and docker_version.client:
        client_obj = docker_version.client
        api_str = (
            client_obj.get("ApiVersion")
            if isinstance(client_obj, dict)
            else getattr(client_obj, "api_version", None)
        )
    if not api_str:
        return None
    try:
        return version.parse(str(api_str))
    except version.InvalidVersion:
        return None
