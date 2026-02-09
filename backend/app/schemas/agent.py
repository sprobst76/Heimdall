import uuid
from datetime import datetime

from pydantic import BaseModel


class HeartbeatRequest(BaseModel):
    timestamp: datetime
    battery_level: int | None = None
    active_app: str | None = None


class HeartbeatResponse(BaseModel):
    status: str = "ok"
    server_time: datetime


class UsageEventRequest(BaseModel):
    app_package: str | None = None
    app_group_id: uuid.UUID | None = None
    event_type: str  # start | stop | blocked
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None


class UsageEventResponse(BaseModel):
    id: uuid.UUID
    status: str = "recorded"


class ResolvedRules(BaseModel):
    day_type: str
    time_windows: list[dict] = []
    group_limits: list[dict] = []
    daily_limit_minutes: int | None = None
    active_tans: list[dict] = []
