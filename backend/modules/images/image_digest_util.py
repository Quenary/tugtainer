import logging
from collections.abc import Iterable
from datetime import datetime

from python_on_whales.components.image.models import ImageInspectResult
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.jobs.check.check_util import (
    RemoteImageMetadata,
    get_remote_image_metadata,
    metadata_from_image_inspect,
    naive_utc,
    platform_from_image,
)
from backend.modules.images.image_digest_model import ImageDigestModel
from backend.util.now import now


def normalize_image_digest(digest: str) -> str:
    """
    Digest key shared by registry responses and repo digests.

    Strips quotes from an ETag and a leading ``repo@``.
    """
    value = digest.strip().strip('"')
    if "@" in value:
        value = value.rsplit("@", 1)[-1]
    return value


async def get_cached_image_digest(
    session: AsyncSession,
    digest: str,
) -> ImageDigestModel | None:
    key = normalize_image_digest(digest)
    if not key:
        return None
    result = await session.execute(
        select(ImageDigestModel).where(ImageDigestModel.digest == key)
    )
    return result.scalar_one_or_none()


async def load_image_digests(
    session: AsyncSession,
    digests: Iterable[str],
) -> dict[str, ImageDigestModel]:
    keys = {normalize_image_digest(item) for item in digests if item}
    keys.discard("")
    if not keys:
        return {}
    result = await session.execute(
        select(ImageDigestModel).where(ImageDigestModel.digest.in_(keys))
    )
    return {row.digest: row for row in result.scalars().all()}


def pending_image_digest(
    update_available: bool,
    remote_digests: list[str] | None,
    cache: dict[str, ImageDigestModel],
) -> ImageDigestModel | None:
    """Cached metadata of a pending update, when that digest was resolved."""
    if not update_available or not remote_digests:
        return None
    return cache.get(normalize_image_digest(remote_digests[0]))


async def save_image_digest(
    session: AsyncSession,
    digest: str,
    version: str | None,
    created: datetime | None,
) -> ImageDigestModel | None:
    """
    Insert metadata for a digest.

    A concurrent insert of the same digest keeps the first row.
    Does not commit the surrounding session.
    """
    key = normalize_image_digest(digest)
    if not key:
        return None
    existing = await get_cached_image_digest(session, key)
    if existing:
        return existing
    row = ImageDigestModel(
        digest=key,
        version=version,
        created=naive_utc(created),
        fetched_at=now(),
    )
    try:
        async with session.begin_nested():
            session.add(row)
    except IntegrityError:
        session.expunge(row)
        return await get_cached_image_digest(session, key)
    return row


async def cache_available_image_metadata(
    session: AsyncSession,
    spec: str,
    remote_digest: str,
    *,
    pulled_image: ImageInspectResult | None,
    local_image: ImageInspectResult | None,
) -> RemoteImageMetadata | None:
    """
    Return cached metadata for a pending digest, fetching it on a miss.

    A pulled image is read locally. Otherwise the registry config blob is
    fetched. A failed fetch is not stored.
    """
    logger = logging.getLogger("cache_available_image_metadata")
    key = normalize_image_digest(remote_digest)
    if not key:
        return None
    existing = await get_cached_image_digest(session, key)
    if existing:
        return RemoteImageMetadata(version=existing.version, created=existing.created)
    try:
        if pulled_image is not None:
            meta = metadata_from_image_inspect(pulled_image)
        else:
            meta = await get_remote_image_metadata(
                spec, platform_from_image(local_image)
            )
    except Exception:
        logger.exception(f"Failed to resolve image metadata for {spec} {key}")
        return None
    await save_image_digest(session, key, meta.version, meta.created)
    return meta
