import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from agent.api.image_api import is_exists


@pytest.mark.asyncio
async def test_image_is_exists_raises_when_missing(mocker: MockerFixture):
    mocker.patch("agent.api.image_api.DOCKER.image.exists", return_value=False)

    with pytest.raises(HTTPException) as exc_info:
        await is_exists("missing:latest")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Image not found"
