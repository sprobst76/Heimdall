import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Family(Base):
    __tablename__ = "families"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Europe/Berlin"
    )
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, server_default=text("'{}'::json"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="family")  # noqa: F821
    day_type_overrides: Mapped[list["DayTypeOverride"]] = relationship(  # noqa: F821
        back_populates="family"
    )
    quest_templates: Mapped[list["QuestTemplate"]] = relationship(  # noqa: F821
        back_populates="family"
    )

    def __repr__(self) -> str:
        return f"<Family(id={self.id}, name={self.name!r})>"
