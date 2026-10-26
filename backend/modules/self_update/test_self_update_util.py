import os
import stat
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import ImageInspectResult

from backend.exception import TugSelfUpdateError
from backend.modules.self_update import self_update_util
from backend.modules.self_update.self_update_util import (
    SelfUpdateStorage,
    cleanup_stale_old_container,
    get_data_mount,
    get_helper_config,
    get_helper_networks,
    get_sqlite_db_path,
    start_self_update,
    watch_self_update_result,
)
from backend.testing import patch_async_session
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.self_update.self_update_files import read_state, write_state
from shared.self_update.self_update_schemas import (
    SELF_UPDATE_PLAN_FILE,
    SELF_UPDATE_PLAN_VERSION,
    SELF_UPDATE_STATE_FILE,
    ESelfUpdateStatus,
    SelfUpdatePlan,
    SelfUpdateState,
)

base_module = "backend.modules.self_update.self_update_util"

SELF_ID = "a" * 64
OLD_IMAGE = "sha256:old"
NEW_IMAGE = "sha256:new"


def _container(
    network_mode: str = "tugtainer",
    networks: list[str] | None = None,
    mounts: list[dict] | None = None,
) -> ContainerInspectResult:
    return ContainerInspectResult.model_validate(
        {
            "id": SELF_ID,
            "name": "tugtainer",
            "image": OLD_IMAGE,
            "config": {"image": "ghcr.io/quenary/tugtainer:1", "labels": {}},
            "host_config": {"network_mode": network_mode},
            "network_settings": {
                "networks": {n: {} for n in (networks or ["tugtainer"])}
            },
            "mounts": mounts
            if mounts is not None
            else [
                {
                    "type": "volume",
                    "name": "tugtainer_data",
                    "source": "/var/lib/docker/volumes/tugtainer_data/_data",
                    "destination": "/tugtainer",
                }
            ],
        }
    )


def _version(api_version: str) -> DockerVersionScheme:
    return DockerVersionScheme.model_validate({"client": {"api_version": api_version}})


def _state(**kwargs) -> SelfUpdateState:
    return SelfUpdateState(
        **{
            "status": ESelfUpdateStatus.PENDING,
            "container_name": "tugtainer",
            "old_container_id": SELF_ID,
            "helper_container_name": "tugtainer-self-update",
            "old_image_id": OLD_IMAGE,
            "new_image_id": NEW_IMAGE,
            **kwargs,
        }
    )


@pytest.fixture
def work_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    path = tmp_path / "self_update"
    mocker.patch(f"{base_module}.SELF_UPDATE_DIR", str(path))
    return path


@pytest.fixture(autouse=True)
def reset_storage():
    SelfUpdateStorage.last_result = None
    SelfUpdateStorage.watch_task = None
    yield
    SelfUpdateStorage.last_result = None
    SelfUpdateStorage.watch_task = None


class TestGetHelperNetworks:
    @pytest.mark.parametrize("mode", ["host", "none", "container:abc"])
    def test_keeps_special_modes(self, mode: str) -> None:
        container = _container(network_mode=mode, networks=[])

        assert get_helper_networks(container, None) == [mode]

    def test_puts_primary_network_first(self) -> None:
        container = _container(network_mode="main", networks=["extra", "main"])

        assert get_helper_networks(container, _version("1.45")) == ["main", "extra"]

    def test_only_primary_network_on_old_api(self) -> None:
        container = _container(network_mode="main", networks=["extra", "main"])

        assert get_helper_networks(container, _version("1.43")) == ["main"]


class TestGetHelperConfig:
    def test_only_docker_access_and_data_volume(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DOCKER_HOST", "tcp://socket-proxy:2375")
        container = _container(
            mounts=[
                {
                    "type": "volume",
                    "name": "tugtainer_data",
                    "destination": "/tugtainer",
                },
                {
                    "type": "bind",
                    "source": "/var/run/docker.sock",
                    "destination": "/var/run/docker.sock",
                },
                {"type": "bind", "source": "/srv/other", "destination": "/other"},
            ]
        )

        config = get_helper_config(
            container,
            get_data_mount(container),
            NEW_IMAGE,
            "tugtainer-self-update",
            "/tugtainer/self_update/plan.json",
            None,
        )

        assert config.model_dump(exclude_unset=True) == {
            "image": NEW_IMAGE,
            "name": "tugtainer-self-update",
            "entrypoint": "python",
            "command": [
                "-m",
                "shared.self_update",
                "/tugtainer/self_update/plan.json",
            ],
            "workdir": "/app",
            "volumes": [
                ("tugtainer_data", "/tugtainer"),
                ("/var/run/docker.sock", "/var/run/docker.sock"),
            ],
            "envs": {"DOCKER_HOST": "tcp://socket-proxy:2375"},
            "networks": ["tugtainer"],
            "labels": {"dev.quenary.tugtainer.protected": "true"},
            "healthcheck": False,
            "remove": True,
        }

    def test_without_docker_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DOCKER_HOST", raising=False)
        container = _container()

        config = get_helper_config(
            container, get_data_mount(container), NEW_IMAGE, "h", "/p", None
        )

        assert config.envs is None


def test_get_data_mount_requires_volume() -> None:
    with pytest.raises(TugSelfUpdateError, match="not a volume"):
        get_data_mount(_container(mounts=[]))


@pytest.mark.parametrize(
    ("db_url", "expected"),
    [
        ("sqlite+aiosqlite:////tugtainer/tugtainer.db", "/tugtainer/tugtainer.db"),
        ("sqlite:////tugtainer/db/../tugtainer.db", "/tugtainer/tugtainer.db"),
        ("postgresql+psycopg2://u:p@db/tugtainer", None),
    ],
)
def test_get_sqlite_db_path(
    mocker: MockerFixture, db_url: str, expected: str | None
) -> None:
    mocker.patch(f"{base_module}.Config.DB_URL", db_url)

    assert get_sqlite_db_path() == expected


def test_get_sqlite_db_path_outside_data_dir(mocker: MockerFixture) -> None:
    mocker.patch(f"{base_module}.Config.DB_URL", "sqlite:////data/tugtainer.db")

    with pytest.raises(TugSelfUpdateError, match="outside"):
        get_sqlite_db_path()


class TestCleanupStaleOldContainer:
    @pytest.mark.parametrize(
        ("status", "old_id", "removed"),
        [
            (ESelfUpdateStatus.SUCCEEDED, SELF_ID, True),
            (ESelfUpdateStatus.SUCCEEDED, "b" * 64, False),
            (ESelfUpdateStatus.FAILED, SELF_ID, False),
            (ESelfUpdateStatus.RUNNING, SELF_ID, False),
        ],
    )
    @pytest.mark.asyncio
    async def test_removes_only_recorded_old(
        self,
        work_dir: Path,
        status: ESelfUpdateStatus,
        old_id: str,
        removed: bool,
    ) -> None:
        write_state(work_dir / SELF_UPDATE_STATE_FILE, _state(status=status))
        client = AsyncMock()
        client.container.exists = AsyncMock(return_value=True)
        client.container.inspect = AsyncMock(return_value=SimpleNamespace(id=old_id))

        await cleanup_stale_old_container(client, "tugtainer")

        assert client.container.remove.await_count == int(removed)

    @pytest.mark.asyncio
    async def test_noop_without_state(self, work_dir: Path) -> None:
        client = AsyncMock()

        await cleanup_stale_old_container(client, "tugtainer")

        client.container.exists.assert_not_called()


class TestStartSelfUpdate:
    @pytest.fixture
    def client(self, mocker: MockerFixture, work_dir: Path) -> AsyncMock:
        mocker.patch(f"{base_module}.Config.ALLOW_SELF_UPDATE", True)
        mocker.patch(
            f"{base_module}.Config.DB_URL",
            "sqlite+aiosqlite:////tugtainer/tugtainer.db",
        )
        mocker.patch(f"{base_module}.read_app_version", return_value="1.0.0")
        mocker.patch(f"{base_module}.start_self_update_watcher")
        session = patch_async_session(mocker, base_module)
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=None))
                )
            )
        )
        client = AsyncMock()
        client.container.exists = AsyncMock(return_value=False)
        client.image.inspect = AsyncMock(
            return_value=ImageInspectResult.model_validate(
                {"id": OLD_IMAGE, "config": {}}
            )
        )
        client.image.pull = AsyncMock(
            return_value=ImageInspectResult.model_validate(
                {
                    "id": NEW_IMAGE,
                    "config": {"labels": {"org.opencontainers.image.version": "1.1.0"}},
                }
            )
        )
        client.common.version = AsyncMock(return_value=None)
        host = SimpleNamespace(id=1, name="local", container_hc_timeout=90)
        mocker.patch(
            f"{base_module}.find_self",
            new=AsyncMock(return_value=(host, client, _container())),
        )
        return client

    @pytest.mark.asyncio
    async def test_writes_plan_and_starts_helper(
        self, client: AsyncMock, work_dir: Path
    ) -> None:
        state = await start_self_update()

        assert state.status == ESelfUpdateStatus.PENDING
        assert state.new_version == "1.1.0"
        assert read_state(work_dir / SELF_UPDATE_STATE_FILE) == state

        plan_path = work_dir / SELF_UPDATE_PLAN_FILE
        assert stat.S_IMODE(os.stat(plan_path).st_mode) == 0o600
        plan = SelfUpdatePlan.model_validate_json(plan_path.read_text())
        assert plan.version == SELF_UPDATE_PLAN_VERSION
        assert plan.container_id == SELF_ID
        assert plan.new_image_id == NEW_IMAGE
        assert plan.create.name == "tugtainer"
        assert plan.create.image == "ghcr.io/quenary/tugtainer:1"
        assert plan.healthcheck_timeout == 90
        assert plan.db_path == "/tugtainer/tugtainer.db"

        helper = client.container.create.await_args.args[0]
        assert helper.name == "tugtainer-self-update"
        assert helper.image == NEW_IMAGE
        client.container.start.assert_awaited_once_with("tugtainer-self-update")

    @pytest.mark.asyncio
    async def test_refuses_same_image(self, client: AsyncMock, work_dir: Path) -> None:
        client.image.pull.return_value = ImageInspectResult.model_validate(
            {"id": OLD_IMAGE}
        )

        with pytest.raises(TugSelfUpdateError, match="No newer image"):
            await start_self_update()

        assert not (work_dir / SELF_UPDATE_PLAN_FILE).exists()
        client.container.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_refuses_while_in_progress(
        self, client: AsyncMock, work_dir: Path
    ) -> None:
        write_state(
            work_dir / SELF_UPDATE_STATE_FILE,
            _state(status=ESelfUpdateStatus.RUNNING),
        )

        with pytest.raises(TugSelfUpdateError, match="in progress"):
            await start_self_update()

    @pytest.mark.asyncio
    async def test_refuses_existing_old_container(self, client: AsyncMock) -> None:
        client.container.exists = AsyncMock(
            side_effect=lambda name: name == "tugtainer-old"
        )

        with pytest.raises(TugSelfUpdateError, match="tugtainer-old already exists"):
            await start_self_update()

        client.image.pull.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleans_up_when_helper_fails(
        self, client: AsyncMock, work_dir: Path
    ) -> None:
        client.container.start = AsyncMock(side_effect=Exception("boom"))
        client.container.exists = AsyncMock(
            side_effect=lambda name: (
                name == "tugtainer-self-update"
                and client.container.create.await_count > 0
            )
        )

        with pytest.raises(Exception, match="boom"):
            await start_self_update()

        assert not (work_dir / SELF_UPDATE_PLAN_FILE).exists()
        assert not (work_dir / SELF_UPDATE_STATE_FILE).exists()
        client.container.remove.assert_awaited_once_with("tugtainer-self-update")

    @pytest.mark.asyncio
    async def test_disabled(self, mocker: MockerFixture) -> None:
        mocker.patch(f"{base_module}.Config.ALLOW_SELF_UPDATE", False)

        with pytest.raises(TugSelfUpdateError, match="disabled"):
            await start_self_update()


class TestWatchSelfUpdateResult:
    @pytest.mark.asyncio
    async def test_reports_final_result_once(
        self, mocker: MockerFixture, work_dir: Path
    ) -> None:
        state = _state(status=ESelfUpdateStatus.ROLLED_BACK, error="unhealthy")
        write_state(work_dir / SELF_UPDATE_STATE_FILE, state)
        report = mocker.patch(f"{base_module}._report_result", new=AsyncMock())

        await watch_self_update_result()

        report.assert_awaited_once_with(state)
        assert SelfUpdateStorage.last_result == state
        assert not (work_dir / SELF_UPDATE_STATE_FILE).exists()
        assert self_update_util.get_current_state() == state

    @pytest.mark.asyncio
    async def test_waits_for_running_helper(
        self, mocker: MockerFixture, work_dir: Path
    ) -> None:
        path = work_dir / SELF_UPDATE_STATE_FILE
        write_state(path, _state(status=ESelfUpdateStatus.RUNNING))
        final = _state(status=ESelfUpdateStatus.SUCCEEDED)

        async def _finish(_):
            write_state(path, final)

        mocker.patch(f"{base_module}._is_helper_running", return_value=True)
        mocker.patch(f"{base_module}.asyncio.sleep", side_effect=_finish)
        report = mocker.patch(f"{base_module}._report_result", new=AsyncMock())
        cleanup = mocker.patch(
            f"{base_module}.cleanup_stale_old_container", new=AsyncMock()
        )
        mocker.patch(
            f"{base_module}.find_self",
            new=AsyncMock(return_value=(None, AsyncMock(), None)),
        )

        await watch_self_update_result()

        report.assert_awaited_once_with(final)
        cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_marks_interrupted_when_helper_gone(
        self, mocker: MockerFixture, work_dir: Path
    ) -> None:
        write_state(
            work_dir / SELF_UPDATE_STATE_FILE,
            _state(status=ESelfUpdateStatus.RUNNING),
        )
        mocker.patch(f"{base_module}._is_helper_running", return_value=False)
        report = mocker.patch(f"{base_module}._report_result", new=AsyncMock())

        await watch_self_update_result()

        reported = report.await_args.args[0]
        assert reported.status == ESelfUpdateStatus.INTERRUPTED
        assert reported.finished_at is not None

    @pytest.mark.asyncio
    async def test_noop_without_state(
        self, mocker: MockerFixture, work_dir: Path
    ) -> None:
        report = mocker.patch(f"{base_module}._report_result", new=AsyncMock())

        await watch_self_update_result()

        report.assert_not_called()


def test_format_result_mentions_versions_and_error() -> None:
    title, body = self_update_util._format_result(
        _state(
            status=ESelfUpdateStatus.ROLLED_BACK,
            old_version="1.0.0",
            new_version="1.1.0",
            error="tugtainer is unhealthy",
        )
    )

    assert title == "Tugtainer self-update rolled back"
    assert "tugtainer: 1.0.0 -> 1.1.0" in body
    assert "Error: tugtainer is unhealthy" in body
