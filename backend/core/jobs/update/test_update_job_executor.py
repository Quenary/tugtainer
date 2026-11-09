from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.update.update_job_executor import execute_update_job
from backend.core.jobs.update.update_job_plan_builder import UpdateJobPlan
from backend.enums.hook_name_enum import EHookName
from shared.agent_protocol import AGENT_UPGRADE_MESSAGE, AgentProtocol
from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import RuntimeVersion
from shared.schemas.container_schemas import CreateContainerRequestBodySchema

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
    client.public.version = AsyncMock(
        return_value=AgentProtocol(version="dev", protocol=2)
    )

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
        f"{base_module}.diff_container_config_with_image",
        return_value=MagicMock(),
    )
    mocker.patch(f"{base_module}.build_create_request", return_value=({}, None))
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


def _running(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        image="sha256:local",
        config=SimpleNamespace(image="nginx:latest"),
        state=SimpleNamespace(status="running", health=None),
    )


def _client() -> MagicMock:
    client = MagicMock()
    client.image.inspect = AsyncMock(return_value=MagicMock(id="sha256:local"))
    client.image.pull = AsyncMock(return_value=MagicMock(id="sha256:remote"))
    client.container.inspect = AsyncMock()
    client.container.stop = AsyncMock()
    client.container.remove = AsyncMock()
    client.container.start = AsyncMock()
    client.container.exists = AsyncMock(return_value=True)
    client.public.version = AsyncMock(
        return_value=AgentProtocol(version="dev", protocol=2)
    )
    return client


@pytest.mark.asyncio
async def test_preflight_failure_leaves_container_and_dependent(
    mocker: MockerFixture,
) -> None:
    web = _running("web")
    db = _running("db")
    client = _client()
    rollback = CreateContainerRequestBodySchema(image="nginx:old", name="web")
    merged = CreateContainerRequestBodySchema(image="nginx:new", name="web")
    seen: list[CreateContainerRequestBodySchema] = []

    def build(body, *, capabilities=None):
        assert capabilities is not None
        assert capabilities.runtime_type == "docker"
        assert capabilities.api_version == "1.44"
        seen.append(body)
        if body is merged:
            raise RuntimePreflightError(
                "VolumeOptions.Subpath requires Docker API >= 1.45, "
                "but the target API is 1.44"
            )
        return {}, None

    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)
    mocker.patch(f"{base_module}.asyncio.sleep", new=AsyncMock())
    mocker.patch(f"{base_module}.Config.ALLOW_HOOKS", False)
    mocker.patch(
        f"{base_module}.get_container_config",
        return_value=(rollback, []),
    )
    mocker.patch(
        f"{base_module}.diff_container_config_with_image",
        return_value=merged,
    )
    mocker.patch(f"{base_module}.build_create_request", side_effect=build)
    mocker.patch(
        f"{base_module}.update_containers_data_after_execution",
        new=AsyncMock(),
    )

    plan = UpdateJobPlan(
        to_update={"web"},
        affected={"db"},
        order=["web", "db"],
        healthcheck_timeouts={"web": 1, "db": 1},
    )
    results = await execute_update_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        [web, db],  # type: ignore[list-item]
        plan,
        docker_version=RuntimeVersion(negotiated_api="1.44"),
    )

    assert seen == [rollback, merged]
    client.container.stop.assert_not_called()
    client.container.remove.assert_not_called()
    client.container.start.assert_not_called()
    web_result = next(result for result in results if result.name == "web")
    assert web_result.result == "failed"
    assert web_result.error is not None
    assert "VolumeOptions.Subpath" in web_result.error


@pytest.mark.asyncio
async def test_protocol_mismatch_does_not_stop_or_remove() -> None:
    web = _running("web")
    client = _client()
    client.public.version = AsyncMock(
        return_value=AgentProtocol(version="1.0.0", protocol=1)
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
        [web],  # type: ignore[list-item]
        plan,
        docker_version=None,
    )

    client.container.stop.assert_not_called()
    client.container.remove.assert_not_called()
    client.image.pull.assert_not_called()
    assert results[0].result == "failed"
    assert results[0].error == AGENT_UPGRADE_MESSAGE
