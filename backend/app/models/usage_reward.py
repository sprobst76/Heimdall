import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.types import UUIDArray


class UsageRewardRule(Base):
    __tablename__ = "usage_reward_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
    )  # 'daily_under', 'streak_under', 'group_free'
    threshold_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_groups.id"), nullable=True,
    )  # null = total usage
    streak_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reward_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_group_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        UUIDArray(), nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<UsageRewardRule(id={self.id}, name={self.name!r})>"


class UsageRewardLog(Base):
    __tablename__ = "usage_reward_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usage_reward_rules.id"), nullable=False,
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False,
    )
    evaluated_date: Mapped[date] = mapped_column(Date, nullable=False)
    usage_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    rewarded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    generated_tan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("tans.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("rule_id", "evaluated_date", name="uq_reward_log_rule_date"),
    )

    def __repr__(self) -> str:
        return f"<UsageRewardLog(id={self.id}, date={self.evaluated_date})>"
