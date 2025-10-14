from sqlalchemy import JSON, Boolean, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base_model import BaseModel
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from .containers_model import ContainersModel


class HostModel(BaseModel):
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
    # Optional fields for python-on-whales client
    config: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    context: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    host: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tls: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    tlscacert: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    tlscert: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    tlskey: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    tlsverify: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    client_binary: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    client_call: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )
    client_type: Mapped[
        Optional[Literal["docker", "podman", "nerdctl", "unknown"]]
    ] = mapped_column(String, nullable=True)

    containers: Mapped[list["ContainersModel"]] = relationship(
        "ContainersModel",
        back_populates="host",
        cascade="all, delete-orphan",
    )
