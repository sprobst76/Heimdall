import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import UUIDArray


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'android', 'windows', 'ios'
    device_identifier: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    device_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    child: Mapped["User"] = relationship(back_populates="devices")  # noqa: F821
    usage_events: Mapped[list["UsageEvent"]] = relationship(  # noqa: F821
        back_populates="device"
    )

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, name={self.name!r}, type={self.type!r})>"


class DeviceCoupling(Base):
    __tablename__ = "device_couplings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    device_ids: Mapped[list[uuid.UUID]] = mapped_column(
        UUIDArray(), nullable=False
    )
    shared_budget: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    child: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<DeviceCoupling(id={self.id}, child_id={self.child_id})>"
