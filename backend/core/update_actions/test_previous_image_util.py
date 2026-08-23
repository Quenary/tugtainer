from python_on_whales.components.container.models import ContainerConfig
from python_on_whales.components.image.models import ImageInspectResult

from backend.core.update_actions.previous_image_util import (
    PreviousImage,
    get_image_version_label,
    get_previous_image,
    get_previous_image_for_result,
)


def _image(
    digests: list[str] | None = None,
    tags: list[str] | None = None,
    labels: dict[str, str] | None = None,
) -> ImageInspectResult:
    return ImageInspectResult(
        id="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        repo_digests=digests,
        repo_tags=tags,
        config=ContainerConfig(labels=labels),
    )


def test_version_label_from_oci_label():
    image = _image(labels={"org.opencontainers.image.version": "1.2.3"})

    assert get_image_version_label(image) == "1.2.3"


def test_version_label_falls_back_to_label_schema():
    image = _image(labels={"org.label-schema.version": "1.2.3"})

    assert get_image_version_label(image) == "1.2.3"


def test_version_label_prefers_oci_over_label_schema():
    image = _image(
        labels={
            "org.label-schema.version": "0.9.0",
            "org.opencontainers.image.version": "1.2.3",
        }
    )

    assert get_image_version_label(image) == "1.2.3"


def test_version_label_is_stripped():
    image = _image(labels={"org.opencontainers.image.version": "  1.2.3\n"})

    assert get_image_version_label(image) == "1.2.3"


def test_version_label_ignores_blank_value():
    image = _image(labels={"org.opencontainers.image.version": "   "})

    assert get_image_version_label(image) is None


def test_version_label_without_labels():
    assert get_image_version_label(_image()) is None
    assert get_image_version_label(_image(labels={})) is None
    assert get_image_version_label(None) is None


def test_get_previous_image_collects_everything():
    image = _image(
        digests=["nginx@sha256:abc"],
        tags=["nginx:1.2.3"],
        labels={"org.opencontainers.image.version": "1.2.3"},
    )

    previous = get_previous_image(image)

    assert previous.digests == ["nginx@sha256:abc"]
    assert previous.tags == ["nginx:1.2.3"]
    assert previous.version == "1.2.3"
    assert previous


def test_get_previous_image_of_locally_built_image():
    """A local image has no repo digests, but its tags are still useful."""
    previous = get_previous_image(_image(tags=["my-app:latest"]))

    assert previous.digests == []
    assert previous.tags == ["my-app:latest"]
    assert previous.version is None
    assert previous


def test_get_previous_image_without_image():
    previous = get_previous_image(None)

    assert previous == PreviousImage()
    assert not previous


def test_get_previous_image_is_falsy_when_nothing_collected():
    assert not get_previous_image(_image())


def test_previous_image_does_not_alias_the_inspect_result():
    """Mutating the collected lists must not touch the inspected image."""
    image = _image(digests=["nginx@sha256:abc"], tags=["nginx:1.2.3"])

    previous = get_previous_image(image)
    previous.digests.append("nginx@sha256:def")

    assert image.repo_digests == ["nginx@sha256:abc"]


def test_for_result_collects_on_updated():
    image = _image(digests=["nginx@sha256:abc"])

    assert get_previous_image_for_result(image, "updated").digests == [
        "nginx@sha256:abc"
    ]


def test_for_result_skips_rolled_back_and_failed():
    """
    After a rollback the container runs the inspected image again,
    so it is the current image, not a previous one.
    """
    image = _image(digests=["nginx@sha256:abc"])

    for result in ("rolled_back", "failed", "available", "not_available", None):
        previous = get_previous_image_for_result(image, result)
        assert not previous, f"expected nothing to be collected for {result}"
