from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class HostBase(BaseModel):
    name: str
    enabled: bool
    prune: bool
    # Optional fields for python-on-whales client
    config: Optional[str] = None
    context: Optional[str] = None
    host: Optional[str] = None
    tls: Optional[bool] = None
    tlscacert: Optional[str] = None
    tlscert: Optional[str] = None
    tlskey: Optional[str] = None
    tlsverify: Optional[bool] = None
    client_binary: Optional[str] = None
    client_call: Optional[list[str]] = None
    client_type: Optional[
        Literal["docker", "podman", "nerdctl", "unknown"]
    ] = None


class HostInfo(HostBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
