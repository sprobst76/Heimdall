"""TOTP Service.

Business logic for TOTP setup, verification, and unlock processing.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tan import TAN
from app.models.user import User
from app.services.tan_service import generate_tan_code


def generate_totp_secret() -> str:
    """Generate a cryptographically random Base32-encoded TOTP secret."""
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, child_name: str, family_name: str) -> str:
    """Return the otpauth:// URI for QR code display in authenticator apps."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=child_name,
        issuer_name=f"Heimdall – {family_name}",
    )


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code. Allows ±30 seconds clock drift (valid_window=1)."""
    return pyotp.TOTP(secret).verify(code, valid_window=1)


async def process_totp_unlock(
    db: AsyncSession,
    child: User,
    mode: str,
) -> dict:
    """Create a TAN for the TOTP unlock and return the result.

    For mode='tan': creates a time TAN worth totp_tan_minutes.
    For mode='override': creates an override TAN lasting totp_override_minutes.
    """
    now = datetime.now(timezone.utc)

    if mode == "tan":
        minutes = child.totp_tan_minutes
        tan_type = "time"
        expires_at = now + timedelta(hours=24)
    else:  # override
        minutes = child.totp_override_minutes
        tan_type = "override"
        expires_at = now + timedelta(minutes=minutes)

    code = await generate_tan_code(db)
    tan = TAN(
        id=uuid.uuid4(),
        child_id=child.id,
        code=code,
        type=tan_type,
        value_minutes=minutes if tan_type == "time" else None,
        expires_at=expires_at,
        single_use=True,
        source="totp",
        status="active",
    )
    db.add(tan)
    await db.flush()

    return {"unlocked": True, "mode": mode, "minutes": minutes}
