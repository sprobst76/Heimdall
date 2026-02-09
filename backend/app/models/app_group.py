import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AppGroup(Base):
    __tablename__ = "app_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )
    always_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tan_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_tan_bonus_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    child: Mapped["User"] = relationship(back_populates="app_groups")  # noqa: F821
    apps: Mapped[list["AppGroupApp"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AppGroup(id={self.id}, name={self.name!r})>"


class AppGroupApp(Base):
    __tablename__ = "app_group_apps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_package: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_executable: Mapped[str | None] = mapped_column(String(255), nullable=True)
    app_name: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    group: Mapped["AppGroup"] = relationship(back_populates="apps")

    def __repr__(self) -> str:
        return f"<AppGroupApp(id={self.id}, app_name={self.app_name!r})>"
