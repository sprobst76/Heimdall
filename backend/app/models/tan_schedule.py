import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Time, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.types import UUIDArray


class TanSchedule(Base):
    __tablename__ = "tan_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    recurrence: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # 'daily' | 'weekdays' | 'weekends' | 'school_days'
    tan_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # 'time' | 'group_unlock' | 'extend_window' | 'override'
    value_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    value_unlock_until: Mapped[time | None] = mapped_column(Time, nullable=True)
    scope_groups: Mapped[list[uuid.UUID] | None] = mapped_column(
        UUIDArray(), nullable=True,
    )
    scope_devices: Mapped[list[uuid.UUID] | None] = mapped_column(
        UUIDArray(), nullable=True,
    )
    expires_after_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=24,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<TanSchedule(id={self.id}, name={self.name!r})>"


class TanScheduleLog(Base):
    __tablename__ = "tan_schedule_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tan_schedules.id"), nullable=False,
    )
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_tan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tans.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("schedule_id", "generated_date", name="uq_tan_schedule_log_date"),
    )

    def __repr__(self) -> str:
        return f"<TanScheduleLog(id={self.id}, date={self.generated_date})>"
