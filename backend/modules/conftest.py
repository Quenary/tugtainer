import pytest

from backend.app import app


@pytest.fixture(autouse=True)
def restore_dependency_overrides():
    """Drop per-test FastAPI overrides so they do not leak into the next test."""
    snapshot = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(snapshot)
