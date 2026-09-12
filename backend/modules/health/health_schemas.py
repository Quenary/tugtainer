from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.schemas.paged_request import PagedRequest, PagedResponse


class HealthHistoryFilterRequest(PagedRequest):
    host_id: int
    container_id: int | None = None
    status: list[str] | None = None


class HealthHistoryResponseItem(BaseModel):
    id: int
    host_id: int
    container_id: int
    container_name: str
    status: str
    restarted: bool
    notified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthHistoryPagedResponse(PagedResponse):
    items: list[HealthHistoryResponseItem]
