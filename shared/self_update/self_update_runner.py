import asyncio
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from shared.util.wait_for_container_healthy import wait_for_container_healthy

from .self_update_docker import SelfUpdateDocker
from .self_update_files import read_state, write_state
from .self_update_schemas import (
    SELF_UPDATE_BACKUP_DIR,
    SELF_UPDATE_OLD_SUFFIX,
    SELF_UPDATE_PLAN_VERSION,
    SELF_UPDATE_STATE_FILE,
    SQLITE_SIDE_SUFFIXES,
    ESelfUpdatePhase,
    ESelfUpdateStatus,
    SelfUpdateJournalEntry,
    SelfUpdatePlan,
    SelfUpdateState,
)

logger: Final = logging.getLogger("self_update")


class SelfUpdateAbort(Exception):
    """Refuse to run before any container was touched."""


def load_plan(plan_path: Path) -> SelfUpdatePlan:
    """
    Read the plan and delete it right away.
    :raises SelfUpdateAbort: if the plan is missing, unreadable
    or of an unknown version
    """
    try:
        content = plan_path.read_text()
    except OSError as e:
        raise SelfUpdateAbort(f"Cannot read plan {plan_path}: {e}") from e
    finally:
        plan_path.unlink(missing_ok=True)
    try:
        data = json.loads(content)
    except ValueError as e:
        raise SelfUpdateAbort(f"Plan is not valid JSON: {e}") from e
    version = data.get("version") if isinstance(data, dict) else None
    if version != SELF_UPDATE_PLAN_VERSION:
        raise SelfUpdateAbort(
            f"Unsupported plan version {version}, expected {SELF_UPDATE_PLAN_VERSION}"
        )
    try:
        return SelfUpdatePlan.model_validate(data)
    except ValidationError as e:
        raise SelfUpdateAbort(f"Invalid plan: {e}") from e


class SelfUpdateRunner:
    """
    Execute a self-update plan:
    rename old to <name>-old, create new under the real name, stop old,
    snapshot the database, start new and wait for health.
    The old container is only stopped until the new one is healthy.
    Every step is recorded in the state file, so a rollback
    (or a later cleanup) knows exactly what has been done.
    """

    def __init__(
        self,
        docker: SelfUpdateDocker,
        plan: SelfUpdatePlan,
        work_dir: Path,
        state: SelfUpdateState,
        health_interval: float = 5,
    ):
        self._docker = docker
        self._plan = plan
        self._work_dir = work_dir
        self._state_path = work_dir / SELF_UPDATE_STATE_FILE
        self._backup_dir = work_dir / SELF_UPDATE_BACKUP_DIR
        self._state = state
        self._health_interval = health_interval
        self._old_name = f"{plan.container_name}{SELF_UPDATE_OLD_SUFFIX}"

    @property
    def state(self) -> SelfUpdateState:
        return self._state

    def _save(self) -> None:
        write_state(self._state_path, self._state)

    def _record(self, phase: ESelfUpdatePhase) -> None:
        logger.info(f"Phase: {phase}")
        self._state.journal.append(SelfUpdateJournalEntry(phase=phase))
        self._save()

    def _finish(self, status: ESelfUpdateStatus, error: str | None = None) -> None:
        self._state.status = status
        if error:
            self._state.error = error
        self._state.finished_at = datetime.now(UTC)
        self._save()
        logger.info(f"Self-update finished with status {status}")

    def run(self) -> SelfUpdateState:
        self._state.status = ESelfUpdateStatus.RUNNING
        self._save()
        try:
            self._precheck()
        except Exception as e:
            logger.exception("Self-update aborted")
            self._finish(ESelfUpdateStatus.ABORTED, str(e))
            return self._state
        try:
            self._swap()
        except Exception as e:
            logger.exception("Self-update failed, rolling back")
            self._state.error = str(e)
            self._save()
            self._rollback()
            return self._state
        self._cleanup_after_success()
        self._finish(ESelfUpdateStatus.SUCCEEDED)
        return self._state

    def _precheck(self) -> None:
        plan = self._plan
        old = self._docker.inspect(plan.container_id)
        if old.id != plan.container_id:
            raise SelfUpdateAbort(f"Container {plan.container_id} not found")
        if old.name != plan.container_name:
            raise SelfUpdateAbort(
                f"Container is named {old.name}, expected {plan.container_name}"
            )
        if old.image != plan.old_image_id:
            raise SelfUpdateAbort(
                f"Container runs image {old.image}, expected {plan.old_image_id}"
            )
        if not self._docker.image_exists(plan.new_image_id):
            raise SelfUpdateAbort(f"Image {plan.new_image_id} not found")
        if self._docker.exists(self._old_name):
            raise SelfUpdateAbort(f"Container {self._old_name} already exists")

    def _swap(self) -> None:
        plan = self._plan

        logger.info(f"Renaming {plan.container_name} to {self._old_name}")
        self._docker.rename(plan.container_id, self._old_name)
        self._record(ESelfUpdatePhase.OLD_RENAMED)

        logger.info(f"Creating {plan.container_name}")
        self._state.new_container_id = self._docker.create(plan.create)
        self._record(ESelfUpdatePhase.NEW_CREATED)

        logger.info(f"Stopping {self._old_name}")
        self._docker.stop(plan.container_id)
        self._record(ESelfUpdatePhase.OLD_STOPPED)

        if plan.db_path:
            self._snapshot_db(Path(plan.db_path))
            self._record(ESelfUpdatePhase.DB_SNAPSHOT)

        new_id = self._state.new_container_id
        logger.info(f"Starting {plan.container_name}")
        self._docker.start(new_id)
        self._record(ESelfUpdatePhase.NEW_STARTED)
        for command in plan.commands:
            logger.info(f"Running command: {command}")
            self._docker.run(command)

        logger.info("Waiting for healthchecks...")
        healthy, _ = asyncio.run(
            wait_for_container_healthy(
                self._inspect_async,
                self._docker.inspect(new_id),
                plan.healthcheck_timeout,
                self._health_interval,
            )
        )
        if not healthy:
            raise Exception(f"{plan.container_name} is unhealthy")
        self._record(ESelfUpdatePhase.NEW_HEALTHY)

    async def _inspect_async(self, name_or_id: str):
        return await asyncio.to_thread(self._docker.inspect, name_or_id)

    def _cleanup_after_success(self) -> None:
        try:
            logger.info(f"Removing {self._old_name}")
            self._docker.remove(self._plan.container_id)
            self._record(ESelfUpdatePhase.OLD_REMOVED)
        except Exception as e:
            # The backend removes it later, as its id is recorded
            logger.exception(f"Failed to remove {self._old_name}")
            self._state.warnings.append(f"Failed to remove {self._old_name}: {e}")
        shutil.rmtree(self._backup_dir, ignore_errors=True)

    def _rollback(self) -> None:
        plan = self._plan
        state = self._state
        errors: list[str] = []

        def _step(phase: ESelfUpdatePhase, description: str, func) -> bool:
            try:
                logger.warning(description)
                func()
                self._record(phase)
                return True
            except Exception as e:
                logger.exception(f"Rollback step failed: {description}")
                errors.append(f"{description}: {e}")
                return False

        def _rollback_steps() -> None:
            if state.has_phase(ESelfUpdatePhase.NEW_CREATED) and state.new_container_id:
                new_id = state.new_container_id
                if not _step(
                    ESelfUpdatePhase.NEW_REMOVED,
                    f"Removing new container {new_id}",
                    lambda: self._docker.remove(new_id),
                ):
                    # It may still use the database, the name and the ports
                    return
            if state.has_phase(ESelfUpdatePhase.DB_SNAPSHOT) and plan.db_path:
                db_path = Path(plan.db_path)
                if not _step(
                    ESelfUpdatePhase.DB_RESTORED,
                    "Restoring database snapshot",
                    lambda: self._restore_db(db_path),
                ):
                    # Do not start the old version on a migrated database
                    return
            if state.has_phase(ESelfUpdatePhase.OLD_RENAMED):
                _step(
                    ESelfUpdatePhase.OLD_RENAMED_BACK,
                    f"Renaming {self._old_name} back to {plan.container_name}",
                    lambda: self._docker.rename(plan.container_id, plan.container_name),
                )
            # Check the actual state, the stop may have failed half way
            old = self._docker.inspect(plan.container_id)
            if not (old.state and old.state.status == "running"):
                _step(
                    ESelfUpdatePhase.OLD_STARTED,
                    f"Starting {plan.container_name}",
                    lambda: self._docker.start(plan.container_id),
                )

        try:
            _rollback_steps()
        except Exception as e:
            logger.exception("Rollback failed")
            errors.append(str(e))

        if errors:
            state.warnings.extend(errors)
            self._finish(ESelfUpdateStatus.FAILED)
            return
        shutil.rmtree(self._backup_dir, ignore_errors=True)
        self._finish(ESelfUpdateStatus.ROLLED_BACK)

    def _db_files(self, db_path: Path) -> list[Path]:
        return [db_path] + [
            db_path.with_name(db_path.name + s) for s in SQLITE_SIDE_SUFFIXES
        ]

    def _snapshot_db(self, db_path: Path) -> None:
        """
        Copy the database files while no container uses them,
        as the new version runs its migrations on start.
        """
        shutil.rmtree(self._backup_dir, ignore_errors=True)
        self._backup_dir.mkdir(parents=True, mode=0o700)
        self._state.db_snapshot_files = []
        for file in self._db_files(db_path):
            if file.exists():
                shutil.copy2(file, self._backup_dir / file.name)
                self._state.db_snapshot_files.append(file.name)
        if db_path.name not in self._state.db_snapshot_files:
            raise Exception(f"Database {db_path} not found")

    def _restore_db(self, db_path: Path) -> None:
        for file in self._db_files(db_path):
            if file.name in self._state.db_snapshot_files:
                shutil.copy2(self._backup_dir / file.name, file)
            else:
                # Created by the new version, would not match the snapshot
                file.unlink(missing_ok=True)


def run_self_update(
    docker: SelfUpdateDocker, plan_path: Path
) -> SelfUpdateState | None:
    """
    Entry point of the helper.
    :returns: final state, or None if there is no state file to report to
    """
    work_dir: Final = plan_path.parent
    state_path: Final = work_dir / SELF_UPDATE_STATE_FILE
    state = read_state(state_path)
    try:
        plan = load_plan(plan_path)
    except SelfUpdateAbort as e:
        logger.error(f"Self-update aborted: {e}")
        if state:
            state.status = ESelfUpdateStatus.ABORTED
            state.error = str(e)
            state.finished_at = datetime.now(UTC)
            write_state(state_path, state)
        return state
    if not state or state.status != ESelfUpdateStatus.PENDING:
        logger.error("Self-update aborted: no pending state file")
        return state
    return SelfUpdateRunner(docker, plan, work_dir, state).run()
