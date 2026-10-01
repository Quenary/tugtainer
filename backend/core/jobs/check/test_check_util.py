from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.core.jobs.check.check_util import (
    ImagePlatform,
    filter_containers_by_check_enabled,
    get_image_remote_digest,
    get_registry_bearer_token,
    get_remote_image_metadata,
    is_insecure_registry,
    metadata_from_config_blob,
    next_manifest_step,
    parse_image_spec,
    parse_oci_created,
    sort_containers_by_checked_at,
)

module_path = "backend.core.jobs.check.check_util"


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

    filtered = filter_containers_by_check_enabled(
        cast(Any, containers), cast(Any, db_map)
    )

    assert [c.name for c in filtered] == ["enabled"]


def test_filter_containers_by_check_enabled_respects_auto_check_label():
    from backend.const import TUGTAINER_AUTO_CHECK_LABEL

    containers = [
        # Label true overrides DB false
        ContainerInspectResult(
            id="c1",
            name="label_true_db_false",
            config=ContainerConfig(labels={TUGTAINER_AUTO_CHECK_LABEL: "true"}),
        ),
        # Label false overrides DB true
        ContainerInspectResult(
            id="c2",
            name="label_false_db_true",
            config=ContainerConfig(labels={TUGTAINER_AUTO_CHECK_LABEL: "false"}),
        ),
        # Label absent, DB true
        ContainerInspectResult(
            id="c3",
            name="no_label_db_true",
            config=ContainerConfig(labels={}),
        ),
        # Label absent, DB false
        ContainerInspectResult(
            id="c4",
            name="no_label_db_false",
            config=ContainerConfig(labels={}),
        ),
    ]
    db_map = {
        "label_true_db_false": SimpleNamespace(check_enabled=False),
        "label_false_db_true": SimpleNamespace(check_enabled=True),
        "no_label_db_true": SimpleNamespace(check_enabled=True),
        "no_label_db_false": SimpleNamespace(check_enabled=False),
    }

    filtered = filter_containers_by_check_enabled(
        cast(Any, containers), cast(Any, db_map)
    )
    assert [c.name for c in filtered] == ["label_true_db_false", "no_label_db_true"]


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

    sorted_containers = sort_containers_by_checked_at(
        cast(Any, containers), cast(Any, db_map)
    )

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

    result = await get_image_remote_digest("localhost.attacker.com/test/image:test")

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
        ('Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'),
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
    assert session.get.call_args.args[0].startswith("https://auth.docker.io/token?")


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
    assert session.get.call_args.args[0].startswith("http://registry.local/token?")
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
async def test_get_registry_bearer_token_rejects_invalid_realm(auth_header, match):
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


def test_parse_oci_created_truncates_fractional_seconds():
    parsed = parse_oci_created("2015-10-31T22:22:56.015925234Z")

    assert parsed == datetime(2015, 10, 31, 22, 22, 56, 15925)
    assert parsed is not None
    assert parsed.tzinfo is None


def test_metadata_from_config_blob_reads_version_and_created():
    meta = metadata_from_config_blob(
        {
            "created": "2024-05-01T00:00:00Z",
            "config": {
                "Labels": {"org.opencontainers.image.version": " 2.3.7 "},
            },
        }
    )

    assert meta.version == "2.3.7"
    assert meta.created == datetime(2024, 5, 1)


def test_metadata_from_config_blob_keeps_created_when_label_is_missing():
    meta = metadata_from_config_blob({"created": "2024-05-01T00:00:00Z", "config": {}})

    assert meta.version is None
    assert meta.created == datetime(2024, 5, 1)


def test_next_manifest_step_reads_config_digest_from_image_manifest():
    step = next_manifest_step(
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": "sha256:cfg"},
        }
    )

    assert step == ("config", "sha256:cfg")


def test_next_manifest_step_picks_matching_platform_and_skips_unknown():
    document = {
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": "sha256:unknown",
                "platform": {"os": "unknown", "architecture": "unknown"},
            },
            {
                "digest": "sha256:arm",
                "platform": {"architecture": "arm64", "os": "linux", "variant": "v8"},
            },
            {
                "digest": "sha256:amd",
                "platform": {"architecture": "amd64", "os": "linux"},
            },
        ],
    }

    assert next_manifest_step(
        document, ImagePlatform(os="linux", architecture="arm64", variant="v8")
    ) == ("manifest", "sha256:arm")


def test_next_manifest_step_uses_the_only_usable_index_entry():
    document = {
        "manifests": [
            {
                "digest": "sha256:only",
                "platform": {"architecture": "amd64", "os": "linux"},
            }
        ]
    }

    assert next_manifest_step(document, None) == ("manifest", "sha256:only")


def test_next_manifest_step_does_not_guess_among_several_platforms():
    document = {
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "manifests": [
            {
                "digest": "sha256:amd",
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            {
                "digest": "sha256:arm",
                "platform": {"architecture": "arm64", "os": "linux"},
            },
        ],
    }

    assert next_manifest_step(document, None) is None


def _mock_json_response(status: int, payload: object, headers: dict | None = None):
    resp = MagicMock()
    resp.status = status
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value=payload)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


@pytest.mark.asyncio
async def test_get_remote_image_metadata_follows_index_then_config_blob(
    mocker: MockerFixture,
):
    index = _mock_json_response(
        200,
        {
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "digest": "sha256:child",
                    "platform": {"architecture": "amd64", "os": "linux"},
                }
            ],
        },
    )
    child = _mock_json_response(
        200,
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": "sha256:config"},
        },
    )
    blob = _mock_json_response(
        200,
        {
            "created": "2024-05-01T00:00:00Z",
            "config": {"Labels": {"org.opencontainers.image.version": "9.1.0"}},
        },
    )
    session = MagicMock()
    session.get = MagicMock(side_effect=[index, child, blob])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value=None)
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )

    meta = await get_remote_image_metadata(
        "ghcr.io/example/app:latest",
        ImagePlatform(os="linux", architecture="amd64"),
    )

    assert meta.version == "9.1.0"
    assert meta.created == datetime(2024, 5, 1)
    urls = [call.args[0] for call in session.get.call_args_list]
    assert urls == [
        "https://ghcr.io/v2/example/app/manifests/latest",
        "https://ghcr.io/v2/example/app/manifests/sha256:child",
        "https://ghcr.io/v2/example/app/blobs/sha256:config",
    ]


@pytest.mark.asyncio
async def test_get_remote_image_metadata_reuses_bearer_token_for_the_blob(
    mocker: MockerFixture,
):
    unauthorized = _mock_json_response(
        401,
        {},
        {
            "WWW-Authenticate": 'Bearer realm="https://auth.example/token",service="ghcr"'
        },
    )
    manifest = _mock_json_response(
        200,
        {
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"digest": "sha256:config"},
        },
    )
    blob = _mock_json_response(200, {"created": "2024-05-01T00:00:00Z", "config": {}})
    session = MagicMock()
    session.get = MagicMock(side_effect=[unauthorized, manifest, blob])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(f"{module_path}.aiohttp.ClientSession", return_value=session)
    mocker.patch(f"{module_path}.SettingsStorage.get", return_value=None)
    mocker.patch(
        f"{module_path}.DockerConfig",
        return_value=SimpleNamespace(get_basic_token=lambda _: None),
    )
    token = mocker.patch(
        f"{module_path}.get_registry_bearer_token",
        AsyncMock(return_value="tok"),
    )

    meta = await get_remote_image_metadata("ghcr.io/example/app:latest")

    assert meta.version is None
    assert meta.created == datetime(2024, 5, 1)
    token.assert_awaited_once()
    blob_headers = session.get.call_args_list[2].kwargs["headers"]
    assert blob_headers["Authorization"] == "Bearer tok"
    assert "application/vnd.oci.image.config.v1+json" in blob_headers["Accept"]
