"""Children router.

Endpoints for managing child users within a family.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_family_member, require_parent
from app.core.security import get_password_hash
from app.database import get_db
from app.models.user import User
from app.schemas.user import ChildCreate, ChildPinReset, ChildUpdate, UserResponse

router = APIRouter(prefix="/families/{family_id}/children", tags=["Children"])


@router.get("/", response_model=list[UserResponse])
async def list_children(
    family_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
):
    """List all children in a family."""
    result = await db.execute(
        select(User).where(
            User.family_id == family_id,
            User.role == "child",
        )
    )
    return result.scalars().all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_child(
    family_id: uuid.UUID,
    body: ChildCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Add a child to the family. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    child = User(
        family_id=family_id,
        name=body.name,
        role="child",
        age=body.age,
        avatar_url=body.avatar_url,
        pin_hash=get_password_hash(body.pin) if body.pin else None,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return child


@router.get("/{child_id}", response_model=UserResponse)
async def get_child(
    family_id: uuid.UUID,
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_family_member()),
):
    """Get details of a specific child."""
    result = await db.execute(
        select(User).where(
            User.id == child_id,
            User.family_id == family_id,
            User.role == "child",
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    return child


@router.put("/{child_id}", response_model=UserResponse)
async def update_child(
    family_id: uuid.UUID,
    child_id: uuid.UUID,
    body: ChildUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Update a child's information. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(User).where(
            User.id == child_id,
            User.family_id == family_id,
            User.role == "child",
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(child, field, value)

    await db.flush()
    await db.refresh(child)
    return child


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(
    family_id: uuid.UUID,
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Remove a child from the family. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    result = await db.execute(
        select(User).where(
            User.id == child_id,
            User.family_id == family_id,
            User.role == "child",
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    await db.delete(child)
    await db.flush()
    return None


@router.put("/{child_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def reset_child_pin(
    family_id: uuid.UUID,
    child_id: uuid.UUID,
    body: ChildPinReset,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Reset a child's PIN. Requires parent role."""
    if current_user.family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sie sind kein Mitglied dieser Familie",
        )

    result = await db.execute(
        select(User).where(
            User.id == child_id,
            User.family_id == family_id,
            User.role == "child",
        )
    )
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kind nicht gefunden",
        )

    child.pin_hash = get_password_hash(body.pin)
    await db.flush()
    return None
