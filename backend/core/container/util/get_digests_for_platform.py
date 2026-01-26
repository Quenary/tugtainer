from shared.schemas.manifest_schema import ManifestInspectSchema


def get_digests_for_platform(
    manifest: ManifestInspectSchema,
    architecture: str,
    os: str,
    image_id: str,
) -> list[str]:
    # for single-platform images
    # TODO python-on-whales missing media_type, config and layers
    # uncomment when fixed
    # if (
    #     manifest.media_type
    #     == "application/vnd.docker.distribution.manifest.v2+json"
    #     and manifest.config
    # ):
    #     return (
    #         [manifest.config.digest] if manifest.config.digest else []
    #     )

    # for multi-platform images
    # TODO python-on-whales missing media_type and schema_version (None)
    # uncomment when fixed
    # if (
    #     manifest.media_type
    #     == "application/vnd.oci.image.index.v1+json"
    #     and manifest.manifests
    # ):
    if manifest.manifests:
        return [
            item.digest
            for item in manifest.manifests
            if item.platform
            and item.digest
            and item.platform.architecture == architecture
            and item.platform.os == os
        ]

    # as a fallback for single-platform images
    # image id should match manifest.config.digest
    return [image_id]
