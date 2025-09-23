from .base_model import BaseModel
from sqlalchemy import String, DateTime, text
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime
from app.helpers.now import now


class SettingModel(BaseModel):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        onupdate=now,
        default=now,
        nullable=False,
    )
