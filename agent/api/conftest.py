import pytest

from agent.app import app
from agent.auth import verify_signature


async def _allow_request() -> None:
    return None


@pytest.fixture(autouse=True)
def bypass_signature():
    """API route tests stub signature checks. Auth coverage lives in ``agent/test_auth.py``."""
    app.dependency_overrides[verify_signature] = _allow_request
    yield
