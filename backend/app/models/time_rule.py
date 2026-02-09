import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.types import TextArray


class TimeRule(Base):
    __tablename__ = "time_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'device' or 'app_group'
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True
    )
    day_types: Mapped[list[str]] = mapped_column(
        TextArray(), nullable=False, default=lambda: ["weekday"]
    )
    time_windows: Mapped[dict] = mapped_column(JSON, nullable=False)
    daily_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_limits: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=list
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<TimeRule(id={self.id}, name={self.name!r})>"
