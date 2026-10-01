from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.update.update_job_executor import execute_update_job
from backend.core.jobs.update.update_job_plan_builder import UpdateJobPlan
from backend.enums.hook_name_enum import EHookName

base_module = "backend.core.jobs.update.update_job_executor"


@pytest.mark.asyncio
async def test_pre_update_hook_failure_skips_stop(mocker: MockerFixture) -> None:
    container = SimpleNamespace(
        name="web",
        image="sha256:local",
        config=SimpleNamespace(image="nginx:latest"),
        state=SimpleNamespace(status="running", health=None),
    )
    client = MagicMock()
    client.image.inspect = AsyncMock(return_value=MagicMock(id="sha256:local"))
    client.image.pull = AsyncMock(return_value=MagicMock(id="sha256:remote"))
    client.container.inspect = AsyncMock(return_value=container)
    client.container.stop = AsyncMock()
    client.container.start = AsyncMock()

    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)
    mocker.patch(f"{base_module}.asyncio.sleep", new=AsyncMock())
    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", True)
    mocker.patch(
        f"{base_module}.get_hooks_map",
        new=AsyncMock(return_value={"web": SimpleNamespace()}),
    )

    async def hooks(_client, _name, _hooks, hook_name):
        if hook_name == EHookName.PRE_UPDATE:
            return [RuntimeError("hook failed")]
        return []

    mocker.patch(f"{base_module}.run_hooks", side_effect=hooks)
    mocker.patch(
        f"{base_module}.get_container_config",
        return_value=(MagicMock(), []),
    )
    mocker.patch(
        f"{base_module}.update_containers_data_after_execution",
        new=AsyncMock(),
    )

    plan = UpdateJobPlan(
        to_update={"web"},
        affected=set(),
        order=["web"],
        healthcheck_timeouts={"web": 1},
    )
    results = await execute_update_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        [container],  # type: ignore[list-item]
        plan,
        docker_version=None,
    )

    client.container.stop.assert_not_called()
    assert results[0].result is None
