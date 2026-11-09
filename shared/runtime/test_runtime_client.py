import base64
import json
import struct
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from pytest_mock import MockerFixture

from shared.runtime.runtime_client import (
    CLIENT_MAX_DOCKER_API,
    RuntimeClient,
    encode_registry_auth,
    format_log_time,
    parse_version_tuple,
    split_image_ref,
)
from shared.runtime.runtime_errors import (
    IncompatibleRuntimeError,
    RuntimeClientError,
    RuntimeConflictError,
    RuntimeExecError,
    RuntimeNotFoundError,
    StreamTruncatedError,
)
from shared.runtime.runtime_models import (
    ContainerConfig,
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host",
    ["ssh://user@example", "npipe:////./pipe/docker_engine"],
)
async def test_unsupported_docker_host_scheme(host: str):
    client = RuntimeClient(host)
    with pytest.raises(RuntimeClientError, match="Unsupported DOCKER_HOST scheme"):
        await client._get_session()


@pytest.mark.asyncio
async def test_plain_socket_path_uses_unix_connector():
    client = RuntimeClient("/tmp/tugtainer-no-such.sock")
    session = await client._get_session()
    try:
        assert isinstance(session.connector, aiohttp.UnixConnector)
    finally:
        await client.close()


def test_encode_registry_auth():
    auth = {"serveraddress": "ghcr.io", "username": "user", "password": "secret"}
    encoded = encode_registry_auth(auth)
    assert encoded is not None
    raw = json.dumps(auth).encode()
    assert encoded == base64.urlsafe_b64encode(raw).decode("ascii")
    assert encoded.endswith("=")
    assert json.loads(base64.urlsafe_b64decode(encoded)) == auth


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


class _Response:
    def __init__(
        self,
        status: int,
        body: str = "",
        json_body: object | None = None,
    ) -> None:
        self.status = status
        self._body = body
        self._json_body = json_body
        self.closed = False

    async def text(self) -> str:
        return self._body

    async def json(self) -> object:
        if self._json_body is None:
            raise ValueError("not json")
        return self._json_body

    def close(self) -> None:
        self.closed = True


class _Session:
    def __init__(
        self, response: _Response | None = None, error: Exception | None = None
    ):
        self._response = response
        self._error = error

    async def request(self, **_kwargs: object) -> _Response:
        if self._error:
            raise self._error
        assert self._response is not None
        return self._response


def _client_with_session(mocker: MockerFixture, session: _Session) -> RuntimeClient:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    client._base_url = "http://localhost"
    mocker.patch.object(client, "_get_session", new=AsyncMock(return_value=session))
    return client


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (404, RuntimeNotFoundError),
        (409, RuntimeConflictError),
        (400, RuntimeClientError),
        (500, RuntimeClientError),
    ],
)
@pytest.mark.asyncio
async def test_request_maps_error_status(
    mocker: MockerFixture,
    status: int,
    error_type: type[Exception],
) -> None:
    response = _Response(status, body="detail", json_body={"message": "detail"})
    client = _client_with_session(mocker, _Session(response))

    with pytest.raises(error_type) as exc_info:
        await client._request("GET", "/containers/missing/json")

    assert getattr(exc_info.value, "status_code", None) == status
    assert response.closed is True


@pytest.mark.asyncio
async def test_request_timeout(mocker: MockerFixture) -> None:
    client = _client_with_session(mocker, _Session(error=TimeoutError()))

    with pytest.raises(RuntimeClientError, match="timeout"):
        await client._request("GET", "/_ping", use_api_prefix=False)


@pytest.mark.asyncio
async def test_request_connection_error(mocker: MockerFixture) -> None:
    client = _client_with_session(
        mocker,
        _Session(error=aiohttp.ClientConnectionError("refused")),
    )

    with pytest.raises(RuntimeClientError, match="Connection error"):
        await client._request("GET", "/containers/json")


def _stream(data: bytes) -> aiohttp.StreamReader:
    reader = aiohttp.StreamReader(MagicMock(), limit=2**16)
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def _frame(stream_type: int, payload: bytes) -> bytes:
    return struct.pack(">BxxxI", stream_type, len(payload)) + payload


@pytest.mark.asyncio
async def test_container_exec_nonzero_includes_stderr(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    created = MagicMock()
    created.json = AsyncMock(return_value={"Id": "exec1"})
    started = MagicMock()
    started.content = _stream(_frame(2, b"boom\n"))
    inspected = MagicMock()
    inspected.json = AsyncMock(return_value={"Running": False, "ExitCode": 2})
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(side_effect=[created, started, inspected]),
    )

    with pytest.raises(RuntimeExecError) as exc_info:
        await client.container_exec("web", ["false"])

    assert exc_info.value.exit_code == 2
    assert exc_info.value.stderr == "boom\n"


def _exec_responses(
    inspect_payloads: list[dict[str, object]],
) -> list[MagicMock]:
    created = MagicMock()
    created.json = AsyncMock(return_value={"Id": "exec1"})
    started = MagicMock()
    started.content = _stream(_frame(1, b"ok"))
    inspected = [
        MagicMock(json=AsyncMock(return_value=payload), close=MagicMock())
        for payload in inspect_payloads
    ]
    return [created, started, *inspected]


@pytest.mark.asyncio
async def test_container_exec_missing_exit_code_fails(
    mocker: MockerFixture,
) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    mocker.patch("shared.runtime.runtime_client.asyncio.sleep", new=AsyncMock())
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(
            side_effect=_exec_responses([{"Running": False, "ExitCode": None}] * 4)
        ),
    )

    with pytest.raises(StreamTruncatedError, match="ExitCode"):
        await client.container_exec("web", ["true"])


@pytest.mark.asyncio
async def test_container_exec_still_running_fails(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    sleep = AsyncMock()
    mocker.patch("shared.runtime.runtime_client.asyncio.sleep", new=sleep)
    mocker.patch.object(
        client,
        "_request",
        new=AsyncMock(
            side_effect=_exec_responses([{"Running": True, "ExitCode": None}] * 4)
        ),
    )

    with pytest.raises(StreamTruncatedError, match="Running"):
        await client.container_exec("web", ["sleep"])

    assert sleep.await_count == 3


@pytest.mark.asyncio
async def test_image_pull_raises_on_stream_error(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    response = MagicMock()
    response.content = _stream(
        b'{"errorDetail": {"message": "unauthorized"}, "error": "unauthorized"}\n'
    )
    mocker.patch.object(client, "_request", new=AsyncMock(return_value=response))

    with pytest.raises(RuntimeClientError, match="unauthorized"):
        await client.image_pull("ghcr.io/org/app:1")


@pytest.mark.asyncio
async def test_service_update_sends_version_index(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    client._runtime_type = "docker"
    mocker.patch.object(
        client,
        "service_inspect",
        new=AsyncMock(
            return_value={
                "Version": {"Index": 7},
                "Spec": {"TaskTemplate": {"ContainerSpec": {"Image": "nginx:1"}}},
            }
        ),
    )
    response = MagicMock()
    request = mocker.patch.object(
        client, "_request", new=AsyncMock(return_value=response)
    )

    await client.service_update("svc1", "nginx:2")

    assert request.await_args is not None
    assert request.await_args.kwargs["params"] == {"version": 7}
    image = request.await_args.kwargs["json_data"]["TaskTemplate"]["ContainerSpec"]
    assert image["Image"] == "nginx:2"


@pytest.mark.asyncio
async def test_service_update_requires_version_index(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    client._runtime_type = "docker"
    mocker.patch.object(
        client,
        "service_inspect",
        new=AsyncMock(return_value={"Spec": {"TaskTemplate": {}}}),
    )

    with pytest.raises(RuntimeClientError, match="Version.Index"):
        await client.service_update("svc1", "nginx:2")


@pytest.mark.asyncio
async def test_service_update_rejected_on_podman() -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.41"
    client._runtime_type = "podman"

    with pytest.raises(IncompatibleRuntimeError, match="Podman"):
        await client.service_update("svc1", "nginx:2")


@pytest.mark.parametrize("tty", [False, True])
@pytest.mark.asyncio
async def test_container_logs_follow_tty(mocker: MockerFixture, tty: bool) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    mocker.patch.object(
        client,
        "container_inspect",
        new=AsyncMock(
            return_value=ContainerInspectResult(config=ContainerConfig(tty=tty))
        ),
    )
    raw = b"plain log\n" if tty else _frame(1, b"plain log\n")
    response = MagicMock()
    response.content = _stream(raw)
    mocker.patch.object(client, "_request", new=AsyncMock(return_value=response))

    text = await client.container_logs("web")

    assert text == "plain log\n"


@pytest.mark.asyncio
async def test_container_logs_forwards_details(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    mocker.patch.object(
        client,
        "container_inspect",
        new=AsyncMock(
            return_value=ContainerInspectResult(config=ContainerConfig(tty=False))
        ),
    )
    response = MagicMock()
    response.content = _stream(_frame(1, b"line\n"))
    request = mocker.patch.object(
        client, "_request", new=AsyncMock(return_value=response)
    )

    text = await client.container_logs("web", tail=20, timestamps=True, details=True)

    assert text == "line\n"
    params = request.await_args.kwargs["params"]
    assert params["details"] is True
    assert params["timestamps"] is True
    assert params["tail"] == 20


def test_format_log_time() -> None:
    moment = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    assert format_log_time(moment) == str(int(moment.timestamp()))
    assert format_log_time(moment.replace(tzinfo=None)) == str(int(moment.timestamp()))
    assert format_log_time("10m") == "10m"
    assert format_log_time(1_700_000_000) == "1700000000"
    hour_ago = int(format_log_time(timedelta(hours=1)))
    expected = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    assert abs(hour_ago - expected) <= 1


@pytest.mark.asyncio
async def test_container_logs_sends_unix_timestamps(mocker: MockerFixture) -> None:
    client = RuntimeClient()
    client._negotiated_api_prefix = "/v1.48"
    mocker.patch.object(
        client,
        "container_inspect",
        new=AsyncMock(
            return_value=ContainerInspectResult(config=ContainerConfig(tty=False))
        ),
    )
    response = MagicMock()
    response.content = _stream(_frame(1, b"line\n"))
    request = mocker.patch.object(
        client, "_request", new=AsyncMock(return_value=response)
    )
    since = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    until = since + timedelta(hours=1)

    await client.container_logs("web", since=since, until=until)

    params = request.await_args.kwargs["params"]
    assert params["since"] == str(int(since.timestamp()))
    assert params["until"] == str(int(until.timestamp()))
