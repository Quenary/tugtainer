from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.const import TUGTAINER_HIDDEN_LABEL
from backend.core.jobs.update.update_host import run_update_host_job

base_module = "backend.core.jobs.update.update_host"


@pytest.mark.asyncio
async def test_run_update_host_job_skips_hidden(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="host", prune=False)
    client = MagicMock()
    client.common.version = AsyncMock(return_value=None)
    visible = ContainerInspectResult(id="a", name="visible")
    hidden = ContainerInspectResult(
        id="b",
        name="hidden",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "yes"}),
    )
    client.container.list = AsyncMock(return_value=[visible, hidden])

    seen: dict[str, list[str]] = {}

    async def fake_plan(_host, containers, manual_for):
        seen["containers"] = [c.name for c in containers]
        seen["manual"] = [c.name for c in manual_for]
        return SimpleNamespace()

    mocker.patch(f"{base_module}.build_update_job_plan", side_effect=fake_plan)
    mocker.patch(f"{base_module}.execute_update_job", AsyncMock())

    ok = await run_update_host_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
    )

    assert ok is True
    assert seen["containers"] == ["visible"]
    assert seen["manual"] == ["visible"]
