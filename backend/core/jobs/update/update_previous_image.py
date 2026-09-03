from dataclasses import dataclass, field

from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.core.jobs.jobs_results import ContainerJobOutcome
from backend.util.get_version_from_labels import get_version_from_labels


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
        version=get_version_from_labels(image.config.labels if image.config else None),
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
