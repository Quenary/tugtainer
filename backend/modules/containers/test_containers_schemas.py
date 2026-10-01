from datetime import datetime

from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.const import (
    TUGTAINER_AUTO_CHECK_LABEL,
    TUGTAINER_AUTO_UPDATE_LABEL,
)
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.containers.containers_schemas import ContainersListItem
from backend.modules.images.image_digest_model import ImageDigestModel


def _docker(labels: dict[str, str] | None = None) -> ContainerInspectResult:
    return ContainerInspectResult(
        id="c1",
        name="web",
        config=ContainerConfig(
            image="nginx:latest",
            labels=labels or {},
        ),
    )


def _db(**kwargs: object) -> ContainersModel:
    data = {
        "id": 1,
        "host_id": 1,
        "name": "web",
        "check_enabled": True,
        "update_enabled": False,
        "update_available": False,
    }
    data.update(kwargs)
    return ContainersModel(**data)


def _digest() -> ImageDigestModel:
    created = datetime(2024, 5, 1, 12, 0)
    return ImageDigestModel(
        digest="sha256:new",
        version="2.3.7",
        created=created,
        fetched_at=created,
    )


def test_from_sources_reads_current_version_and_auto_labels():
    item = ContainersListItem.from_sources(
        1,
        _docker(
            {
                TUGTAINER_AUTO_CHECK_LABEL: "true",
                TUGTAINER_AUTO_UPDATE_LABEL: "false",
                "org.opencontainers.image.version": "2.3.6",
            }
        ),
        _db(check_enabled=False, update_enabled=True),
    )

    assert item.current_version == "2.3.6"
    assert item.auto_check_label is True
    assert item.auto_update_label is False
    assert item.check_enabled is False
    assert item.update_enabled is True
    assert item.image == "nginx:latest"
    assert item.available_version is None
    assert item.available_created is None


def test_from_sources_copies_pending_digest_metadata():
    digest = _digest()
    item = ContainersListItem.from_sources(
        1,
        _docker(),
        _db(update_available=True, remote_digests=["sha256:new"]),
        digest,
    )

    assert item.update_available is True
    assert item.available_version == "2.3.7"
    assert item.available_created == digest.created


def test_from_sources_keeps_created_when_the_pending_image_has_no_version():
    created = datetime(2024, 5, 1)
    digest = ImageDigestModel(
        digest="sha256:new",
        version=None,
        created=created,
        fetched_at=created,
    )

    item = ContainersListItem.from_sources(
        1,
        _docker(),
        _db(update_available=True),
        digest,
    )

    assert item.available_version is None
    assert item.available_created == created


def test_from_sources_ignores_digest_metadata_when_update_is_not_available():
    item = ContainersListItem.from_sources(1, _docker(), _db(), _digest())

    assert item.update_available is False
    assert item.available_version is None
    assert item.available_created is None


def test_from_sources_without_a_digest_row_leaves_available_fields_empty():
    item = ContainersListItem.from_sources(
        1,
        _docker(),
        _db(update_available=True),
    )

    assert item.available_version is None
    assert item.available_created is None


def test_from_sources_without_a_db_row_ignores_the_digest():
    item = ContainersListItem.from_sources(1, _docker(), None, _digest())

    assert item.id is None
    assert item.update_available is None
    assert item.available_version is None
    assert item.available_created is None


def test_from_sources_maps_previous_image_fields():
    item = ContainersListItem.from_sources(
        1,
        _docker(),
        _db(
            previous_image_digests=["nginx@sha256:old"],
            previous_image_tags=["nginx:1.2.3"],
            previous_image_version="1.2.3",
        ),
    )

    assert item.previous_image_digests == ["nginx@sha256:old"]
    assert item.previous_image_tags == ["nginx:1.2.3"]
    assert item.previous_image_version == "1.2.3"
