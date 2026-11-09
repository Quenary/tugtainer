from pydantic import BaseModel


class NetworkConnectBodySchema(BaseModel):
    network: str
    container: str
    aliases: list[str] | None = None
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    links: list[str] | None = None
    mac_address: str | None = None
    gateway_priority: int | None = None


class NetworkDisconnectBodySchema(BaseModel):
    network: str
    container: str
    force: bool = False
