from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from backend.docker_config import DockerConfig

module_path = "backend.docker_config"


@pytest.mark.parametrize(
    "file_exists, expected_auths",
    [
        (False, {}),
        (
            True,
            {
                "https://index.docker.io/v1/": {
                    "auth": "base64_encoded_auth"
                }
            },
        ),
    ],
)
def test_docker_config(
    mocker: MockerFixture,
    file_exists,
    expected_auths,
):
    # reset singleton
    DockerConfig._instance = None

    mocker.patch("pathlib.Path.exists", return_value=file_exists)

    if file_exists:
        mocker.patch(
            "builtins.open",
            mocker.mock_open(
                read_data='{"auths": {"https://index.docker.io/v1/": {"auth": "base64_encoded_auth"}}}'
            ),
        )
    else:
        mocker.patch("builtins.open", side_effect=FileNotFoundError)

    docker_config = DockerConfig("/path/to/docker")

    assert docker_config.path == Path("/path/to/docker/config.json")
    assert docker_config.auths == expected_auths


@pytest.mark.parametrize(
    "auths, registry, expected",
    [
        # exact match
        (
            {"my.registry.com": {"auth": "token1"}},
            "my.registry.com",
            "token1",
        ),
        # dockerhub special case (registry-1)
        (
            {
                "https://index.docker.io/v1/": {
                    "auth": "dockerhub_token"
                }
            },
            "registry-1.docker.io",
            "dockerhub_token",
        ),
        # dockerhub special case (docker.io)
        (
            {
                "https://index.docker.io/v1/": {
                    "auth": "dockerhub_token"
                }
            },
            "docker.io",
            "dockerhub_token",
        ),
        # partial match: registry in key
        (
            {"https://gcr.io/project": {"auth": "gcr_token"}},
            "gcr.io",
            "gcr_token",
        ),
        # partial match: key in registry
        (
            {"gcr.io": {"auth": "gcr_token"}},
            "gcr.io/project",
            "gcr_token",
        ),
        # no match
        (
            {"another.registry.com": {"auth": "token"}},
            "unknown.registry.com",
            None,
        ),
        # entry exists but no "auth"
        (
            {"my.registry.com": {"username": "user"}},
            "my.registry.com",
            None,
        ),
        # empty auths
        (
            {},
            "docker.io",
            None,
        ),
    ],
)
def test_get_basic_token(auths, registry, expected):
    # reset singleton
    DockerConfig._instance = None

    docker_config = DockerConfig()

    # напрямую подменяем auths
    docker_config.auths = auths

    result = docker_config.get_basic_token(registry)

    assert result == expected
