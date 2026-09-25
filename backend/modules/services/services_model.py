from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base_model import BaseModel
from backend.util.now import now

if TYPE_CHECKING:
    from backend.modules.hosts.hosts_model import HostsModel


class SwarmServicesModel(BaseModel):
    """Model of a Docker Swarm service tracked by Tugtainer."""

    __tablename__ = "swarm_services"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    image: Mapped[str] = mapped_column(String, nullable=False)
    image_id: Mapped[str | None] = mapped_column(String, nullable=True)

    check_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )
    update_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )
    update_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )

    checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        default=now,
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

    local_digests: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    remote_digests: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    notified_available_digests: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )

    host: Mapped["HostsModel"] = relationship("HostsModel", back_populates="services")
