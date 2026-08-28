import os
from collections.abc import Iterable
from pathlib import Path
from typing import Final

SECRET_ENV_VARS: Final[tuple[str, ...]] = (
    "AGENT_SECRET",
    "JWT_SECRET_KEY",
    "GH_TOKEN",
    "OIDC_CLIENT_ID",
    "OIDC_CLIENT_SECRET",
)


def apply_file_env(names: Iterable[str] = SECRET_ENV_VARS) -> None:
    """
    Resolve Docker-style VAR_FILE secrets into os.environ.

    VAR and VAR_FILE are exclusive. After a successful read, VAR_FILE is left
    empty so a later load_dotenv() does not resurrect the path and trip the
    exclusive check on a second apply (start.py / reload / Config.load).
    """
    for name in names:
        file_name = f"{name}_FILE"
        value = os.getenv(name)
        file_value = os.getenv(file_name)

        if value and file_value:
            raise RuntimeError(
                f"Both {name} and {file_name} are set (but are exclusive)"
            )
        if not file_value:
            continue

        path = Path(file_value)
        try:
            content = path.read_text().rstrip("\r\n")
        except OSError as exc:
            raise RuntimeError(f"Secret file not readable: {file_value}") from exc

        os.environ[name] = content
        os.environ[file_name] = ""
