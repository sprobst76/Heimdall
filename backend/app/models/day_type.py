import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DayTypeOverride(Base):
    __tablename__ = "day_type_overrides"
    __table_args__ = (
        UniqueConstraint("family_id", "date", name="uq_day_type_overrides_family_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    day_type: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 'api' or 'manual'

    # Relationships
    family: Mapped["Family"] = relationship(back_populates="day_type_overrides")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DayTypeOverride(id={self.id}, date={self.date}, day_type={self.day_type!r})>"
