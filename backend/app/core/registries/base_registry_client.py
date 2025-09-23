class BaseRegistryClient:
    """Base class for registry clients"""

    def __init__(self, image_spec: str):
        self.image_spec = image_spec
        self.image, self.tag = self._parse_image(image_spec)

    def _parse_image(self, image_spec: str):
        if ":" in image_spec:
            return image_spec.rsplit(":", 1)
        return image_spec, "latest"

    async def get_remote_digest(self) -> str | None:
        raise NotImplementedError
