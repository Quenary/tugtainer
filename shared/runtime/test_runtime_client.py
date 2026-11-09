from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from shared.runtime.runtime_client import (
    CLIENT_MAX_DOCKER_API,
    RuntimeClient,
    encode_registry_auth,
    parse_version_tuple,
    split_image_ref,
)
from shared.runtime.runtime_errors import (
    IncompatibleRuntimeError,
    RuntimeNotFoundError,
)
from shared.runtime.runtime_models import (
    ContainerInspectResult,
    ContainerState,
    ImageInspectResult,
)
from shared.schemas.container_schemas import CreateContainerRequestBodySchema


def test_parse_version_tuple():
    assert parse_version_tuple("1.44") == (1, 44)
    assert parse_version_tuple("1.48.2") == (1, 48)
    assert parse_version_tuple("2") == (2, 0)
    assert parse_version_tuple(None) == (0, 0)


def test_encode_registry_auth():
    auth = {"serveraddress": "ghcr.io", "username": "user", "password": "token"}
    encoded = encode_registry_auth(auth)
    assert encoded is not None
    assert "=" not in encoded  # Must be stripped padding


@pytest.mark.asyncio
async def test_get_version_docker_negotiation(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "28.0.0",
            "ApiVersion": "1.48",
            "MinAPIVersion": "1.24",
            "Components": [{"Name": "Engine", "Version": "28.0.0"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    assert version_info.runtime_type == "docker"
    assert version_info.negotiated_api == "1.48"
    assert client._negotiated_api_prefix == "/v1.48"


@pytest.mark.asyncio
async def test_get_version_docker_caps_at_max_supported(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    # Future daemon with API 1.55
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "32.0.0",
            "ApiVersion": "1.55",
            "MinAPIVersion": "1.24",
            "Components": [{"Name": "Engine"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    # Must negotiate to CLIENT_MAX_DOCKER_API (1.48)
    assert (
        version_info.negotiated_api
        == f"{CLIENT_MAX_DOCKER_API[0]}.{CLIENT_MAX_DOCKER_API[1]}"
    )
    assert (
        client._negotiated_api_prefix
        == f"/v{CLIENT_MAX_DOCKER_API[0]}.{CLIENT_MAX_DOCKER_API[1]}"
    )


@pytest.mark.asyncio
async def test_get_version_docker_too_old_raises(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {}
    # Daemon older than 1.44 (e.g. 1.41)
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "20.10.0",
            "ApiVersion": "1.41",
            "MinAPIVersion": "1.12",
            "Components": [{"Name": "Engine"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    with pytest.raises(IncompatibleRuntimeError) as exc_info:
        await client.get_version()
    assert "below minimum supported 1.44" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_version_podman_detection(mocker: MockerFixture):
    client = RuntimeClient()
    mock_resp = mocker.MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Libpod-API-Version": "5.2.0"}
    mock_resp.json = mocker.AsyncMock(
        return_value={
            "Version": "5.2.0",
            "ApiVersion": "1.41",
            "Components": [{"Name": "Podman Engine", "Version": "5.2.0"}],
        }
    )
    mock_resp.close = mocker.MagicMock()
    mocker.patch.object(client, "_request", return_value=mock_resp)

    version_info = await client.get_version()
    assert version_info.runtime_type == "podman"
    assert version_info.libpod_api_version == "5.2.0"
    # Podman does NOT raise for ApiVersion < 1.44
    assert client._negotiated_api_prefix == "/v1.41"


DIGEST = "sha256:" + "a" * 64


@pytest.mark.parametrize(
    ("spec", "repo", "tag", "digest"),
    [
        ("nginx", "nginx", None, None),
        ("nginx:1", "nginx", "1", None),
        ("localhost:5000/app", "localhost:5000/app", None, None),
        ("localhost:5000/app:tests", "localhost:5000/app", "tests", None),
        (f"repo@{DIGEST}", "repo", None, DIGEST),
        (f"repo:tag@{DIGEST}", "repo", "tag", DIGEST),
    ],
)
def test_split_image_ref(
    spec: str,
    repo: str,
    tag: str | None,
    digest: str | None,
) -> None:
    assert split_image_ref(spec) == (repo, tag, digest)


async def _empty_pull_stream(_reader: object):
    if False:
        yield {}


@pytest.mark.parametrize(
    ("spec", "params"),
    [
        ("nginx", {"fromImage": "nginx", "tag": "latest"}),
        ("nginx:1", {"fromImage": "nginx", "tag": "1"}),
        (
            "localhost:5000/app",
            {"fromImage": "localhost:5000/app", "tag": "latest"},
        ),
        (
            "localhost:5000/app:tests",
            {"fromImage": "localhost:5000/app", "tag": "tests"},
        ),
        (f"repo@{DIGEST}", {"fromImage": f"repo@{DIGEST}"}),
        (f"repo:tag@{DIGEST}", {"fromImage": f"repo@{DIGEST}"}),
    ],
)
@pytest.mark.asyncio
async def test_image_pull_reference_params(
    mocker: MockerFixture,
    spec: str,
    params: dict[str, str],
) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = mocker.MagicMock()
    request = mocker.patch.object(
        client, "_request", new=AsyncMock(return_value=response)
    )
    mocker.patch(
        "shared.runtime.runtime_client.parse_json_lines_stream",
        side_effect=_empty_pull_stream,
    )
    mocker.patch.object(
        client,
        "image_inspect",
        new=AsyncMock(return_value=ImageInspectResult(id="sha256:pulled")),
    )

    await client.image_pull(spec)

    assert request.await_args is not None
    assert request.await_args.args == ("POST", "/images/create")
    assert request.await_args.kwargs["params"] == params


@pytest.mark.parametrize(
    ("repo", "expected_repo", "expected_tag"),
    [
        ("nginx", "nginx", "latest"),
        ("nginx:1", "nginx", "1"),
        ("localhost:5000/app", "localhost:5000/app", "latest"),
        ("localhost:5000/app:tests", "localhost:5000/app", "tests"),
        (f"repo@{DIGEST}", "repo", "latest"),
        (f"repo:tag@{DIGEST}", "repo", "tag"),
    ],
)
@pytest.mark.asyncio
async def test_image_tag_reference_params(
    mocker: MockerFixture,
    repo: str,
    expected_repo: str,
    expected_tag: str,
) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = mocker.MagicMock()
    request = mocker.patch.object(
        client, "_request", new=AsyncMock(return_value=response)
    )

    await client.image_tag("sha256:source", repo)

    assert request.await_args is not None
    assert request.await_args.kwargs["params"] == {
        "repo": expected_repo,
        "tag": expected_tag,
    }


def _json_response(mocker: MockerFixture, payload: object):
    response = mocker.MagicMock()
    response.json = AsyncMock(return_value=payload)
    return response


@pytest.mark.asyncio
async def test_container_list_inspects_each_summary(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    summary = {
        "Id": "abc",
        "Names": ["/web"],
        "State": "running",
        "Status": "Up 3 seconds",
    }
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=_json_response(mocker, [summary])),
    )
    inspected = ContainerInspectResult(
        id="abc",
        name="web",
        state=ContainerState(status="running", running=True),
    )
    inspect = mocker.patch.object(
        client,
        "container_inspect",
        new=AsyncMock(return_value=inspected),
    )

    result = await client.container_list()

    assert result == [inspected]
    inspect.assert_awaited_once_with("abc")


@pytest.mark.asyncio
async def test_container_list_skips_removed_container(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    summaries = [
        {"Id": "gone", "State": "running"},
        {"Id": "kept", "State": "exited"},
    ]
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=_json_response(mocker, summaries)),
    )
    kept = ContainerInspectResult(id="kept", name="kept")

    async def inspect_one(item_id: str) -> ContainerInspectResult:
        if item_id == "gone":
            raise RuntimeNotFoundError("gone")
        return kept

    mocker.patch.object(client, "container_inspect", new=inspect_one)

    result = await client.container_list()

    assert result == [kept]


@pytest.mark.asyncio
async def test_image_list_inspects_each_summary(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    summary = {"Id": "sha256:img", "RepoTags": ["nginx:1"], "Created": 1710000000}
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=_json_response(mocker, [summary])),
    )
    inspected = ImageInspectResult(id="sha256:img", repo_tags=["nginx:1"])
    inspect = mocker.patch.object(
        client,
        "image_inspect",
        new=AsyncMock(return_value=inspected),
    )

    result = await client.image_list()

    assert result == [inspected]
    inspect.assert_awaited_once_with("sha256:img")


@pytest.mark.asyncio
async def test_service_list_requests_task_status(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    client._runtime_type = "docker"
    payload = [
        {
            "ID": "svc1",
            "ServiceStatus": {"RunningTasks": 2, "DesiredTasks": 3},
        }
    ]
    request = mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=_json_response(mocker, payload)),
    )

    result = await client.service_list()

    assert request.await_args is not None
    assert request.await_args.args == ("GET", "/services")
    assert request.await_args.kwargs["params"] == {"status": True}
    assert result[0]["ServiceStatus"]["RunningTasks"] == 2
    assert result[0]["ServiceStatus"]["DesiredTasks"] == 3


@pytest.mark.asyncio
async def test_container_create_sends_engine_body(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = mocker.MagicMock()
    response.json = AsyncMock(return_value={"Id": "created"})
    request = mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(return_value=response),
    )
    mocker.patch.object(
        client,
        "container_inspect",
        new=AsyncMock(return_value=ContainerInspectResult(id="created")),
    )

    await client.container_create(
        CreateContainerRequestBodySchema(
            image="nginx",
            name="web",
            command=["nginx"],
            platform="linux/amd64",
        )
    )

    assert request.await_args is not None
    assert request.await_args.kwargs["json_data"]["Image"] == "nginx"
    assert request.await_args.kwargs["json_data"]["Cmd"] == ["nginx"]
    assert "image" not in request.await_args.kwargs["json_data"]
    assert request.await_args.kwargs["params"] == {
        "name": "web",
        "platform": "linux/amd64",
    }
