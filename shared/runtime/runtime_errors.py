from typing import Any


class RuntimeEngineError(Exception):
    """Base exception for all runtime engine interactions."""

    def __init__(
        self,
        message: str = "",
        status_code: int | None = None,
        detail: Any = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"{self.message}: {self.detail}"
        return self.message or super().__str__()


class RuntimeClientError(RuntimeEngineError):
    """HTTP error returned by Docker/Podman engine daemon."""

    pass


class RuntimeNotFoundError(RuntimeClientError):
    """Resource (container, image, network, service) not found (HTTP 404)."""

    pass


class RuntimeConflictError(RuntimeClientError):
    """Conflict error from runtime daemon (HTTP 409), e.g. Swarm version conflict."""

    pass


class RuntimePreflightError(RuntimeEngineError):
    """Preflight validation failed before recreation; operation aborted safely."""

    pass


class IncompatibleRuntimeError(RuntimeEngineError):
    """Runtime engine or API version does not meet supported criteria."""

    pass


class RuntimeExecError(RuntimeEngineError):
    """Command executed inside container exited with a non-zero exit code."""

    def __init__(self, exit_code: int, stdout: str = "", stderr: str = ""):
        message = f"Command failed with exit code {exit_code}"
        detail = ""
        if stdout:
            detail += f"\nstdout: {stdout}"
        if stderr:
            detail += f"\nstderr: {stderr}"
        super().__init__(message=message, status_code=424, detail=detail.strip())
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class StreamTruncatedError(RuntimeEngineError):
    """Streaming response disconnected before payload or frame completed."""

    pass
