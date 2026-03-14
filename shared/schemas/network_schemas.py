
from pydantic import BaseModel


class NetworkDisconnectBodySchema(BaseModel):
    network: str
    container: str
    force: bool = False