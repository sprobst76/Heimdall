import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TanScheduleCreate(BaseModel):
    name: str
    recurrence: str  # daily | weekdays | weekends | school_days
    tan_type: str  # time | group_unlock | extend_window | override
    value_minutes: int | None = None
    value_unlock_until: str | None = None  # "HH:MM"
    scope_groups: list[uuid.UUID] | None = None
    scope_devices: list[uuid.UUID] | None = None
    expires_after_hours: int = 24


class TanScheduleUpdate(BaseModel):
    name: str | None = None
    recurrence: str | None = None
    tan_type: str | None = None
    value_minutes: int | None = None
    value_unlock_until: str | None = None
    scope_groups: list[uuid.UUID] | None = None
    scope_devices: list[uuid.UUID] | None = None
    expires_after_hours: int | None = None
    active: bool | None = None


class TanScheduleResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    recurrence: str
    tan_type: str
    value_minutes: int | None = None
    value_unlock_until: str | None = None
    scope_groups: list[uuid.UUID] | None = None
    scope_devices: list[uuid.UUID] | None = None
    expires_after_hours: int
    active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TanScheduleLogResponse(BaseModel):
    id: uuid.UUID
    schedule_id: uuid.UUID
    generated_date: str
    generated_tan_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
