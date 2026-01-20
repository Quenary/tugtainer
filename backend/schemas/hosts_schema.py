from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class HostBase(BaseModel):
    name: str
    enabled: bool
    prune: bool
    prune_all: bool
    url: str
    secret: Optional[str] = None
    timeout: int
    container_hc_timeout: int


class HostInfo(HostBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class HostStatusResponseBody(BaseModel):
    id: int
    ok: bool | None = None
    err: str | None = None


class HostSummary(BaseModel):
    host_id: int
    host_name: str
    total_containers: int
    by_status: dict[str, int]
    by_health: dict[str, int]
    by_protected: dict[str, int]
    by_check_enabled: dict[str, int]
    by_update_enabled: dict[str, int]
    by_update_available: dict[str, int]
