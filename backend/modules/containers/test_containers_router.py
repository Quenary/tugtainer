from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import app
from backend.core.agent_client import (
    AgentClient,
    AgentClientContainer,
)
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.containers.containers_schemas import (
    ContainerHooks,
    ContainersListItem,
)

base_module = "backend.modules.containers.containers_router"

client = TestClient(app)


async def override_is_authorized():
    return True


app.dependency_overrides[is_authorized] = override_is_authorized


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
