import os
from pathlib import Path

from .self_update_schemas import SelfUpdateState

# Plan and state may include env values of the app container
FILE_MODE = 0o600


def write_private_file(path: Path, content: str) -> None:
    """
    Atomically write a file readable only by the owner.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    with os.fdopen(fd, "w") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)


def read_state(path: Path) -> SelfUpdateState | None:
    """Read the state file, None if it does not exist."""
    try:
        content = path.read_text()
    except FileNotFoundError:
        return None
    return SelfUpdateState.model_validate_json(content)


def write_state(path: Path, state: SelfUpdateState) -> None:
    write_private_file(path, state.model_dump_json(indent=2))
