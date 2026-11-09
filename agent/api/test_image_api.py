from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from agent.api.image_api import is_exists, list_images, pull
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    PullImageRequestBodySchema,
)


@pytest.mark.asyncio
async def test_image_is_exists_raises_when_missing(mocker: MockerFixture):
    mocker.patch(
        "agent.api.image_api.RUNTIME_CLIENT.image_exists",
        new=AsyncMock(return_value=False),
    )

    with pytest.raises(HTTPException) as exc_info:
        await is_exists("missing:latest")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Image not found"


@pytest.mark.asyncio
async def test_list_images_passes_repository_or_tag_as_reference(
    mocker: MockerFixture,
) -> None:
    image_list = mocker.patch(
        "agent.api.image_api.RUNTIME_CLIENT.image_list",
        new=AsyncMock(return_value=[]),
    )

    await list_images(
        GetImageListBodySchema(
            repository_or_tag="nginx:1",
            filters={"dangling": ["true"]},
            all=False,
        )
    )

    image_list.assert_awaited_once_with(
        all=False,
        filters={"dangling": ["true"], "reference": ["nginx:1"]},
    )


@pytest.mark.asyncio
async def test_pull_passes_registry_auth(mocker: MockerFixture) -> None:
    auth = {"username": "user", "password": "secret", "serveraddress": "ghcr.io"}
    mocker.patch("agent.api.image_api.registry_auth_for_image", return_value=auth)
    image_pull = mocker.patch(
        "agent.api.image_api.RUNTIME_CLIENT.image_pull",
        new=AsyncMock(),
    )

    await pull(PullImageRequestBodySchema(image="ghcr.io/org/app:1"))

    image_pull.assert_awaited_once_with("ghcr.io/org/app:1", auth_config=auth)
