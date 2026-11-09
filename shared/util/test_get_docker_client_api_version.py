from packaging.version import Version

from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.util.get_docker_client_api_version import get_docker_client_api_version


def test_returns_none_without_version() -> None:
    assert get_docker_client_api_version(None) is None
    assert get_docker_client_api_version(DockerVersionScheme()) is None


def test_prefers_negotiated_api() -> None:
    version = DockerVersionScheme(api_version="1.41", negotiated_api="1.48")

    assert get_docker_client_api_version(version) == Version("1.48")


def test_falls_back_to_api_version() -> None:
    version = DockerVersionScheme(api_version="1.44")

    assert get_docker_client_api_version(version) == Version("1.44")


def test_returns_none_for_invalid_version() -> None:
    version = DockerVersionScheme(api_version="not-a-version")

    assert get_docker_client_api_version(version) is None
