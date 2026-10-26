from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, Field

from shared.schemas.container_schemas import CreateContainerRequestBodySchema

# Bump on any incompatible change of SelfUpdatePlan.
# The helper refuses plans of other versions without touching anything.
SELF_UPDATE_PLAN_VERSION: Final = 1

# File names inside the self-update work dir on the data volume
SELF_UPDATE_PLAN_FILE: Final = "plan.json"
SELF_UPDATE_STATE_FILE: Final = "state.json"
SELF_UPDATE_BACKUP_DIR: Final = "backup"

# Suffixes of container names used during the swap
SELF_UPDATE_OLD_SUFFIX: Final = "-old"
SELF_UPDATE_HELPER_SUFFIX: Final = "-self-update"

# SQLite keeps uncommitted pages next to the database file
SQLITE_SIDE_SUFFIXES: Final[tuple[str, ...]] = ("-wal", "-shm")


def _now() -> datetime:
    return datetime.now(UTC)


class SelfUpdatePlan(BaseModel):
    """
    Plan precomputed by the backend and executed by the helper.
    """

    version: int
    container_id: str
    container_name: str
    old_image_id: str
    new_image_id: str
    old_version: str | None = None
    new_version: str | None = None
    create: CreateContainerRequestBodySchema
    # Docker commands to run after the new container started,
    # e.g. ["network", "connect", ...]
    commands: list[list[str]] = []
    healthcheck_timeout: int
    # Absolute path of the SQLite database on the data volume, if any
    db_path: str | None = None


class ESelfUpdateStatus(StrEnum):
    # Backend launched the helper, which has not picked up the plan yet
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    # Refused before touching any container
    ABORTED = "aborted"
    ROLLED_BACK = "rolled_back"
    # Rollback did not complete, manual action required
    FAILED = "failed"
    # Helper is gone without a final status
    INTERRUPTED = "interrupted"


FINAL_SELF_UPDATE_STATUSES: Final = frozenset(
    {
        ESelfUpdateStatus.SUCCEEDED,
        ESelfUpdateStatus.ABORTED,
        ESelfUpdateStatus.ROLLED_BACK,
        ESelfUpdateStatus.FAILED,
        ESelfUpdateStatus.INTERRUPTED,
    }
)


class ESelfUpdatePhase(StrEnum):
    OLD_RENAMED = "old_renamed"
    NEW_CREATED = "new_created"
    OLD_STOPPED = "old_stopped"
    DB_SNAPSHOT = "db_snapshot"
    NEW_STARTED = "new_started"
    NEW_HEALTHY = "new_healthy"
    OLD_REMOVED = "old_removed"
    # Rollback steps
    NEW_REMOVED = "new_removed"
    DB_RESTORED = "db_restored"
    OLD_RENAMED_BACK = "old_renamed_back"
    OLD_STARTED = "old_started"


class SelfUpdateJournalEntry(BaseModel):
    phase: ESelfUpdatePhase
    at: datetime = Field(default_factory=_now)


class SelfUpdateState(BaseModel):
    """
    State file on the data volume.
    Written by the backend when the helper is launched,
    then kept up to date by the helper as a phase journal.
    """

    status: ESelfUpdateStatus
    container_name: str
    old_container_id: str
    new_container_id: str | None = None
    helper_container_name: str
    old_image_id: str
    new_image_id: str
    old_version: str | None = None
    new_version: str | None = None
    journal: list[SelfUpdateJournalEntry] = []
    # SQLite files present when the snapshot was taken (file names only)
    db_snapshot_files: list[str] = []
    error: str | None = None
    warnings: list[str] = []
    started_at: datetime = Field(default_factory=_now)
    finished_at: datetime | None = None

    def has_phase(self, phase: ESelfUpdatePhase) -> bool:
        return any(e.phase == phase for e in self.journal)

    @property
    def is_final(self) -> bool:
        return self.status in FINAL_SELF_UPDATE_STATUSES
