from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from backend.app import app
from backend.modules.auth.auth_util import is_authorized
from backend.modules.settings.settings_constants import TEST_NOTIFICATION_RESULTS

base_module = "backend.modules.settings.settings_router"

client = TestClient(app)


async def override_is_authorized():
    return True


app.dependency_overrides[is_authorized] = override_is_authorized


def _body(urls: str = "https://example.com/hook") -> dict[str, str]:
    return {
        "title_template": "title",
        "body_template": "body",
        "urls": urls,
    }


@pytest.mark.parametrize("urls", ["", "  \n  "])
def test_test_notification_requires_urls(urls: str):
    response = client.post("/settings/test_notification", json=_body(urls))

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Failed to send notification. URLs is undefined."
    )


@pytest.mark.asyncio
async def test_test_notification_sends_sample_results(mocker: MockerFixture):
    send = mocker.patch(
        f"{base_module}.send_check_notification",
        new_callable=AsyncMock,
    )
    mocker.patch(
        f"{base_module}.validate_notification_urls_against_ssrf",
        new_callable=AsyncMock,
    )

    response = client.post("/settings/test_notification", json=_body())

    assert response.status_code == 200
    send.assert_awaited_once_with(
        TEST_NOTIFICATION_RESULTS,
        title_template="title",
        body_template="body",
        urls="https://example.com/hook",
    )
