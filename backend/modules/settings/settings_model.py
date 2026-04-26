from datetime import datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base_model import BaseModel
from backend.util.now import now


class SettingModel(BaseModel):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        onupdate=now,
        default=now,
        nullable=False,
    )
