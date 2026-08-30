from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)

from backend.core.agent_client import AgentClient, AgentClientNetwork
from backend.core.jobs.jobs_results import (
    ContainerJobOutcome,
    ContainerJobResult,
)
from backend.core.jobs.update.update_util import (
    disconnect_all_networks,
    update_containers_data_after_execution,
)
from backend.modules.containers.containers_model import ContainersModel
from shared.schemas.network_schemas import NetworkDisconnectBodySchema


def _container(
    name: str = "app",
    networks: dict | None = None,
):
    return SimpleNamespace(
        name=name,
        network_settings=SimpleNamespace(networks=networks),
    )


@pytest.mark.asyncio
async def test_disconnect_all_networks_disconnects_each_network():
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    container = _container(networks={"stacka_shared": {}, "proxy": {}})

    await disconnect_all_networks(client, container, True)

    assert client.network.disconnect.call_count == 2
    called_networks = {
        call.args[0].network for call in client.network.disconnect.call_args_list
    }
    assert called_networks == {"stacka_shared", "proxy"}
    for call in client.network.disconnect.call_args_list:
        body = call.args[0]
        assert isinstance(body, NetworkDisconnectBodySchema)
        assert body.container == "app"
        assert body.force is True


@pytest.mark.asyncio
async def test_disconnect_all_networks_logs_failure_and_continues(caplog):
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    client.network.disconnect.side_effect = [
        Exception("network in use"),
        None,
    ]
    container = _container(networks={"owned": {}, "proxy": {}})

    await disconnect_all_networks(client, container, True)

    assert client.network.disconnect.call_count == 2
    assert "Failed to disconnect app from network owned" in caplog.text
    assert "network in use" in caplog.text


@pytest.mark.asyncio
async def test_disconnect_all_networks_noop_without_networks():
    client = AsyncMock(spec=AgentClient)
    client.network = AsyncMock(spec=AgentClientNetwork)
    container = _container(networks=None)

    await disconnect_all_networks(client, container, True)

    client.network.disconnect.assert_not_called()


class _FakeSession:
    """Minimal stand-in for the async session used by the update util."""

    def __init__(self, containers: list[ContainersModel]):
        self._containers = containers
        self.committed = False

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def scalars(self, *args: object, **kwargs: object):
        return list(self._containers)

    async def commit(self) -> None:
        self.committed = True


def _db_container(name: str = "app", **kwargs) -> ContainersModel:
    return ContainersModel(name=name, host_id=1, **kwargs)


def _patch_session(
    db_containers: list[ContainersModel],
    mocker,
) -> _FakeSession:
    session = _FakeSession(db_containers)
    mocker.patch(
        "backend.core.jobs.update.update_util.async_session_maker",
        return_value=session,
    )
    return session


def _job_result(
    result: ContainerJobOutcome,
    name: str = "app",
    digests: list[str] | None = None,
    tags: list[str] | None = None,
    version: str | None = None,
) -> ContainerJobResult:
    return ContainerJobResult(
        container=ContainerInspectResult(name=name),
        result=result,
        previous_image_digests=digests or [],
        previous_image_tags=tags or [],
        previous_image_version=version,
    )


@pytest.mark.asyncio
async def test_stores_previous_image_after_update(mocker):
    container = _db_container(update_available=True)
    session = _patch_session([container], mocker)

    await update_containers_data_after_execution(
        1,
        [
            _job_result(
                "updated",
                digests=["nginx@sha256:abc"],
                tags=["nginx:1.2.3"],
                version="1.2.3",
            )
        ],
    )

    assert container.previous_image_digests == ["nginx@sha256:abc"]
    assert container.previous_image_tags == ["nginx:1.2.3"]
    assert container.previous_image_version == "1.2.3"
    assert container.update_available is False
    assert container.updated_at is not None
    assert session.committed is True


@pytest.mark.asyncio
async def test_does_not_store_previous_image_after_rollback(mocker):
    container = _db_container(
        previous_image_digests=["nginx@sha256:old"],
        previous_image_version="1.0.0",
    )
    _patch_session([container], mocker)

    await update_containers_data_after_execution(
        1,
        [_job_result("rolled_back")],
    )

    assert container.previous_image_digests == ["nginx@sha256:old"]
    assert container.previous_image_version == "1.0.0"


@pytest.mark.asyncio
async def test_keeps_stored_previous_image_when_update_carries_none(mocker):
    """
    An update that could not collect any identity must not wipe the pin
    the user already had.
    """
    container = _db_container(
        previous_image_digests=["nginx@sha256:old"],
        previous_image_tags=["nginx:1.0.0"],
        previous_image_version="1.0.0",
    )
    _patch_session([container], mocker)

    await update_containers_data_after_execution(
        1,
        [_job_result("updated")],
    )

    assert container.previous_image_digests == ["nginx@sha256:old"]
    assert container.previous_image_tags == ["nginx:1.0.0"]
    assert container.previous_image_version == "1.0.0"
    assert container.update_available is False


@pytest.mark.asyncio
async def test_stores_previous_image_without_digests(mocker):
    """A locally built image has no digests, its tags are still worth keeping."""
    container = _db_container()
    _patch_session([container], mocker)

    await update_containers_data_after_execution(
        1,
        [_job_result("updated", tags=["my-app:latest"])],
    )

    assert container.previous_image_digests == []
    assert container.previous_image_tags == ["my-app:latest"]
