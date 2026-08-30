from types import SimpleNamespace

from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.enums.job_status_enum import EJobStatus


def _tracker(host_id: int, name: str = "tracker-test") -> HostJobTracker:
    return HostJobTracker(SimpleNamespace(id=host_id, name=name))


def test_finish_appends_completed_and_begin_preserves_it():
    tracker = _tracker(99011)

    tracker.begin("check", ["a", "b"], [])
    tracker.set_container("a", EJobStatus.DONE)
    first = tracker.finish(EJobStatus.DONE)

    after_first = tracker.get()
    assert after_first is not None
    assert after_first["status"] == EJobStatus.DONE
    assert after_first["current"] is None
    assert len(after_first["completed"]) == 1
    assert after_first["completed"][0]["kind"] == "check"
    assert after_first["completed"][0]["names"] == ["a", "b"]
    assert first["names"] == ["a", "b"]
    assert "a" in first["containers"]

    tracker.begin("check", ["c", "d"], [])
    mid = tracker.get()
    assert mid is not None
    assert mid["status"] == EJobStatus.PREPARING
    assert mid["current"] is not None
    assert mid["current"]["kind"] == "check"
    assert mid["current"]["names"] == ["c", "d"]
    assert len(mid["completed"]) == 1
    assert "a" not in (mid["current"].get("containers") or {})
    assert mid["current"]["containers"]["c"]["status"] == EJobStatus.PREPARING

    second = tracker.finish(EJobStatus.DONE)
    after_second = tracker.get()
    assert after_second is not None
    assert after_second["current"] is None
    assert len(after_second["completed"]) == 2
    assert after_second["completed"][0]["names"] == ["a", "b"]
    assert after_second["completed"][1]["names"] == ["c", "d"]
    assert second["names"] == ["c", "d"]


def test_complete_current_keeps_host_active():
    tracker = _tracker(99012)

    tracker.begin("check", ["a"], [{"kind": "update", "names": ["b"]}])
    first = tracker.complete_current(EJobStatus.DONE)

    state = tracker.get()
    assert state is not None
    assert state["status"] == EJobStatus.PREPARING
    assert state["current"] is not None
    assert state["current"]["kind"] == "check"
    assert state["current"]["names"] == ["a"]
    assert state["queued"] == [{"kind": "update", "names": ["b"]}]
    assert len(state["completed"]) == 1
    assert first["kind"] == "check"


def test_append_log_writes_and_caps():
    tracker = _tracker(99013)
    tracker.begin("check", ["a"], [])
    tracker.append_log("line-0")
    current = tracker.get()["current"]
    assert current["log"] == ["line-0"]

    for i in range(1, 501):
        tracker.append_log(f"line-{i}")
    log = tracker.get()["current"]["log"]
    assert len(log) == 500
    assert log[0] == "line-1"
    assert log[-1] == "line-500"

    finished = tracker.finish(EJobStatus.DONE)
    assert finished["log"][-1] == "line-500"
    assert tracker.get()["completed"][0]["log"][-1] == "line-500"
