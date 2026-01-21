from pydantic import BaseModel, ConfigDict
from python_on_whales.components.buildx.imagetools.models import (
    ImageVariantManifest,
    ManifestConfig,
)


class ManifestInspectSchema(BaseModel):
    schema_version: str | int | None
    media_type: str | None
    manifests: list[ImageVariantManifest] | None
    # TODO python-on-whales Manifest class should be updated, missing config
    # config: ManifestConfig | None

    model_config = ConfigDict(from_attributes=True)
