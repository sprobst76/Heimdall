import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UsageRewardRuleCreate(BaseModel):
    name: str
    trigger_type: str  # daily_under | streak_under | group_free
    threshold_minutes: int
    target_group_id: uuid.UUID | None = None
    streak_days: int | None = None
    reward_minutes: int
    reward_group_ids: list[uuid.UUID] | None = None


class UsageRewardRuleUpdate(BaseModel):
    name: str | None = None
    trigger_type: str | None = None
    threshold_minutes: int | None = None
    target_group_id: uuid.UUID | None = None
    streak_days: int | None = None
    reward_minutes: int | None = None
    reward_group_ids: list[uuid.UUID] | None = None
    active: bool | None = None


class UsageRewardRuleResponse(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    name: str
    trigger_type: str
    threshold_minutes: int
    target_group_id: uuid.UUID | None = None
    streak_days: int | None = None
    reward_minutes: int
    reward_group_ids: list[uuid.UUID] | None = None
    active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UsageRewardLogResponse(BaseModel):
    id: uuid.UUID
    rule_id: uuid.UUID
    child_id: uuid.UUID
    evaluated_date: date
    usage_minutes: int
    threshold_minutes: int
    rewarded: bool
    generated_tan_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
