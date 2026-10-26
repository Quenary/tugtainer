import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import ContainerInspectResult

from shared.schemas.container_schemas import CreateContainerRequestBodySchema
from shared.self_update.self_update_files import read_state, write_state
from shared.self_update.self_update_runner import (
    SelfUpdateAbort,
    load_plan,
    run_self_update,
)
from shared.self_update.self_update_schemas import (
    SELF_UPDATE_PLAN_FILE,
    SELF_UPDATE_PLAN_VERSION,
    SELF_UPDATE_STATE_FILE,
    ESelfUpdatePhase,
    ESelfUpdateStatus,
    SelfUpdatePlan,
    SelfUpdateState,
)

base_module = "shared.self_update.self_update_runner"

OLD_ID = "old" + "0" * 61
NEW_ID = "new" + "0" * 61
OLD_IMAGE = "sha256:old"
NEW_IMAGE = "sha256:new"
NAME = "tugtainer"


class FakeDocker:
    """In-memory SelfUpdateDocker, fails on the operations listed in fail_on."""

    def __init__(self, fail_on: set[str] | None = None):
        self.fail_on = fail_on or set()
        self.calls: list[tuple[str, ...]] = []
        self.containers: dict[str, dict] = {
            OLD_ID: {"name": NAME, "image": OLD_IMAGE, "status": "running"}
        }
        self.images = {OLD_IMAGE, NEW_IMAGE}
        self.health = "healthy"

    def _call(self, op: str, *args: str) -> None:
        self.calls.append((op, *args))
        if op in self.fail_on:
            raise Exception(f"{op} failed")

    def _find(self, name_or_id: str) -> str:
        for id, c in self.containers.items():
            if name_or_id in (id, c["name"]):
                return id
        raise Exception(f"No such container {name_or_id}")

    def inspect(self, name_or_id: str) -> ContainerInspectResult:
        self._call("inspect", name_or_id)
        id = self._find(name_or_id)
        c = self.containers[id]
        health = SimpleNamespace(status=self.health) if id == NEW_ID else None
        return cast(
            ContainerInspectResult,
            SimpleNamespace(
                id=id,
                name=c["name"],
                image=c["image"],
                state=SimpleNamespace(status=c["status"], health=health),
            ),
        )

    def exists(self, name_or_id: str) -> bool:
        try:
            self._find(name_or_id)
            return True
        except Exception:
            return False

    def image_exists(self, image_id: str) -> bool:
        return image_id in self.images

    def rename(self, name_or_id: str, new_name: str) -> None:
        self._call("rename", name_or_id, new_name)
        if self.exists(new_name):
            raise Exception(f"Name {new_name} is in use")
        self.containers[self._find(name_or_id)]["name"] = new_name

    def create(self, body: CreateContainerRequestBodySchema) -> str:
        self._call("create", str(body.name))
        if self.exists(str(body.name)):
            raise Exception(f"Name {body.name} is in use")
        self.containers[NEW_ID] = {
            "name": body.name,
            "image": NEW_IMAGE,
            "status": "created",
        }
        return NEW_ID

    def start(self, name_or_id: str) -> None:
        self._call("start", name_or_id)
        self.containers[self._find(name_or_id)]["status"] = "running"

    def stop(self, name_or_id: str) -> None:
        self._call("stop", name_or_id)
        self.containers[self._find(name_or_id)]["status"] = "exited"

    def remove(self, name_or_id: str) -> None:
        self._call("remove", name_or_id)
        del self.containers[self._find(name_or_id)]

    def run(self, command: list[str]) -> None:
        self._call("run", *command)


def _plan(db_path: Path | None = None, healthcheck_timeout: int = 30) -> SelfUpdatePlan:
    return SelfUpdatePlan(
        version=SELF_UPDATE_PLAN_VERSION,
        container_id=OLD_ID,
        container_name=NAME,
        old_image_id=OLD_IMAGE,
        new_image_id=NEW_IMAGE,
        old_version="1.0.0",
        new_version="1.1.0",
        create=CreateContainerRequestBodySchema(image="repo/tugtainer:1", name=NAME),
        commands=[["network", "connect", "extra", NAME]],
        healthcheck_timeout=healthcheck_timeout,
        db_path=str(db_path) if db_path else None,
    )


def _pending_state() -> SelfUpdateState:
    return SelfUpdateState(
        status=ESelfUpdateStatus.PENDING,
        container_name=NAME,
        old_container_id=OLD_ID,
        helper_container_name=f"{NAME}-self-update",
        old_image_id=OLD_IMAGE,
        new_image_id=NEW_IMAGE,
    )


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    path = tmp_path / "self_update"
    path.mkdir()
    return path


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db = tmp_path / "tugtainer.db"
    db.write_text("db-before")
    db.with_name("tugtainer.db-wal").write_text("wal-before")
    return db


@pytest.fixture(autouse=True)
def no_health_sleep(mocker: MockerFixture) -> None:
    mocker.patch("shared.util.wait_for_container_healthy.asyncio.sleep")


def _prepare(
    work_dir: Path, plan: SelfUpdatePlan, state: SelfUpdateState | None = None
) -> Path:
    plan_path = work_dir / SELF_UPDATE_PLAN_FILE
    plan_path.write_text(plan.model_dump_json(exclude_unset=True))
    write_state(work_dir / SELF_UPDATE_STATE_FILE, state or _pending_state())
    return plan_path


def _phases(state: SelfUpdateState) -> list[ESelfUpdatePhase]:
    return [e.phase for e in state.journal]


class TestLoadPlan:
    def test_deletes_plan_after_reading(self, work_dir: Path) -> None:
        plan_path = _prepare(work_dir, _plan())

        plan = load_plan(plan_path)

        assert plan.container_id == OLD_ID
        assert not plan_path.exists()

    @pytest.mark.parametrize(
        "content",
        [
            "not json",
            json.dumps({"version": SELF_UPDATE_PLAN_VERSION + 1}),
            json.dumps({"container_id": OLD_ID}),
            json.dumps({"version": SELF_UPDATE_PLAN_VERSION}),
        ],
    )
    def test_refuses_invalid_plan(self, work_dir: Path, content: str) -> None:
        plan_path = work_dir / SELF_UPDATE_PLAN_FILE
        plan_path.write_text(content)

        with pytest.raises(SelfUpdateAbort):
            load_plan(plan_path)
        assert not plan_path.exists()


class TestRunSelfUpdate:
    def test_success(self, work_dir: Path, db_path: Path) -> None:
        docker = FakeDocker()
        plan_path = _prepare(work_dir, _plan(db_path))

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.SUCCEEDED
        assert state.new_container_id == NEW_ID
        assert _phases(state) == [
            ESelfUpdatePhase.OLD_RENAMED,
            ESelfUpdatePhase.NEW_CREATED,
            ESelfUpdatePhase.OLD_STOPPED,
            ESelfUpdatePhase.DB_SNAPSHOT,
            ESelfUpdatePhase.NEW_STARTED,
            ESelfUpdatePhase.NEW_HEALTHY,
            ESelfUpdatePhase.OLD_REMOVED,
        ]
        assert docker.containers == {
            NEW_ID: {"name": NAME, "image": NEW_IMAGE, "status": "running"}
        }
        assert ("run", "network", "connect", "extra", NAME) in docker.calls
        assert read_state(work_dir / SELF_UPDATE_STATE_FILE) == state
        assert not (work_dir / "backup").exists()

    def test_state_file_is_private(self, work_dir: Path) -> None:
        plan_path = _prepare(work_dir, _plan())

        run_self_update(FakeDocker(), plan_path)

        mode = os.stat(work_dir / SELF_UPDATE_STATE_FILE).st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_old_kept_when_remove_fails(self, work_dir: Path) -> None:
        docker = FakeDocker(fail_on={"remove"})
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.SUCCEEDED
        assert ESelfUpdatePhase.OLD_REMOVED not in _phases(state)
        assert state.warnings
        assert docker.containers[OLD_ID]["name"] == f"{NAME}-old"

    @pytest.mark.parametrize(
        ("change", "message"),
        [
            ({"name": "other"}, "named other"),
            ({"image": "sha256:other"}, "runs image"),
        ],
    )
    def test_aborts_when_container_changed(
        self, work_dir: Path, change: dict, message: str
    ) -> None:
        docker = FakeDocker()
        docker.containers[OLD_ID].update(change)
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ABORTED
        assert message in str(state.error)
        assert not [c for c in docker.calls if c[0] != "inspect"]

    def test_aborts_when_old_name_taken(self, work_dir: Path) -> None:
        docker = FakeDocker()
        docker.containers["x" * 64] = {
            "name": f"{NAME}-old",
            "image": OLD_IMAGE,
            "status": "exited",
        }
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ABORTED
        assert len(docker.containers) == 2

    def test_aborts_on_unknown_plan_version(self, work_dir: Path) -> None:
        docker = FakeDocker()
        plan_path = _prepare(work_dir, _plan())
        plan_path.write_text(json.dumps({"version": 99}))

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ABORTED
        assert "version 99" in str(state.error)
        assert docker.calls == []

    def test_requires_pending_state(self, work_dir: Path) -> None:
        docker = FakeDocker()
        state = _pending_state()
        state.status = ESelfUpdateStatus.SUCCEEDED
        plan_path = _prepare(work_dir, _plan(), state)

        result = run_self_update(docker, plan_path)

        assert result is not None
        assert result.status == ESelfUpdateStatus.SUCCEEDED
        assert docker.calls == []

    def test_rolls_back_unhealthy(self, work_dir: Path, db_path: Path) -> None:
        docker = FakeDocker()
        docker.health = "unhealthy"
        # Skip the wait loop, the final attempt decides
        plan_path = _prepare(work_dir, _plan(db_path, healthcheck_timeout=0))
        original_start = docker.start

        def start_and_migrate(name_or_id: str) -> None:
            original_start(name_or_id)
            if name_or_id == NEW_ID:
                db_path.write_text("db-migrated")
                db_path.with_name("tugtainer.db-wal").unlink()
                db_path.with_name("tugtainer.db-shm").write_text("shm-new")

        docker.start = start_and_migrate  # type: ignore[method-assign]

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ROLLED_BACK
        assert "unhealthy" in str(state.error)
        assert _phases(state)[-4:] == [
            ESelfUpdatePhase.NEW_REMOVED,
            ESelfUpdatePhase.DB_RESTORED,
            ESelfUpdatePhase.OLD_RENAMED_BACK,
            ESelfUpdatePhase.OLD_STARTED,
        ]
        assert docker.containers == {
            OLD_ID: {"name": NAME, "image": OLD_IMAGE, "status": "running"}
        }
        assert db_path.read_text() == "db-before"
        assert db_path.with_name("tugtainer.db-wal").read_text() == "wal-before"
        assert not db_path.with_name("tugtainer.db-shm").exists()

    def test_rolls_back_failed_create_without_restart(self, work_dir: Path) -> None:
        docker = FakeDocker(fail_on={"create"})
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ROLLED_BACK
        assert _phases(state) == [
            ESelfUpdatePhase.OLD_RENAMED,
            ESelfUpdatePhase.OLD_RENAMED_BACK,
        ]
        assert docker.containers[OLD_ID] == {
            "name": NAME,
            "image": OLD_IMAGE,
            "status": "running",
        }
        assert not [c for c in docker.calls if c[0] in ("stop", "start")]

    def test_failed_when_rollback_fails(self, work_dir: Path) -> None:
        docker = FakeDocker(fail_on={"start", "remove"})
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.FAILED
        assert state.warnings
        assert state.finished_at is not None

    def test_rollback_stops_when_new_cannot_be_removed(
        self, work_dir: Path, db_path: Path
    ) -> None:
        docker = FakeDocker(fail_on={"remove"})
        docker.health = "unhealthy"
        plan_path = _prepare(work_dir, _plan(db_path, healthcheck_timeout=0))
        original_start = docker.start

        def start_and_migrate(name_or_id: str) -> None:
            original_start(name_or_id)
            if name_or_id == NEW_ID:
                db_path.write_text("db-migrated")

        docker.start = start_and_migrate  # type: ignore[method-assign]

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.FAILED
        assert ESelfUpdatePhase.DB_RESTORED not in _phases(state)
        assert ESelfUpdatePhase.OLD_RENAMED_BACK not in _phases(state)
        # The running new container keeps its database, the copy stays
        assert db_path.read_text() == "db-migrated"
        assert (work_dir / "backup" / "tugtainer.db").read_text() == "db-before"
        assert docker.containers[OLD_ID]["name"] == f"{NAME}-old"

    def test_rollback_does_not_restart_running_old(self, work_dir: Path) -> None:
        docker = FakeDocker(fail_on={"stop"})
        plan_path = _prepare(work_dir, _plan())

        state = run_self_update(docker, plan_path)

        assert state is not None
        assert state.status == ESelfUpdateStatus.ROLLED_BACK
        assert ESelfUpdatePhase.OLD_STARTED not in _phases(state)
        assert ("start", OLD_ID) not in docker.calls
        assert docker.containers == {
            OLD_ID: {"name": NAME, "image": OLD_IMAGE, "status": "running"}
        }
