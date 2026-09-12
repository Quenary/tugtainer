from pydantic import BaseModel, Field


class PagedRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PagedResponse(BaseModel):
    total: int
    page: int
    limit: int
