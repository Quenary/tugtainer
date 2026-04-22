from typing import Any, cast
import pytest
from fastapi.testclient import TestClient

from pytest_mock import MockerFixture
from backend.app import app

module_path = "backend.modules.public.public_router"

client = TestClient(app)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "current_version, latest_version, expected_is_available, expected_release_url",
    [
        ("1.0.0", "1.1.0", True, "https://github.com/release"),
        ("1.1.0", "1.2.0", True, "https://github.com/release"),
        ("1.2.0", "1.1.0", False, "https://github.com/release"),
        ("1.2.0", "1.2.0", False, "https://github.com/release"),
    ],
)
async def test_is_update_available(
    mocker: MockerFixture,
    current_version,
    latest_version,
    expected_is_available,
    expected_release_url,
):
    # clear cache
    from backend.modules.public.public_router import (
        is_update_available,
    )

    cast(Any, is_update_available).cache.clear()

    mocker.patch(
        f"builtins.open", mocker.mock_open(read_data=current_version)
    )
    mocker.patch(
        f"{module_path}.fetch_latest_release",
        return_value={
            "tag_name": latest_version,
            "html_url": expected_release_url,
        },
    )

    response = client.get("/public/is_update_available")
    assert response.status_code == 200

    data = response.json()
    assert data["is_available"] == expected_is_available
    assert data["release_url"] == expected_release_url
