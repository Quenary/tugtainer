import pytest

from backend.core.check_actions.check_actions_util import (
    parse_image_spec,
)


@pytest.mark.parametrize(
    "spec, expected_registry, expected_repo, expected_tag",
    [
        (
            "quenary/tugtainer:latest",
            "registry-1.docker.io",
            "quenary/tugtainer",
            "latest",
        ),
        (
            "ghcr.io/quenary/tugtainer:1",
            "ghcr.io",
            "quenary/tugtainer",
            "1",
        ),
        (
            "localhost:5000/myimage:dev",
            "localhost:5000",
            "myimage",
            "dev",
        ),
        (
            "library/alpine:3.14",
            "registry-1.docker.io",
            "library/alpine",
            "3.14",
        ),
    ],
)
def test_parse_image_spec(
    spec, expected_registry, expected_repo, expected_tag
):
    registry, repo, tag = parse_image_spec(spec)
    assert registry == expected_registry
    assert repo == expected_repo
    assert tag == expected_tag
