from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)
from python_on_whales.components.image.models import ImageInspectResult

from backend.const import TUGTAINER_HIDDEN_LABEL
from backend.modules.images.images_router import get_list

module_path = "backend.modules.images.images_router"


@pytest.mark.asyncio
async def test_image_used_only_by_hidden_container_stays_used(
    mocker: MockerFixture,
):
    mocker.patch(
        f"{module_path}.get_host",
        AsyncMock(return_value=mocker.Mock()),
    )
    hidden = ContainerInspectResult(
        id="c",
        name="hidden",
        image="sha256:used",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "on"}),
    )
    client = mocker.Mock()
    client.container.list = AsyncMock(return_value=[hidden])
    client.image.list = AsyncMock(
        return_value=[ImageInspectResult(id="sha256:used", repo_tags=["app:1"])]
    )
    mocker.patch(
        f"{module_path}.AgentClientManager.get_host_client",
        return_value=client,
    )

    images = await get_list(1, session=AsyncMock())

    assert len(images) == 1
    assert images[0].unused is False
    assert images[0].dangling is False
