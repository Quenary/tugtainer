from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base_model import BaseModel
from backend.util.now import now

if TYPE_CHECKING:
    from backend.modules.containers.containers_model import ContainersModel
    from backend.modules.hosts.hosts_model import HostsModel


class ContainerHealthState(BaseModel):
    __tablename__ = "container_health_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    container_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    restart_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    host: Mapped["HostsModel"] = relationship(
        "HostsModel", back_populates="health_states"
    )
    container: Mapped["ContainersModel | None"] = relationship(
        "ContainersModel", back_populates="health_state"
    )


class ContainerHealthHistory(BaseModel):
    __tablename__ = "container_health_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False
    )
    container_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("containers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    restarted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    host: Mapped["HostsModel"] = relationship(
        "HostsModel", back_populates="health_history"
    )
    container: Mapped["ContainersModel | None"] = relationship(
        "ContainersModel", back_populates="health_history"
    )
