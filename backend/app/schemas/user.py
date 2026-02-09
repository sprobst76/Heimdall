import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str
    role: str  # parent | child


class ChildCreate(BaseModel):
    name: str
    age: int | None = None
    avatar_url: str | None = None
    pin: str | None = None  # 4-6 digit PIN for child app


class ChildUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    avatar_url: str | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    family_id: uuid.UUID
    email: str | None = None
    avatar_url: str | None = None
    age: int | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
