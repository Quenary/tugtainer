from pydantic import BaseModel, ConfigDict
from python_on_whales.components.buildx.imagetools.models import (
    ImageVariantManifest,
)


class ManifestInspectSchema(BaseModel):
    schema_version: str | int | None = None
    media_type: str | None = None
    manifests: list[ImageVariantManifest] | None

    model_config = ConfigDict(from_attributes=True)
