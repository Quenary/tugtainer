from pydantic import BaseModel


class NetworkConnectBodySchema(BaseModel):
    network: str
    container: str
    aliases: list[str] | None = None
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    links: list[str] | None = None
    link_local_ips: list[str] | None = None
    mac_address: str | None = None
    driver_opts: dict[str, str] | None = None
    gateway_priority: int | None = None


class NetworkDisconnectBodySchema(BaseModel):
    network: str
    container: str
    force: bool = False
