from typing import Final

# Labels commonly used by publishers to declare a human readable version.
# The OCI label is the current standard, label-schema is its predecessor
# and is still present on a fair amount of older images.
VERSION_LABELS: Final[tuple[str, ...]] = (
    "org.opencontainers.image.version",
    "org.label-schema.version",
)


def get_version_from_labels(labels: dict[str, str] | None) -> str | None:
    """
    Get a human readable version declared by the image labels.

    This is a best effort hint, not something to pin with:
    the value is whatever the publisher wrote, so it may be inherited
    from a base image, a branch name, or a tag that is not published
    in the same form. Use the digests to pin an image.

    :param labels: dict of labels
    :return: version string or None
    """
    if not labels:
        return None
    for label in VERSION_LABELS:
        value = labels.get(label)
        if value and value.strip():
            return value.strip()
    return None
