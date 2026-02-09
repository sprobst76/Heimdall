import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceCreate(BaseModel):
    name: str
    type: str  # android | windows | ios
    device_identifier: str


class DeviceUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class DeviceResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    type: str
    device_identifier: str
    status: str
    last_seen: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeviceCouplingCreate(BaseModel):
    device_ids: list[uuid.UUID]
    shared_budget: bool = True


class DeviceCouplingResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    device_ids: list[uuid.UUID]
    shared_budget: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
