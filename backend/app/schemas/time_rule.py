import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TimeWindow(BaseModel):
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    note: str | None = None


class GroupLimit(BaseModel):
    group_id: uuid.UUID
    max_minutes: int


class TimeRuleCreate(BaseModel):
    name: str
    target_type: str  # device | app_group
    target_id: uuid.UUID | None = None
    day_types: list[str] = ["weekday"]
    time_windows: list[TimeWindow]
    daily_limit_minutes: int | None = None
    group_limits: list[GroupLimit] = []
    priority: int = 10
    valid_from: date | None = None
    valid_until: date | None = None


class TimeRuleUpdate(BaseModel):
    name: str | None = None
    day_types: list[str] | None = None
    time_windows: list[TimeWindow] | None = None
    daily_limit_minutes: int | None = None
    group_limits: list[GroupLimit] | None = None
    priority: int | None = None
    active: bool | None = None
    valid_from: date | None = None
    valid_until: date | None = None


class TimeRuleResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    target_type: str
    target_id: uuid.UUID | None = None
    day_types: list[str]
    time_windows: list[TimeWindow]
    daily_limit_minutes: int | None = None
    group_limits: list[GroupLimit]
    priority: int
    active: bool
    valid_from: date | None = None
    valid_until: date | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
