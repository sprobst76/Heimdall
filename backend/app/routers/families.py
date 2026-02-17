"""Families router.

Endpoints for viewing and updating family settings, members, and invitations.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_family_member, require_parent
from app.database import get_db
from app.models.family import Family
from app.models.invitation import FamilyInvitation
from app.models.user import User
from app.schemas.family import FamilyResponse, FamilyUpdate
from app.schemas.invitation import InvitationCreate, InvitationResponse
from app.schemas.user import UserResponse
from app.services.invitation_service import generate_invitation_code

router = APIRouter(prefix="/families", tags=["Families"])


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
):
    """Get family details. Requires the caller to be a family member."""
    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()

    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    return family


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: uuid.UUID,
    body: FamilyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Update family settings. Requires parent role."""
    # Verify parent belongs to this family
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(select(Family).where(Family.id == family_id))
    family = result.scalar_one_or_none()

    if family is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found",
        )

    _allowed = {"name", "timezone", "settings"}
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in _allowed:
            setattr(family, field, value)

    await db.flush()
    await db.refresh(family)
    return family


@router.get("/{family_id}/members", response_model=list[UserResponse])
async def list_family_members(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
):
    """List all members of a family."""
    result = await db.execute(
        select(User).where(User.family_id == family_id)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

@router.post(
    "/{family_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    family_id: uuid.UUID,
    body: InvitationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Create a family invitation code. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie sind kein Mitglied dieser Familie",
        )

    code = await generate_invitation_code(db)
    invitation = FamilyInvitation(
        family_id=family_id,
        code=code,
        role=body.role,
        created_by=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()
    await db.refresh(invitation)
    return invitation


@router.get("/{family_id}/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
):
    """List active (unused, non-expired) invitations for a family."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(FamilyInvitation).where(
            FamilyInvitation.family_id == family_id,
            FamilyInvitation.used_by.is_(None),
            FamilyInvitation.expires_at > now,
        ).order_by(FamilyInvitation.created_at.desc())
    )
    return result.scalars().all()


@router.delete(
    "/{family_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_invitation(
    family_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Revoke an invitation. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie sind kein Mitglied dieser Familie",
        )

    result = await db.execute(
        select(FamilyInvitation).where(
            FamilyInvitation.id == invitation_id,
            FamilyInvitation.family_id == family_id,
        )
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Einladung nicht gefunden",
        )

    await db.delete(invitation)
    await db.flush()
    return None
