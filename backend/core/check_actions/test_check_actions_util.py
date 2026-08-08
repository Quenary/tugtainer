from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.check_actions.check_actions_util import (
    filter_containers_by_check_enabled,
    get_image_remote_digest,
    parse_image_spec,
    sort_containers_by_checked_at,
)

module_path = "backend.core.check_actions.check_actions_util"


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
        (
            "docker.io/p3terx/aria2-pro:latest",
            "registry-1.docker.io",
            "p3terx/aria2-pro",
            "latest",
        ),
        (
            "index.docker.io/library/nginx:latest",
            "registry-1.docker.io",
            "library/nginx",
            "latest",
        ),
        (
            "docker.io/nginx:latest",
            "registry-1.docker.io",
            "library/nginx",
            "latest",
        ),
        (
            "nginx",
            "registry-1.docker.io",
            "library/nginx",
            "latest",
        ),
        (
            "nginx:1.27",
            "registry-1.docker.io",
            "library/nginx",
            "1.27",
        ),
        (
            "p3terx/aria2-pro:latest",
            "registry-1.docker.io",
            "p3terx/aria2-pro",
            "latest",
        ),
    ],
)
def test_parse_image_spec(spec, expected_registry, expected_repo, expected_tag):
    registry, repo, tag = parse_image_spec(spec)
    assert registry == expected_registry
    assert repo == expected_repo
    assert tag == expected_tag


def test_filter_containers_by_check_enabled_keeps_only_enabled():
    containers = [
        SimpleNamespace(name="enabled"),
        SimpleNamespace(name="disabled"),
        SimpleNamespace(name="missing"),
    ]
    db_map = {
        "enabled": SimpleNamespace(check_enabled=True),
        "disabled": SimpleNamespace(check_enabled=False),
    }

    filtered = filter_containers_by_check_enabled(containers, db_map)

    assert [c.name for c in filtered] == ["enabled"]


def test_sort_containers_by_checked_at_orders_earliest_first():
    containers = [
        SimpleNamespace(name="never"),
        SimpleNamespace(name="recent"),
        SimpleNamespace(name="old"),
    ]
    db_map = {
        "recent": SimpleNamespace(checked_at=datetime(2026, 8, 8, tzinfo=UTC)),
        "old": SimpleNamespace(checked_at=datetime(2026, 1, 1, tzinfo=UTC)),
        "never": SimpleNamespace(checked_at=None),
    }

    sorted_containers = sort_containers_by_checked_at(containers, db_map)

    assert [c.name for c in sorted_containers] == [
        "never",
        "old",
        "recent",
    ]


def _mock_head_response(
    status: int,
    headers: dict | None = None,
):
    resp = MagicMock()
    resp.status = status
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.mark.asyncio
async def test_get_image_remote_digest_uses_registry_1_for_docker_io(
    mocker: MockerFixture,
):
    digest = "sha256:abc123"
    head_resp = _mock_head_response(200, {"Docker-Content-Digest": digest})

    session = MagicMock()
    session.head = MagicMock(return_value=head_resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value=None)
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    result = await get_image_remote_digest("docker.io/p3terx/aria2-pro:latest")

    assert result == digest
    session.head.assert_called()
    url = session.head.call_args.args[0]
    assert url == ("https://registry-1.docker.io/v2/p3terx/aria2-pro/manifests/latest")


@pytest.mark.asyncio
async def test_get_image_remote_digest_bearer_auth_flow(
    mocker: MockerFixture,
):
    digest = "sha256:def456"
    unauthorized = _mock_head_response(
        401,
        {
            "WWW-Authenticate": (
                'Bearer realm="https://auth.docker.io/token",'
                'service="registry.docker.io",'
                'scope="repository:library/nginx:pull"'
            )
        },
    )
    authorized = _mock_head_response(200, {"Docker-Content-Digest": digest})
    token_resp = MagicMock()
    token_resp.raise_for_status = MagicMock()
    token_resp.json = AsyncMock(return_value={"token": "tok"})
    token_resp.__aenter__ = AsyncMock(return_value=token_resp)
    token_resp.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.head = MagicMock(side_effect=[unauthorized, authorized])
    session.get = MagicMock(return_value=token_resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value=None)
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    result = await get_image_remote_digest("nginx:latest")

    assert result == digest
    assert session.head.call_count == 2
    auth_header = session.head.call_args_list[1].kwargs["headers"]["Authorization"]
    assert auth_header == "Bearer tok"


@pytest.mark.asyncio
async def test_get_image_remote_digest_returns_local_on_304(
    mocker: MockerFixture,
):
    local_digest = (
        "nginx@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    )
    not_modified = _mock_head_response(304)

    session = MagicMock()
    session.head = MagicMock(return_value=not_modified)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value=None)
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    result = await get_image_remote_digest("nginx:latest", local_digest)

    assert result == local_digest.split("@")[-1]
    headers = session.head.call_args.kwargs["headers"]
    assert headers["If-None-Match"] == local_digest.split("@")[-1]
