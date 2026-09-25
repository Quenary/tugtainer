from datetime import datetime

from pydantic import BaseModel, Field


class SwarmInfoSchema(BaseModel):
    cluster_id: str | None = None
    node_id: str | None = None
    is_manager: bool = False


class ServiceReplicasSchema(BaseModel):
    running: int = 0
    desired: int | None = None


class ServiceListItemSchema(BaseModel):
    id: str
    name: str
    image: str
    image_id: str | None = None
    mode: str = "replicated"
    replicas: ServiceReplicasSchema = Field(default_factory=ServiceReplicasSchema)
    labels: dict[str, str] = Field(default_factory=dict)
    update_status_state: str | None = None
    update_status_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ServiceUpdateRequestBody(BaseModel):
    service_id: str
    image: str


class ServicePatchBodySchema(BaseModel):
    check_enabled: bool | None = None
    update_enabled: bool | None = None
