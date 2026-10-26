from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from backend.app import app
from backend.exception import TugSelfUpdateError
from backend.modules.auth.auth_util import is_authorized_req
from shared.self_update.self_update_schemas import ESelfUpdateStatus, SelfUpdateState

module_path = "backend.modules.self_update.self_update_router"

client = TestClient(app)


@pytest.fixture(autouse=True)
def authorized():
    app.dependency_overrides[is_authorized_req] = lambda: True


def _state() -> SelfUpdateState:
    return SelfUpdateState(
        status=ESelfUpdateStatus.PENDING,
        container_name="tugtainer",
        old_container_id="a" * 64,
        helper_container_name="tugtainer-self-update",
        old_image_id="sha256:old",
        new_image_id="sha256:new",
    )


@pytest.mark.parametrize("allowed", [True, False])
def test_status(mocker: MockerFixture, allowed: bool) -> None:
    mocker.patch(f"{module_path}.Config.ALLOW_SELF_UPDATE", allowed)
    mocker.patch(f"{module_path}.get_current_state", return_value=_state())

    response = client.get("/self_update/status")

    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is allowed
    assert data["state"]["status"] == "pending"


def test_start_disabled(mocker: MockerFixture) -> None:
    mocker.patch(f"{module_path}.Config.ALLOW_SELF_UPDATE", False)
    start = mocker.patch(f"{module_path}.start_self_update", new=AsyncMock())

    response = client.post("/self_update/start")

    assert response.status_code == 403
    start.assert_not_called()


def test_start_accepted(mocker: MockerFixture) -> None:
    mocker.patch(f"{module_path}.Config.ALLOW_SELF_UPDATE", True)
    mocker.patch(
        f"{module_path}.start_self_update", new=AsyncMock(return_value=_state())
    )

    response = client.post("/self_update/start")

    assert response.status_code == 202
    assert response.json()["helper_container_name"] == "tugtainer-self-update"


def test_start_conflict(mocker: MockerFixture) -> None:
    mocker.patch(f"{module_path}.Config.ALLOW_SELF_UPDATE", True)
    mocker.patch(
        f"{module_path}.start_self_update",
        new=AsyncMock(side_effect=TugSelfUpdateError("No newer image for x:1")),
    )

    response = client.post("/self_update/start")

    assert response.status_code == 409
    assert response.json()["detail"] == "No newer image for x:1"
