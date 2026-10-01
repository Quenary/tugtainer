from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base_model import BaseModel


class ImageDigestModel(BaseModel):
    """
    Immutable registry metadata for one image digest.

    Shared by containers and swarm services. A row is written even when the
    image has no version label, so later checks do not fetch the same blob.
    """

    __tablename__ = "image_digests"

    digest: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
