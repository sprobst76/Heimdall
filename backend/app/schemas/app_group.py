import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppCreate(BaseModel):
    app_name: str
    app_package: str | None = None
    app_executable: str | None = None
    platform: str  # android | windows | ios


class AppResponse(BaseModel):
    id: uuid.UUID
    app_name: str
    app_package: str | None = None
    app_executable: str | None = None
    platform: str
    model_config = ConfigDict(from_attributes=True)


class AppGroupCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None
    category: str
    risk_level: str = "medium"
    always_allowed: bool = False
    tan_allowed: bool = True
    max_tan_bonus_per_day: int | None = None


class AppGroupUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    category: str | None = None
    risk_level: str | None = None
    always_allowed: bool | None = None
    tan_allowed: bool | None = None
    max_tan_bonus_per_day: int | None = None


class AppGroupResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    icon: str | None = None
    color: str | None = None
    category: str
    risk_level: str
    always_allowed: bool
    tan_allowed: bool
    max_tan_bonus_per_day: int | None = None
    apps: list[AppResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
