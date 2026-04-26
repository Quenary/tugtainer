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
    agent_client_mock.container = mocker.Mock(
        spec=AgentClientContainer
    )
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
        f"{base_module}.map_container_schema",
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

    app.dependency_overrides[get_async_session] = (
        override_get_async_session
    )

    response = client.get("/containers/1/test-container")

    assert response.status_code == 200
    res = response.json()
    assert res["item"]["host_id"] == 1
    assert res["item"]["name"] == "test-container"
    assert res["item"]["container_id"] == "test-container-id"
    assert res["item"]["image"] == "test:latest"
