import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TANCreate(BaseModel):
    type: str  # time | group_unlock | extend_window | override
    scope_groups: list[uuid.UUID] | None = None
    scope_devices: list[uuid.UUID] | None = None
    value_minutes: int | None = None
    value_unlock_until: str | None = None  # "HH:MM"
    expires_at: datetime | None = None  # defaults to end of day
    single_use: bool = True


class TANRedeemRequest(BaseModel):
    code: str


class TANResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    code: str
    type: str
    scope_groups: list[uuid.UUID] | None = None
    scope_devices: list[uuid.UUID] | None = None
    value_minutes: int | None = None
    value_unlock_until: str | None = None
    expires_at: datetime
    single_use: bool
    source: str | None = None
    status: str
    redeemed_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
