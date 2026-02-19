"""TOTP schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class TotpSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TotpStatusResponse(BaseModel):
    enabled: bool
    mode: str
    tan_minutes: int
    override_minutes: int


class TotpSettingsUpdate(BaseModel):
    mode: Optional[str] = Field(None, pattern="^(tan|override|both)$")
    tan_minutes: Optional[int] = Field(None, ge=5, le=480)
    override_minutes: Optional[int] = Field(None, ge=5, le=480)


class TotpUnlockRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")
    mode: str = Field("tan", pattern="^(tan|override)$")


class TotpUnlockResponse(BaseModel):
    unlocked: bool
    mode: str
    minutes: int
