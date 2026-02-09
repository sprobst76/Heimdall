import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class DayTypeOverrideCreate(BaseModel):
    date: date
    day_type: str  # holiday | vacation | weekend | weekday | custom
    label: str | None = None


class DayTypeOverrideResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    date: date
    day_type: str
    label: str | None = None
    source: str
    model_config = ConfigDict(from_attributes=True)


class HolidaySyncRequest(BaseModel):
    year: int
    subdivision: str = "DE-BW"
