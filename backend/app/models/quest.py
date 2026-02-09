import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QuestTemplate(Base):
    __tablename__ = "quest_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    reward_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    tan_groups: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    proof_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ai_verify: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurrence: Mapped[str] = mapped_column(String(30), nullable=False)
    auto_detect_app: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auto_detect_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    family: Mapped["Family"] = relationship(back_populates="quest_templates")  # noqa: F821
    instances: Mapped[list["QuestInstance"]] = relationship(back_populates="template")

    def __repr__(self) -> str:
        return f"<QuestTemplate(id={self.id}, name={self.name!r})>"


class QuestInstance(Base):
    __tablename__ = "quest_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quest_templates.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available"
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proof_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    proof_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_tan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tans.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    template: Mapped["QuestTemplate"] = relationship(back_populates="instances")
    child: Mapped["User"] = relationship(  # noqa: F821
        back_populates="quest_instances", foreign_keys=[child_id]
    )
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by])  # noqa: F821
    generated_tan: Mapped["TAN | None"] = relationship(foreign_keys=[generated_tan_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<QuestInstance(id={self.id}, status={self.status!r})>"
