from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from backend.docker_config import DockerConfig, normalize_registry_host

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
        # URL-form key with path (host only)
        (
            {"https://gcr.io/project": {"auth": "gcr_token"}},
            "gcr.io",
            "gcr_token",
        ),
        # path on registry argument is stripped to host
        (
            {"gcr.io": {"auth": "gcr_token"}},
            "gcr.io/project",
            "gcr_token",
        ),
        # https://ghcr.io/v1/ → ghcr.io
        (
            {"https://ghcr.io/v1/": {"auth": "ghcr_token"}},
            "ghcr.io",
            "ghcr_token",
        ),
        # case-insensitive host match
        (
            {"https://GHCR.IO": {"auth": "ghcr_token"}},
            "ghcr.io",
            "ghcr_token",
        ),
        # substring lookalike must not match (SA)
        (
            {"ghcr.io": {"auth": "ghcr_token"}},
            "ghcr.io.attacker.example",
            None,
        ),
        (
            {"https://ghcr.io": {"auth": "ghcr_token"}},
            "ghcr.io.attacker.example",
            None,
        ),
        (
            {"ghcr.io.attacker.example": {"auth": "evil_token"}},
            "ghcr.io",
            None,
        ),
        # suffix lookalike must not match
        (
            {"gcr.io": {"auth": "gcr_token"}},
            "mygcr.io",
            None,
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


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ghcr.io", "ghcr.io"),
        ("https://ghcr.io", "ghcr.io"),
        ("https://ghcr.io/v1/", "ghcr.io"),
        ("https://gcr.io/project", "gcr.io"),
        ("GHCR.IO", "ghcr.io"),
        ("localhost:5000", "localhost:5000"),
        ("http://localhost:5000", "localhost:5000"),
        ("https://index.docker.io/v1/", "registry-1.docker.io"),
        ("docker.io", "registry-1.docker.io"),
        ("registry-1.docker.io", "registry-1.docker.io"),
        ("ghcr.io.attacker.example", "ghcr.io.attacker.example"),
        ("", ""),
    ],
)
def test_normalize_registry_host(value, expected):
    assert normalize_registry_host(value) == expected
