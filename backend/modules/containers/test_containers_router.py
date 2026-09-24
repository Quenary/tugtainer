from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import app
from backend.core.agent_client import (
    AgentClient,
    AgentClientContainer,
)
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized_req
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.containers.containers_schemas import (
    ContainerHooks,
    ContainersListItem,
)

base_module = "backend.modules.containers.containers_router"

client = TestClient(app)


async def override_is_authorized_req():
    return True


app.dependency_overrides[is_authorized_req] = override_is_authorized_req


@pytest.mark.asyncio
async def test_get_container(mocker: MockerFixture):

    mocker.patch(
        f"{base_module}.get_host",
        mocker.AsyncMock(return_value=mocker.Mock()),
    )

    agent_client_mock = mocker.Mock(spec=AgentClient)
    agent_client_mock.container = mocker.Mock(spec=AgentClientContainer)
    agent_client_mock.container.inspect = mocker.AsyncMock(
        return_value=ContainerInspectResult(
            id="test-id",
            name="test-container",
        )
    )

    mocker.patch(
        f"{base_module}.AgentClientManager.get_host_client",
        return_value=agent_client_mock,
    )

    mocker.patch(
        f"{base_module}.ContainersListItem.from_sources",
        return_value=ContainersListItem(
            host_id=1,
            name="test-container",
            container_id="test-container-id",
            image="test:latest",
            protected=False,
            ports=None,
            status=None,
            exit_code=None,
            health=None,
        ),
    )

    result_scalar_mock = mocker.Mock(spec=ContainersModel)
    result_scalar_mock.id = 1
    result_scalar_mock.host_id = 1
    result_scalar_mock.name = "test-container"

    mock_result = mocker.Mock()
    mock_result.scalar_one_or_none.return_value = result_scalar_mock

    async_session_mock = AsyncMock(spec=AsyncSession)
    async_session_mock.execute.return_value = mock_result

    async def override_get_async_session():
        return async_session_mock

    app.dependency_overrides[get_async_session] = override_get_async_session

    response = client.get("/containers/1/test-container")

    assert response.status_code == 200
    res = response.json()
    assert res["item"]["host_id"] == 1
    assert res["item"]["name"] == "test-container"
    assert res["item"]["container_id"] == "test-container-id"
    assert res["item"]["image"] == "test:latest"


@pytest.mark.asyncio
async def test_hooks_enabled_reflects_config(mocker: MockerFixture):
    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", True)
    response = client.get("/containers/hooks_enabled")
    assert response.status_code == 200
    assert response.json() is True

    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", False)
    response = client.get("/containers/hooks_enabled")
    assert response.status_code == 200
    assert response.json() is False


@pytest.mark.asyncio
async def test_host_progress_empty_returns_null(mocker: MockerFixture):
    host = mocker.Mock()
    host.id = 2
    host.name = "local"
    mocker.patch(
        f"{base_module}.get_host",
        mocker.AsyncMock(return_value=host),
    )

    async def override_get_async_session():
        return AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_async_session] = override_get_async_session

    response = client.get("/containers/progress/2")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_patch_container_hooks_forbidden_when_disabled(
    mocker: MockerFixture,
):
    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", False)

    response = client.patch(
        "/containers/1/test-container",
        json={"hooks": {"pre_update": ["echo hi"]}},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_container_hooks_allowed_when_enabled(
    mocker: MockerFixture,
):
    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", True)

    # db_cont only needs a real .name — patch_container_data reads it directly
    # to call client.container.inspect(db_cont.name). Everything else about
    # the row is irrelevant here because from_sources itself is mocked below
    # (same technique test_get_container already uses in this file) — do NOT
    # pass name=... to Mock()'s constructor, that sets the mock's debug repr
    # name instead of a `.name` attribute; set it by assignment instead.
    db_cont_mock = mocker.Mock(spec=ContainersModel)
    db_cont_mock.name = "test-container"
    mocker.patch(
        f"{base_module}.insert_or_update_container",
        mocker.AsyncMock(return_value=db_cont_mock),
    )
    mocker.patch(
        f"{base_module}.get_host",
        mocker.AsyncMock(return_value=mocker.Mock()),
    )
    agent_client_mock = mocker.Mock(spec=AgentClient)
    agent_client_mock.container = mocker.Mock(spec=AgentClientContainer)
    agent_client_mock.container.inspect = mocker.AsyncMock(
        return_value=ContainerInspectResult(
            id="test-id",
            name="test-container",
        )
    )
    mocker.patch(
        f"{base_module}.AgentClientManager.get_host_client",
        return_value=agent_client_mock,
    )
    mocker.patch(
        f"{base_module}.ContainersListItem.from_sources",
        return_value=ContainersListItem(
            host_id=1,
            name="test-container",
            container_id="test-container-id",
            image="test:latest",
            protected=False,
            ports=None,
            status=None,
            exit_code=None,
            health=None,
            hooks=ContainerHooks(pre_update=["echo hi"]),
        ),
    )

    response = client.patch(
        "/containers/1/test-container",
        json={"hooks": {"pre_update": ["echo hi"]}},
    )

    assert response.status_code == 200
    assert response.json()["hooks"]["pre_update"] == ["echo hi"]


def test_update_all_endpoint(mocker: MockerFixture):
    mock_update_all = mocker.patch(
        f"{base_module}.update_all_hosts",
        mocker.AsyncMock(),
    )
    response = client.post("/containers/update")
    assert response.status_code == 200
    mock_update_all.assert_called_once_with(True)


def test_check_all_endpoint(mocker: MockerFixture):
    mock_check_all = mocker.patch(
        f"{base_module}.check_all_hosts",
        mocker.AsyncMock(),
    )
    response = client.post("/containers/check")
    assert response.status_code == 200
    mock_check_all.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_control_containers_empty_names():
    response = client.post("/containers/1/start", json={"names": []})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_control_containers_success(mocker: MockerFixture):
    host = mocker.Mock()
    host.enabled = True
    mocker.patch(f"{base_module}.get_host", mocker.AsyncMock(return_value=host))

    c1 = ContainerInspectResult(id="id-1", name="c1")
    c2 = ContainerInspectResult(id="id-2", name="c2")

    agent_client_mock = mocker.Mock(spec=AgentClient)
    agent_client_mock.container = mocker.Mock(spec=AgentClientContainer)
    agent_client_mock.container.inspect = mocker.AsyncMock(side_effect=[c1, c2, c1, c2])
    agent_client_mock.container.stop = mocker.AsyncMock()

    mocker.patch(
        f"{base_module}.AgentClientManager.get_host_client",
        return_value=agent_client_mock,
    )
    mocker.patch(f"{base_module}.is_protected_container", return_value=False)

    mocker.patch(
        f"{base_module}.ContainersListItem.from_sources",
        side_effect=[
            ContainersListItem(
                host_id=1,
                name="c1",
                container_id="id-1",
                image="img1:latest",
                protected=False,
                ports=None,
                status="exited",
                exit_code=0,
                health=None,
            ),
            ContainersListItem(
                host_id=1,
                name="c2",
                container_id="id-2",
                image="img2:latest",
                protected=False,
                ports=None,
                status="exited",
                exit_code=0,
                health=None,
            ),
        ],
    )

    mock_result = mocker.Mock()
    mock_result.scalars.return_value.all.return_value = []
    async_session_mock = AsyncMock(spec=AsyncSession)
    async_session_mock.execute.return_value = mock_result

    async def override_session():
        return async_session_mock

    app.dependency_overrides[get_async_session] = override_session

    response = client.post("/containers/1/stop", json={"names": ["c1", "c2"]})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "c1"
    assert data[1]["name"] == "c2"
    assert agent_client_mock.container.stop.await_count == 2


@pytest.mark.asyncio
async def test_control_containers_protected_forbidden(mocker: MockerFixture):
    host = mocker.Mock()
    host.enabled = True
    mocker.patch(f"{base_module}.get_host", mocker.AsyncMock(return_value=host))

    c1 = ContainerInspectResult(id="id-1", name="c1")

    agent_client_mock = mocker.Mock(spec=AgentClient)
    agent_client_mock.container = mocker.Mock(spec=AgentClientContainer)
    agent_client_mock.container.inspect = mocker.AsyncMock(return_value=c1)
    agent_client_mock.container.stop = mocker.AsyncMock()

    mocker.patch(
        f"{base_module}.AgentClientManager.get_host_client",
        return_value=agent_client_mock,
    )
    mocker.patch(f"{base_module}.is_protected_container", return_value=True)

    response = client.post("/containers/1/stop", json={"names": ["c1"]})

    assert response.status_code == 403
    assert response.json()["detail"] == "Protected container not allowed"
    agent_client_mock.container.stop.assert_not_called()


def test_containers_list_item_auto_labels():
    from backend.const import (
        TUGTAINER_AUTO_CHECK_LABEL,
        TUGTAINER_AUTO_UPDATE_LABEL,
    )

    docker_cont = ContainerInspectResult(
        id="c1",
        name="test-cont",
        config=ContainerConfig(
            labels={
                TUGTAINER_AUTO_CHECK_LABEL: "true",
                TUGTAINER_AUTO_UPDATE_LABEL: "false",
            }
        ),
    )
    db_cont = ContainersModel(
        id=1,
        host_id=1,
        name="test-cont",
        check_enabled=False,
        update_enabled=True,
    )

    item = ContainersListItem.from_sources(1, docker_cont, db_cont)
    assert item.auto_check_label is True
    assert item.auto_update_label is False
    assert item.check_enabled is False
    assert item.update_enabled is True
