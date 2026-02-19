import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.types import UUIDArray


class TAN(Base):
    __tablename__ = "tans"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # 'time', 'group_unlock', 'extend_window', 'override'
    scope_groups: Mapped[list[uuid.UUID] | None] = mapped_column(
        UUIDArray(), nullable=True
    )
    scope_devices: Mapped[list[uuid.UUID] | None] = mapped_column(
        UUIDArray(), nullable=True
    )
    value_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_unlock_until: Mapped[time | None] = mapped_column(Time, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    single_use: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'quest', 'parent_manual', 'scheduled', 'totp'
    source_quest_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    child: Mapped["User"] = relationship(  # noqa: F821
        back_populates="tans", foreign_keys=[child_id]
    )

    def __repr__(self) -> str:
        return f"<TAN(id={self.id}, code={self.code!r}, type={self.type!r})>"
