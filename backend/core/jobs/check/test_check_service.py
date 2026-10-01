from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import backend.modules.containers.containers_model  # noqa: F401
import backend.modules.health.health_model  # noqa: F401
from backend.core.jobs.check.check_service import run_check_service_job
from backend.enums.job_status_enum import EJobStatus
from backend.testing import make_service, patch_async_session

base_module = "backend.core.jobs.check.check_service"


@pytest.fixture
def mock_session(mocker: MockerFixture):
    session = MagicMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_execute_result)

    patch_async_session(mocker, base_module, session)
    mocker.patch(
        f"{base_module}.cache_available_image_metadata",
        AsyncMock(return_value=None),
    )
    return session


@pytest.mark.asyncio
async def test_check_service_missing_image(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = make_service(image="")

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert result.result is None
    assert result.local_digests == []
    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("local_digest", "remote_digest", "expected"),
    [
        ("nginx@sha256:old_digest", "sha256:new_digest", "available"),
        ("nginx@sha256:current_digest", "sha256:current_digest", "not_available"),
    ],
)
async def test_check_service_local_image_digest_outcome(
    mocker: MockerFixture,
    mock_session: MagicMock,
    local_digest: str,
    remote_digest: str,
    expected: str,
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = make_service(name="web", image="nginx:alpine")

    local_img = MagicMock()
    local_img.id = "sha256:local123"
    local_img.repo_digests = [local_digest]
    client.image.inspect = AsyncMock(return_value=local_img)

    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value=remote_digest),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert result.result == expected
    assert result.local_digests == [local_digest]
    assert result.remote_digests == [remote_digest]
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_check_service_records_resolved_available_version(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    service = make_service(name="web", image="nginx:alpine")
    local_img = MagicMock()
    local_img.id = "sha256:local123"
    local_img.repo_digests = ["nginx@sha256:old_digest"]
    local_img.config = SimpleNamespace(
        labels={"org.opencontainers.image.version": "2.3.6"}
    )
    client.image.inspect = AsyncMock(return_value=local_img)
    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value="sha256:new_digest"),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)
    created = datetime(2024, 5, 1)
    cache = mocker.patch(
        f"{base_module}.cache_available_image_metadata",
        AsyncMock(return_value=SimpleNamespace(version="2.3.7", created=created)),
    )

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
    )

    assert result.current_version == "2.3.6"
    assert result.available_version == "2.3.7"
    assert result.available_created == created
    cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_service_pinned_digest_when_image_not_on_manager(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    # Image in service spec contains pinned digest from Swarm
    service = make_service(
        name="web",
        image="nginx:alpine@sha256:pinned_digest_abc",
    )

    # Manager does not have the image locally
    client.image.inspect = AsyncMock(side_effect=Exception("Image not found"))
    client.image.pull = AsyncMock()

    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value="sha256:new_remote_digest"),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    # Should NOT have pulled image to manager
    client.image.pull.assert_not_called()
    assert result.result == "available"
    assert result.local_digests == ["sha256:pinned_digest_abc"]
    assert result.remote_digests == ["sha256:new_remote_digest"]


@pytest.mark.asyncio
async def test_check_service_local_image_without_digests_exits_early(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = make_service(name="web", image="local-custom-app:latest")

    # Local image exists but has no repo digests (built locally)
    local_img = MagicMock()
    local_img.id = "sha256:local123"
    local_img.repo_digests = []
    client.image.inspect = AsyncMock(return_value=local_img)

    remote_digest_mock = mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    # Exits early as local image, no remote check performed
    remote_digest_mock.assert_not_called()
    assert result.result is None
    assert result.local_digests == []
    tracker.set_container.assert_called_with("web", EJobStatus.DONE, result)


@pytest.mark.asyncio
async def test_check_service_pull_before_check(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = make_service(name="web", image="nginx:alpine")

    # Image not cached on manager initially
    client.image.inspect = AsyncMock(side_effect=Exception("Not found"))

    # PULL_BEFORE_CHECK is enabled
    def settings_mock(key):
        if (
            str(key) == "PULL_BEFORE_CHECK"
            or getattr(key, "value", None) == "pull_before_check"
        ):
            return True
        return 0

    mocker.patch(f"{base_module}.SettingsStorage.get", side_effect=settings_mock)

    pulled_img = MagicMock()
    pulled_img.id = "sha256:pulled123"
    pulled_img.repo_digests = ["nginx@sha256:pulled_digest"]
    client.image.pull = AsyncMock(return_value=pulled_img)

    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value="sha256:new_remote"),
    )

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert client.image.pull.called
    assert result.result == "available"
    assert result.local_digests == ["nginx@sha256:pulled_digest"]
