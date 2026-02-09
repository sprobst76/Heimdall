import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_child_started", "child_id", "started_at"),
        Index("ix_usage_events_app_group_started", "app_group_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    app_package: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_groups.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'start', 'stop', 'blocked'
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="usage_events")  # noqa: F821
    child: Mapped["User"] = relationship()  # noqa: F821
    app_group: Mapped["AppGroup | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<UsageEvent(id={self.id}, event_type={self.event_type!r})>"
