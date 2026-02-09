import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    reward_minutes: int
    tan_groups: list[uuid.UUID] | None = None
    proof_type: str  # photo | screenshot | parent_confirm | auto | checklist
    ai_verify: bool = False
    ai_prompt: str | None = None
    recurrence: str  # daily | weekly | school_days | once
    auto_detect_app: str | None = None
    auto_detect_minutes: int | None = None


class QuestTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    reward_minutes: int | None = None
    proof_type: str | None = None
    ai_verify: bool | None = None
    recurrence: str | None = None
    active: bool | None = None


class QuestTemplateResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    name: str
    description: str | None = None
    category: str
    reward_minutes: int
    tan_groups: list[uuid.UUID] | None = None
    proof_type: str
    ai_verify: bool
    recurrence: str
    active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestInstanceResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    child_id: uuid.UUID
    status: str
    claimed_at: datetime | None = None
    proof_url: str | None = None
    ai_result: dict | None = None
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    generated_tan_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestSubmitProof(BaseModel):
    proof_type: str
    proof_url: str


class QuestReview(BaseModel):
    approved: bool
    feedback: str | None = None
