from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from backend.core.agent_client import AgentClient, AgentClientContainer
from backend.core.update_actions.hooks_executor import (
    get_hooks_map,
    run_hooks,
)
from backend.enums.hook_name_enum import EHookName
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.containers.containers_schemas import ContainerHooks
from shared.schemas.container_schemas import ExecContainerRequestBodySchema

base_module = "backend.core.update_actions.hooks_executor"


@pytest.mark.asyncio
async def test_run_hooks_returns_empty_list_when_no_hooks_configured():
    client = AsyncMock(spec=AgentClient)
    client.container = AsyncMock(spec=AgentClientContainer)

    errors = await run_hooks(client, "my-container", None, EHookName.PRE_UPDATE)

    assert errors == []
    client.container.exec.assert_not_called()


@pytest.mark.asyncio
async def test_run_hooks_runs_each_command_in_order():
    client = AsyncMock(spec=AgentClient)
    client.container = AsyncMock(spec=AgentClientContainer)
    hooks = ContainerHooks(pre_update=["echo one", "echo two"])

    errors = await run_hooks(client, "my-container", hooks, EHookName.PRE_UPDATE)

    assert errors == []
    assert client.container.exec.call_count == 2
    client.container.exec.assert_any_call(
        "my-container", ExecContainerRequestBodySchema(command="echo one")
    )
    client.container.exec.assert_any_call(
        "my-container", ExecContainerRequestBodySchema(command="echo two")
    )


@pytest.mark.asyncio
async def test_run_hooks_collects_errors_but_keeps_running():
    client = AsyncMock(spec=AgentClient)
    client.container = AsyncMock(spec=AgentClientContainer)
    client.container.exec.side_effect = [Exception("boom"), None]
    hooks = ContainerHooks(pre_update=["echo one", "echo two"])

    errors = await run_hooks(client, "my-container", hooks, EHookName.PRE_UPDATE)

    assert len(errors) == 1
    assert str(errors[0]) == "boom"
    assert client.container.exec.call_count == 2


@pytest.mark.asyncio
async def test_get_hooks_map_empty_names_skips_db(mocker: MockerFixture):
    session_maker_mock = mocker.patch(f"{base_module}.async_session_maker")

    result = await get_hooks_map(1, [])

    assert result == {}
    session_maker_mock.assert_not_called()


@pytest.mark.asyncio
async def test_get_hooks_map_builds_map_from_db_rows(mocker: MockerFixture):
    row_with_hooks = mocker.Mock(spec=ContainersModel)
    row_with_hooks.name = "with-hooks"
    row_with_hooks.hooks = {"pre_update": ["echo hi"]}

    row_without_hooks = mocker.Mock(spec=ContainersModel)
    row_without_hooks.name = "without-hooks"
    row_without_hooks.hooks = None

    session_mock = AsyncMock()
    session_mock.scalars.return_value = [row_with_hooks, row_without_hooks]

    session_cm = mocker.MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session_mock)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    result = await get_hooks_map(1, ["with-hooks", "without-hooks"])

    assert result["with-hooks"].pre_update == ["echo hi"]
    assert result["without-hooks"] == ContainerHooks()
