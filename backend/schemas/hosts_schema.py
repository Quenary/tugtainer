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


class HostInfo(HostBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class HostStatusResponseBody(BaseModel):
    id: int
    ok: bool | None = None
    err: str | None = None
