import ssl

from pydantic import BaseModel, ConfigDict, field_validator


def normalize_ssl_ca(value: str | None) -> str | None:
    """Strip PEM, treat empty as unset, reject invalid certificates."""
    if value is None:
        return None
    pem = value.strip()
    if not pem:
        return None
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=pem)
    except ssl.SSLError as e:
        raise ValueError("Invalid CA certificate PEM") from e
    return pem


class HostBase(BaseModel):
    name: str
    enabled: bool
    prune: bool
    prune_all: bool
    url: str
    ssl: bool
    ssl_ca: str | None = None
    timeout: int
    container_hc_timeout: int


class HostCreate(HostBase):
    secret: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("ssl_ca")
    @classmethod
    def validate_ssl_ca(cls, value: str | None) -> str | None:
        return normalize_ssl_ca(value)


class HostUpdate(HostBase):
    is_changing_secret: bool = False
    secret: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("ssl_ca")
    @classmethod
    def validate_ssl_ca(cls, value: str | None) -> str | None:
        return normalize_ssl_ca(value)


class HostInfo(HostBase):
    id: int
    has_secret: bool
    available_updates_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class HostStatusResponseBody(BaseModel):
    id: int
    ok: bool | None = None
    err: str | None = None


class HostSummary(BaseModel):
    host_id: int
    host_name: str
    host_enabled: bool
    total_containers: int
    by_status: dict[str, int]
    by_health: dict[str, int]
    by_protected: dict[str, int]
    by_check_enabled: dict[str, int]
    by_update_enabled: dict[str, int]
    by_update_available: dict[str, int]
    by_update_available_auto_check: dict[str, int]
    total_images: int
    unused_images: int
    dangling_images: int
