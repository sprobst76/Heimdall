import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvitationCreate(BaseModel):
    role: str = "parent"


class InvitationResponse(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    code: str
    role: str
    created_by: uuid.UUID
    expires_at: datetime
    used_by: uuid.UUID | None = None
    used_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
