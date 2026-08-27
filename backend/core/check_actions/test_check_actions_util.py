from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.check_actions.check_actions_util import (
    filter_containers_by_check_enabled,
    get_image_remote_digest,
    get_registry_bearer_token,
    is_insecure_registry,
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
    assert session.get.call_args.kwargs["allow_redirects"] is False


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


@pytest.mark.parametrize(
    "registry, insecure_list, expected",
    [
        ("localhost:5000", "localhost:5000", True),
        ("localhost:5000", "http://localhost:5000", True),
        ("localhost", "localhost", True),
        ("LocalHost", "localhost", True),
        ("localhost.attacker.com", "localhost", False),
        ("localhost", "localhost.attacker.com", False),
        ("localhost:5000", "localhost", False),
        ("ghcr.io", "ghcr.io", True),
        ("ghcr.io.attacker.example", "ghcr.io", False),
        ("registry-1.docker.io", "docker.io", True),
        ("my.registry.com", None, False),
        ("my.registry.com", "", False),
        ("my.registry.com", "other.io\nmy.registry.com", True),
    ],
)
def test_is_insecure_registry(registry, insecure_list, expected):
    assert is_insecure_registry(registry, insecure_list) is expected


@pytest.mark.asyncio
async def test_get_image_remote_digest_does_not_treat_lookalike_as_insecure(
    mocker: MockerFixture,
):
    digest = "sha256:abc123"
    head_resp = _mock_head_response(200, {"Docker-Content-Digest": digest})

    session = MagicMock()
    session.head = MagicMock(return_value=head_resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value="localhost")
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    result = await get_image_remote_digest(
        "localhost.attacker.com/test/image:test"
    )

    assert result == digest
    assert session.head.call_args.args[0] == (
        "https://localhost.attacker.com/v2/test/image/manifests/test"
    )
    assert session.head.call_args.kwargs["ssl"] is True


@pytest.mark.asyncio
async def test_get_image_remote_digest_uses_http_ssl_for_exact_insecure_host(
    mocker: MockerFixture,
):
    digest = "sha256:abc123"
    head_resp = _mock_head_response(200, {"Docker-Content-Digest": digest})

    session = MagicMock()
    session.head = MagicMock(return_value=head_resp)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(
        f"{module_path}.SettingsStorage.get",
        return_value="localhost:5000",
    )
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    result = await get_image_remote_digest("localhost:5000/myimage:dev")

    assert result == digest
    assert session.head.call_args.kwargs["ssl"] is False
    assert session.head.call_args.args[0] == (
        "https://localhost:5000/v2/myimage/manifests/dev"
    )


def _mock_token_response(token: str = "tok"):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={"token": token})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.mark.asyncio
async def test_get_registry_bearer_token_sends_basic_without_redirects():
    token_resp = _mock_token_response("tok")
    session = MagicMock()
    session.get = MagicMock(return_value=token_resp)

    result = await get_registry_bearer_token(
        session,
        (
            'Bearer realm="https://auth.docker.io/token",'
            'service="registry.docker.io"'
        ),
        "library/nginx",
        basic_token="secret",
        ssl=True,
        insecure=False,
    )

    assert result == "tok"
    kwargs = session.get.call_args.kwargs
    assert kwargs["allow_redirects"] is False
    assert kwargs["headers"]["Authorization"] == "Basic secret"
    assert kwargs["ssl"] is True
    assert session.get.call_args.args[0].startswith(
        "https://auth.docker.io/token?"
    )


@pytest.mark.asyncio
async def test_get_registry_bearer_token_rejects_http_realm_when_secure():
    session = MagicMock()
    session.get = MagicMock()

    with pytest.raises(ValueError, match="HTTP Bearer realm"):
        await get_registry_bearer_token(
            session,
            'Bearer realm="http://127.0.0.1:16928/internal-metadata"',
            "test/image",
            basic_token="leaked",
            ssl=True,
            insecure=False,
        )

    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_registry_bearer_token_allows_http_realm_when_insecure():
    token_resp = _mock_token_response("tok")
    session = MagicMock()
    session.get = MagicMock(return_value=token_resp)

    result = await get_registry_bearer_token(
        session,
        'Bearer realm="http://registry.local/token",service="registry.local"',
        "myimage",
        basic_token="local_token",
        ssl=False,
        insecure=True,
    )

    assert result == "tok"
    assert session.get.call_args.args[0].startswith(
        "http://registry.local/token?"
    )
    assert session.get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_header, match",
    [
        ('Bearer realm="file:///etc/passwd"', "Invalid Bearer realm"),
        ('Bearer realm="/relative"', "Invalid Bearer realm"),
        ("Bearer service=registry.docker.io", "Bearer realm is missing"),
    ],
)
async def test_get_registry_bearer_token_rejects_invalid_realm(
    auth_header, match
):
    session = MagicMock()
    session.get = MagicMock()

    with pytest.raises(ValueError, match=match):
        await get_registry_bearer_token(
            session,
            auth_header,
            "test/image",
            basic_token="secret",
        )

    session.get.assert_not_called()
