import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("families.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'parent' or 'child'
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    family: Mapped["Family"] = relationship(back_populates="users")  # noqa: F821
    devices: Mapped[list["Device"]] = relationship(back_populates="child")  # noqa: F821
    app_groups: Mapped[list["AppGroup"]] = relationship(back_populates="child")  # noqa: F821
    tans: Mapped[list["TAN"]] = relationship(  # noqa: F821
        back_populates="child", foreign_keys="TAN.child_id"
    )
    quest_instances: Mapped[list["QuestInstance"]] = relationship(  # noqa: F821
        back_populates="child", foreign_keys="QuestInstance.child_id"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name!r}, role={self.role!r})>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
