from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)
from python_on_whales.components.image.models import ImageInspectResult

from backend.core.jobs.check.check_container import run_check_container_job
from backend.enums.job_status_enum import EJobStatus
from backend.testing import patch_async_session

base_module = "backend.core.jobs.check.check_container"


def _container(image: str | None = "nginx:latest") -> ContainerInspectResult:
    config = ContainerConfig(image=image) if image is not None else None
    return ContainerInspectResult(
        id="c1",
        name="web",
        image="sha256:local",
        config=config,
    )


def _local_image(digests: list[str] | None) -> ImageInspectResult:
    return ImageInspectResult(
        id="sha256:local",
        repo_digests=digests,
        config=ContainerConfig(labels={"org.opencontainers.image.version": "1.0.0"}),
    )


def _session(c_db: SimpleNamespace | None) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = c_db
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_check_container_exits_without_image_spec(
    mocker: MockerFixture,
) -> None:
    client = MagicMock()
    client.image.inspect = AsyncMock()
    tracker = MagicMock()
    patch_async_session(mocker, base_module, _session(None))

    result = await run_check_container_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        _container(image=None),
        tracker=tracker,
    )

    assert result.result is None
    client.image.inspect.assert_not_called()
    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
async def test_check_container_exits_without_repo_digests(
    mocker: MockerFixture,
) -> None:
    client = MagicMock()
    client.image.inspect = AsyncMock(return_value=_local_image([]))
    tracker = MagicMock()
    patch_async_session(mocker, base_module, _session(None))

    result = await run_check_container_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        _container(),
        tracker=tracker,
    )

    assert result.result is None
    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remote", "stored_remote", "expected", "update_available"),
    [
        ("sha256:new", None, "available", True),
        ("sha256:local", None, "not_available", False),
        ("sha256:new", ["sha256:new"], "available(notified)", True),
        (None, None, None, True),
    ],
)
async def test_check_container_digest_outcome(
    mocker: MockerFixture,
    remote: str | None,
    stored_remote: list[str] | None,
    expected: str | None,
    update_available: bool,
) -> None:
    client = MagicMock()
    client.image.inspect = AsyncMock(return_value=_local_image(["nginx@sha256:local"]))
    tracker = MagicMock()
    c_db = SimpleNamespace(
        update_available=True,
        remote_digests=stored_remote,
    )
    patch_async_session(mocker, base_module, _session(c_db))
    mocker.patch(f"{base_module}.asyncio.sleep", new=AsyncMock())
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)
    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        new=AsyncMock(return_value=remote),
    )
    mocker.patch(
        f"{base_module}.cache_available_image_metadata",
        new=AsyncMock(return_value=None),
    )
    insert = mocker.patch(
        f"{base_module}.insert_or_update_container",
        new=AsyncMock(),
    )

    result = await run_check_container_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        _container(),
        tracker=tracker,
    )

    assert result.result == expected
    assert insert.await_args.args[3]["update_available"] is update_available
    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
async def test_check_container_records_error_slot(mocker: MockerFixture) -> None:
    client = MagicMock()
    client.image.inspect = AsyncMock(side_effect=RuntimeError("inspect failed"))
    tracker = MagicMock()
    patch_async_session(mocker, base_module, _session(None))
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_container_job(
        client,
        SimpleNamespace(id=1, name="host"),  # type: ignore[arg-type]
        _container(),
        tracker=tracker,
    )

    assert result.result is None
    tracker.set_container.assert_called_with("web", EJobStatus.ERROR, result)
