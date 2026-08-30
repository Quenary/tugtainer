from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from backend.config import Config

if TYPE_CHECKING:
    from backend.core.jobs.jobs_tracker import HostJobTracker

LOG_FORMAT = "BACKEND - %(levelname)s - %(name)s: %(message)s"
_HANDLER_NAME = "job_log_handler"

_job_log_sink: ContextVar[Callable[[str], None] | None] = ContextVar(
    "job_log_sink",
    default=None,
)


class JobLogHandler(logging.Handler):
    """Forwards records to the current job only when a ContextVar sink is set."""

    def emit(self, record: logging.LogRecord) -> None:
        sink = _job_log_sink.get()
        if sink is None:
            return
        try:
            sink(self.format(record))
        except Exception:
            self.handleError(record)


def _handler_level() -> int:
    name = getattr(Config, "LOG_LEVEL", None) or "INFO"
    return getattr(logging, str(name).upper(), logging.INFO)


def install_job_log_handler() -> JobLogHandler:
    """Attach a single process-wide handler to the root logger."""
    root = logging.getLogger()
    for existing in root.handlers:
        if getattr(existing, "name", None) == _HANDLER_NAME:
            return existing  # type: ignore[return-value]
    handler = JobLogHandler()
    handler.name = _HANDLER_NAME
    handler.setLevel(_handler_level())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    return handler


@asynccontextmanager
async def capture_job_logs(tracker: HostJobTracker):
    """Route logging from this task's call chain into tracker.append_log."""
    token = _job_log_sink.set(tracker.append_log)
    try:
        yield
    finally:
        _job_log_sink.reset(token)
