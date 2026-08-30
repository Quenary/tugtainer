from dataclasses import dataclass, field
from typing import Final

from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.core.jobs.jobs_results import ContainerJobOutcome

# Labels commonly used by publishers to declare a human readable version.
# The OCI label is the current standard, label-schema is its predecessor
# and is still present on a fair amount of older images.
VERSION_LABELS: Final[tuple[str, ...]] = (
    "org.opencontainers.image.version",
    "org.label-schema.version",
)


@dataclass
class PreviousImage:
    """
    Identity of the image a container ran before an update.

    :param digests: repo digests e.g. ["repo@sha256:..."], the only value
        that is guaranteed to pin the exact image again
    :param tags: repo tags of that image, e.g. ["repo:1.2.3"]
    :param version: version reported by the image labels, if any.
        A hint only, see get_image_version_label
    """

    digests: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version: str | None = None

    def __bool__(self) -> bool:
        return bool(self.digests or self.tags or self.version)


def get_image_version_label(
    image: ImageInspectResult | None,
) -> str | None:
    """
    Get a human readable version declared by the image labels.

    This is a best effort hint, not something to pin with:
    the value is whatever the publisher wrote, so it may be inherited
    from a base image, a branch name, or a tag that is not published
    in the same form. Use the digests to pin an image.

    :param image: inspected image
    :return: version string or None
    """
    labels = image.config.labels if image and image.config else None
    if not labels:
        return None
    for label in VERSION_LABELS:
        value = labels.get(label)
        if value and value.strip():
            return value.strip()
    return None


def get_previous_image(
    image: ImageInspectResult | None,
) -> PreviousImage:
    """
    Collect the identity of an image from its inspect result.
    Everything is read from the already inspected image,
    no registry requests are made.

    :param image: image the container ran before the update
    :return: collected identity, falsy when nothing could be collected
    """
    if not image:
        return PreviousImage()
    return PreviousImage(
        digests=list(image.repo_digests or []),
        tags=list(image.repo_tags or []),
        version=get_image_version_label(image),
    )


def get_previous_image_for_result(
    image: ImageInspectResult | None,
    result: ContainerJobOutcome | None,
) -> PreviousImage:
    """
    Collect the previous image identity for a finished update.

    The image inspected before the pull is the *previous* one only when the
    new image actually took over. After a rollback or a failure the container
    is back on that same image, so it is the current one and recording it
    would hand the user a pin to what they are already running.

    :param image: image inspected before the pull
    :param result: result of the update for this container
    :return: collected identity, falsy when nothing should be recorded
    """
    if result != "updated":
        return PreviousImage()
    return get_previous_image(image)
