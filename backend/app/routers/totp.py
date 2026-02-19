"""TOTP parent authorization endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_child, require_parent
from app.core.rate_limit import limiter
from app.database import get_db
from app.models.family import Family
from app.models.user import User
from app.schemas.totp import (
    TotpSetupResponse,
    TotpSettingsUpdate,
    TotpStatusResponse,
    TotpUnlockRequest,
    TotpUnlockResponse,
)
from app.services.totp_service import (
    generate_totp_secret,
    get_provisioning_uri,
    process_totp_unlock,
    verify_totp_code,
)

router = APIRouter(tags=["TOTP"])

VALID_MODES = {"tan", "override", "both"}


async def _get_child(
    db: AsyncSession,
    child_id: uuid.UUID,
    current_user: User,
) -> User:
    """Verify parent has access to the child and return the child."""
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kind nicht gefunden")
    if child.family_id != current_user.family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Zugriff auf dieses Kind")
    return child


async def _get_family_name(db: AsyncSession, family_id: uuid.UUID) -> str:
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()
    return family.name if family else "Familie"


# ---------------------------------------------------------------------------
# Parent endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/children/{child_id}/totp/setup",
    response_model=TotpSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def setup_totp(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> TotpSetupResponse:
    """Generate a new TOTP secret for a child. Returns QR provisioning URI."""
    child = await _get_child(db, child_id, current_user)
    family_name = await _get_family_name(db, child.family_id)

    secret = generate_totp_secret()
    uri = get_provisioning_uri(secret, child.name, family_name)

    child.totp_secret = secret
    child.totp_enabled = True
    await db.commit()

    return TotpSetupResponse(secret=secret, provisioning_uri=uri)


@router.get(
    "/children/{child_id}/totp/status",
    response_model=TotpStatusResponse,
)
async def get_totp_status(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> TotpStatusResponse:
    """Get TOTP configuration for a child."""
    child = await _get_child(db, child_id, current_user)

    return TotpStatusResponse(
        enabled=child.totp_enabled,
        mode=child.totp_mode,
        tan_minutes=child.totp_tan_minutes,
        override_minutes=child.totp_override_minutes,
    )


@router.put(
    "/children/{child_id}/totp/settings",
    response_model=TotpStatusResponse,
)
async def update_totp_settings(
    child_id: uuid.UUID,
    body: TotpSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> TotpStatusResponse:
    """Update TOTP mode and duration settings."""
    child = await _get_child(db, child_id, current_user)

    if body.mode is not None:
        child.totp_mode = body.mode
    if body.tan_minutes is not None:
        child.totp_tan_minutes = body.tan_minutes
    if body.override_minutes is not None:
        child.totp_override_minutes = body.override_minutes

    await db.commit()

    return TotpStatusResponse(
        enabled=child.totp_enabled,
        mode=child.totp_mode,
        tan_minutes=child.totp_tan_minutes,
        override_minutes=child.totp_override_minutes,
    )


@router.delete(
    "/children/{child_id}/totp",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disable_totp(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
) -> None:
    """Disable TOTP and delete the secret for a child."""
    child = await _get_child(db, child_id, current_user)

    child.totp_enabled = False
    child.totp_secret = None
    await db.commit()


# ---------------------------------------------------------------------------
# Child unlock endpoint (called from Flutter app)
# ---------------------------------------------------------------------------


@router.post(
    "/children/{child_id}/totp/unlock",
    response_model=TotpUnlockResponse,
)
@limiter.limit("10/minute")
async def unlock_totp(
    request: Request,
    child_id: uuid.UUID,
    body: TotpUnlockRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_child),
) -> TotpUnlockResponse:
    """Validate a TOTP code and unlock the child's device.

    The child (via Flutter app) submits the 6-digit code from the parent's
    authenticator. On success, an active TAN is created that grants the
    configured bonus time or override.
    """
    # Verify the child is unlocking their own account
    if current_user.id != child_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff",
        )

    # Fetch child record (has TOTP fields)
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kind nicht gefunden")

    if not child.totp_enabled or child.totp_secret is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP ist für dieses Kind nicht aktiviert",
        )

    # Validate that the requested mode is allowed
    if child.totp_mode != "both" and body.mode != child.totp_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modus '{body.mode}' ist nicht erlaubt. Konfiguriert: '{child.totp_mode}'",
        )

    # Verify the TOTP code
    if not verify_totp_code(child.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger Code",
        )

    result_data = await process_totp_unlock(db, child, body.mode)
    await db.commit()

    return TotpUnlockResponse(**result_data)
