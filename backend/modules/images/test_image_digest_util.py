from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.check.check_util import RemoteImageMetadata
from backend.modules.images.image_digest_model import ImageDigestModel
from backend.modules.images.image_digest_util import (
    cache_available_image_metadata,
    normalize_image_digest,
    pending_image_digest,
)


def test_normalize_image_digest_strips_repo_and_quotes():
    assert normalize_image_digest(' "nginx@sha256:abc" ') == "sha256:abc"
    assert normalize_image_digest("sha256:abc") == "sha256:abc"


def test_pending_image_digest_only_when_update_is_pending():
    created = datetime(2024, 5, 1)
    row = ImageDigestModel(
        digest="sha256:new",
        version="2.3.7",
        created=created,
        fetched_at=created,
    )
    cache = {"sha256:new": row}

    assert pending_image_digest(True, ["sha256:new"], cache) is row
    assert pending_image_digest(False, ["sha256:new"], cache) is None
    assert pending_image_digest(True, ["sha256:missing"], cache) is None


def _session_with_row(row: object | None) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)
    nested = MagicMock()
    nested.__aenter__ = AsyncMock(return_value=None)
    nested.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=nested)
    session.add = MagicMock()
    session.expunge = MagicMock()
    return session


@pytest.mark.asyncio
async def test_cache_reuses_stored_digest_without_a_registry_read(
    mocker: MockerFixture,
):
    created = datetime(2024, 5, 1)
    session = _session_with_row(
        SimpleNamespace(version="2.3.7", created=created, digest="sha256:new")
    )
    fetch = mocker.patch(
        "backend.modules.images.image_digest_util.get_remote_image_metadata",
        AsyncMock(),
    )

    meta = await cache_available_image_metadata(
        session,
        "nginx:latest",
        "sha256:new",
        pulled_image=None,
        local_image=None,
    )

    assert meta == RemoteImageMetadata(version="2.3.7", created=created)
    fetch.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_cache_reads_a_pulled_image_instead_of_the_registry(
    mocker: MockerFixture,
):
    session = _session_with_row(None)
    fetch = mocker.patch(
        "backend.modules.images.image_digest_util.get_remote_image_metadata",
        AsyncMock(),
    )
    pulled = MagicMock()
    pulled.created = datetime(2024, 5, 1)
    pulled.config = SimpleNamespace(
        labels={"org.opencontainers.image.version": "9.1.0"}
    )

    meta = await cache_available_image_metadata(
        session,
        "nginx:latest",
        "sha256:new",
        pulled_image=pulled,
        local_image=None,
    )

    assert meta is not None
    assert meta.version == "9.1.0"
    assert meta.created == datetime(2024, 5, 1)
    fetch.assert_not_awaited()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_cache_does_not_store_a_failed_registry_read(mocker: MockerFixture):
    session = _session_with_row(None)
    mocker.patch(
        "backend.modules.images.image_digest_util.get_remote_image_metadata",
        AsyncMock(side_effect=ValueError("registry down")),
    )

    meta = await cache_available_image_metadata(
        session,
        "nginx:latest",
        "sha256:new",
        pulled_image=None,
        local_image=None,
    )

    assert meta is None
    session.add.assert_not_called()
