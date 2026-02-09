"""Families router.

Endpoints for viewing and updating family settings and members.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_family_member, require_parent
from app.database import get_db
from app.models.family import Family
from app.models.user import User
from app.schemas.family import FamilyResponse, FamilyUpdate
from app.schemas.user import UserResponse

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

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
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
