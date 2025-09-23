from typing import Any, Optional
from pydantic import BaseModel


class ContainerGetResponseBody(BaseModel):
    name: str
    short_id: str
    ports: dict[str, Any]
    status: str
    health: str
    check_enabled: Optional[bool] = None
    update_enabled: Optional[bool] = None


class ContainerPatchRequestBody(BaseModel):
    check_enabled: Optional[bool] = None
    update_enabled: Optional[bool] = None
