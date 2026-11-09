import base64
import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from shared.runtime.registry_auth import (
    image_registry_host,
    normalize_registry_host,
    registry_auth_for_image,
)
from shared.runtime.runtime_client import RuntimeClient, encode_registry_auth

AUTH = base64.b64encode(b"user:secret").decode("ascii")


def _write_config(directory: Path, payload: dict) -> None:
    (directory / "config.json").write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ghcr.io", "ghcr.io"),
        ("https://GHCR.IO/v1/", "ghcr.io"),
        ("localhost:5000", "localhost:5000"),
        ("https://index.docker.io/v1/", "registry-1.docker.io"),
        ("docker.io", "registry-1.docker.io"),
    ],
)
def test_normalize_registry_host(value: str, expected: str) -> None:
    assert normalize_registry_host(value) == expected


@pytest.mark.parametrize(
    ("image", "host"),
    [
        ("nginx:1", "docker.io"),
        ("library/nginx", "docker.io"),
        ("ghcr.io/org/app:1", "ghcr.io"),
        ("localhost:5000/app:tests", "localhost:5000"),
    ],
)
def test_image_registry_host(image: str, host: str) -> None:
    assert image_registry_host(image) == host


def test_registry_auth_decodes_matching_entry(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        {"auths": {"https://index.docker.io/v1/": {"auth": AUTH}}},
    )

    auth = registry_auth_for_image("nginx:1", config_dir=tmp_path)

    assert auth == {
        "username": "user",
        "password": "secret",
        "serveraddress": "https://index.docker.io/v1/",
    }


def test_registry_auth_uses_identity_token_without_password(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        {"auths": {"myregistry.azurecr.io": {"identitytoken": "refresh-token"}}},
    )

    auth = registry_auth_for_image("myregistry.azurecr.io/app:1", config_dir=tmp_path)

    assert auth == {
        "identitytoken": "refresh-token",
        "serveraddress": "myregistry.azurecr.io",
    }


def test_registry_auth_identity_token_precedes_username_password(
    tmp_path: Path,
) -> None:
    _write_config(
        tmp_path,
        {
            "auths": {
                "myregistry.azurecr.io": {
                    "username": "00000000-0000-0000-0000-000000000000",
                    "password": "secret",
                    "identitytoken": " refresh-token ",
                }
            }
        },
    )

    auth = registry_auth_for_image("myregistry.azurecr.io/app:1", config_dir=tmp_path)

    assert auth == {
        "identitytoken": "refresh-token",
        "serveraddress": "myregistry.azurecr.io",
    }


def test_registry_auth_uses_username_and_password_fields(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        {
            "auths": {
                "localhost:5000": {
                    "username": "user",
                    "password": "secret",
                }
            }
        },
    )

    auth = registry_auth_for_image("localhost:5000/app:tests", config_dir=tmp_path)

    assert auth == {
        "username": "user",
        "password": "secret",
        "serveraddress": "localhost:5000",
    }


def test_registry_auth_missing_entry_returns_none(tmp_path: Path) -> None:
    _write_config(tmp_path, {"auths": {"ghcr.io": {"auth": AUTH}}})

    assert registry_auth_for_image("localhost:5000/app", config_dir=tmp_path) is None


def test_registry_auth_missing_file_returns_none(tmp_path: Path) -> None:
    assert registry_auth_for_image("nginx", config_dir=tmp_path) is None


def test_registry_auth_warns_about_credential_helpers(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import shared.runtime.registry_auth as registry_auth

    registry_auth._helper_warning_logged = False
    _write_config(
        tmp_path,
        {"credsStore": "desktop", "auths": {"ghcr.io": {"auth": AUTH}}},
    )

    with caplog.at_level("WARNING"):
        auth = registry_auth_for_image("ghcr.io/org/app", config_dir=tmp_path)

    assert auth is not None
    assert "credsStore" in caplog.text


@pytest.mark.asyncio
async def test_image_pull_sends_registry_auth_header(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    _write_config(
        tmp_path,
        {"auths": {"localhost:5000": {"auth": AUTH}}},
    )
    auth = registry_auth_for_image("localhost:5000/app:tests", config_dir=tmp_path)
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = mocker.MagicMock()
    request = mocker.patch.object(
        client,
        "_request",
        new=mocker.AsyncMock(return_value=response),
    )

    async def _empty(_reader: object):
        if False:
            yield {}

    mocker.patch(
        "shared.runtime.runtime_client.parse_json_lines_stream",
        side_effect=_empty,
    )
    mocker.patch.object(client, "image_inspect", new=mocker.AsyncMock())

    await client.image_pull("localhost:5000/app:tests", auth_config=auth)

    assert request.await_args is not None
    header = request.await_args.kwargs["headers"]["X-Registry-Auth"]
    assert header == encode_registry_auth(auth)


@pytest.mark.asyncio
async def test_image_pull_sends_identity_token_header(
    mocker: MockerFixture,
) -> None:
    auth = {
        "identitytoken": "refresh-token",
        "serveraddress": "myregistry.azurecr.io",
    }
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = mocker.MagicMock()
    request = mocker.patch.object(
        client,
        "_request",
        new=mocker.AsyncMock(return_value=response),
    )

    async def _empty(_reader: object):
        if False:
            yield {}

    mocker.patch(
        "shared.runtime.runtime_client.parse_json_lines_stream",
        side_effect=_empty,
    )
    mocker.patch.object(client, "image_inspect", new=mocker.AsyncMock())

    await client.image_pull("myregistry.azurecr.io/app:1", auth_config=auth)

    header = request.await_args.kwargs["headers"]["X-Registry-Auth"]
    decoded = json.loads(base64.urlsafe_b64decode(header))
    assert decoded == auth
    assert "username" not in decoded
    assert "password" not in decoded
