from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import backend.modules.containers.containers_model  # noqa: F401
import backend.modules.health.health_model  # noqa: F401
from backend.core.jobs.check.check_service import run_check_service_job
from backend.enums.job_status_enum import EJobStatus
from shared.schemas.service_schemas import ServiceListItemSchema, ServiceReplicasSchema

base_module = "backend.core.jobs.check.check_service"


def _make_service(
    name: str = "web",
    image: str = "nginx:alpine",
    service_id: str = "svc-123",
) -> ServiceListItemSchema:
    return ServiceListItemSchema(
        id=service_id,
        name=name,
        image=image,
        mode="replicated",
        replicas=ServiceReplicasSchema(running=1, desired=1),
    )


@pytest.fixture
def mock_session(mocker: MockerFixture):
    session = MagicMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_execute_result)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
    return session


@pytest.mark.asyncio
async def test_check_service_missing_image(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = _make_service(image="")

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
async def test_check_service_local_image_update_available(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = _make_service(name="web", image="nginx:alpine")

    # Local inspect succeeds with repo digests
    local_img = MagicMock()
    local_img.id = "sha256:local123"
    local_img.repo_digests = ["nginx@sha256:old_digest"]
    client.image.inspect = AsyncMock(return_value=local_img)

    # Remote digest differs
    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value="sha256:new_digest"),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert result.result == "available"
    assert result.local_digests == ["nginx@sha256:old_digest"]
    assert result.remote_digests == ["sha256:new_digest"]
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_check_service_local_image_not_available(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    service = _make_service(name="web", image="nginx:alpine")

    local_img = MagicMock()
    local_img.id = "sha256:local123"
    local_img.repo_digests = ["nginx@sha256:current_digest"]
    client.image.inspect = AsyncMock(return_value=local_img)

    # Remote digest matches local
    mocker.patch(
        f"{base_module}.get_image_remote_digest",
        AsyncMock(return_value="sha256:current_digest"),
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    result = await run_check_service_job(
        client,
        host,  # type: ignore[arg-type]
        service,
        tracker=tracker,
    )

    assert result.result == "not_available"
    assert result.remote_digests == ["sha256:current_digest"]


@pytest.mark.asyncio
async def test_check_service_pinned_digest_when_image_not_on_manager(
    mocker: MockerFixture, mock_session: MagicMock
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    tracker = MagicMock()
    # Image in service spec contains pinned digest from Swarm
    service = _make_service(
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
    service = _make_service(name="web", image="local-custom-app:latest")

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
    service = _make_service(name="web", image="nginx:alpine")

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
