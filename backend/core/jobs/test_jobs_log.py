import asyncio
import logging
from types import SimpleNamespace

from backend.core.jobs.jobs_log import capture_job_logs, install_job_log_handler
from backend.core.jobs.jobs_tracker import HostJobTracker


def _tracker(host_id: int = 99021) -> HostJobTracker:
    return HostJobTracker(SimpleNamespace(id=host_id, name="log-test"))


def test_capture_records_only_with_context(monkeypatch):
    root = logging.getLogger()
    monkeypatch.setattr(root, "level", logging.INFO)
    handler = install_job_log_handler()
    handler.setLevel(logging.INFO)

    tracker = _tracker()
    tracker.begin("check", ["open-webui"], [])
    job_logger = logging.getLogger("run_check_container_job.open-webui")
    job_logger.setLevel(logging.INFO)

    job_logger.info("outside the job")
    assert tracker.get()["current"].get("log") == []

    async def _inside() -> None:
        async with capture_job_logs(tracker):
            job_logger.info("Checking container update availability")

    asyncio.run(_inside())

    log = tracker.get()["current"]["log"]
    assert any("Checking container update availability" in line for line in log)
    assert any("run_check_container_job.open-webui" in line for line in log)
    assert not any("outside the job" in line for line in log)

    job_logger.info("after capture")
    assert not any("after capture" in line for line in tracker.get()["current"]["log"])


def test_foreign_task_does_not_write_to_job_log(monkeypatch):
    root = logging.getLogger()
    monkeypatch.setattr(root, "level", logging.INFO)
    handler = install_job_log_handler()
    handler.setLevel(logging.INFO)

    tracker = _tracker(99022)
    tracker.begin("check", ["a"], [])
    job_logger = logging.getLogger("get_image_remote_digest")
    job_logger.setLevel(logging.INFO)

    async def _job() -> None:
        async with capture_job_logs(tracker):
            await asyncio.sleep(0)

    async def _other() -> None:
        job_logger.info("other request")

    async def _run() -> None:
        await asyncio.gather(_job(), _other())

    asyncio.run(_run())
    assert tracker.get()["current"].get("log") == []
