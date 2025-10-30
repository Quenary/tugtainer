from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base_model import BaseModel
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .containers_model import ContainersModel


class HostsModel(BaseModel):
    """Model of docker host"""

    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("TRUE"),
    )
    prune: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )
    url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    secret: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    timeout: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default=text("5")
    )

    containers: Mapped[list["ContainersModel"]] = relationship(
        "ContainersModel",
        back_populates="host",
        cascade="all, delete-orphan",
    )
