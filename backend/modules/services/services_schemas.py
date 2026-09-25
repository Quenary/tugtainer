from datetime import datetime

from pydantic import BaseModel, Field


class ServiceListItem(BaseModel):
    id: str
    name: str
    image: str
    mode: str = "replicated"
    replicas_running: int = 0
    replicas_desired: int | None = None
    check_enabled: bool = False
    update_enabled: bool = False
    update_available: bool = False
    checked_at: datetime | None = None
    updated_at: datetime | None = None
    update_status_state: str | None = None
    update_status_message: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class ServicePatchBody(BaseModel):
    check_enabled: bool | None = None
    update_enabled: bool | None = None


class ServiceTriggerRequestBody(BaseModel):
    names: list[str] | None = None
