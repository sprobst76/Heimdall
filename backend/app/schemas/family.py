import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FamilyBase(BaseModel):
    name: str
    timezone: str = "Europe/Berlin"


class FamilyCreate(FamilyBase):
    pass


class FamilyUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    settings: dict | None = None


class FamilyResponse(FamilyBase):
    id: uuid.UUID
    settings: dict = {}
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
