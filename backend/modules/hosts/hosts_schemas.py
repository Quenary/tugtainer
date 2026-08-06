from pydantic import BaseModel, ConfigDict


class HostBase(BaseModel):
    name: str
    enabled: bool
    prune: bool
    prune_all: bool
    url: str
    ssl: bool
    timeout: int
    container_hc_timeout: int


class HostCreate(HostBase):
    secret: str | None = None


class HostUpdate(HostBase):
    is_changing_secret: bool = False
    secret: str | None = None


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
    total_images: int
    unused_images: int
    dangling_images: int
