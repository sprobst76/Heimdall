"""App Groups router.

Endpoints for managing app groups and their member apps for a child.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.app_group import AppGroup, AppGroupApp
from app.models.user import User
from app.schemas.app_group import (
    AppCreate,
    AppGroupCreate,
    AppGroupResponse,
    AppGroupUpdate,
    AppResponse,
)
from app.services.rule_push_service import push_rules_to_child_devices

router = APIRouter(prefix="/children/{child_id}/app-groups", tags=["App Groups"])


async def _verify_child_access(
    db: AsyncSession, child_id: uuid.UUID, current_user: User
) -> User:
    """Verify the current user has access to this child's data."""
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()

    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child not found",
        )

    if child.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this family",
        )

    return child


@router.get("/", response_model=list[AppGroupResponse])
async def list_app_groups(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """List all app groups for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup)
        .where(AppGroup.child_id == child_id)
        .options(selectinload(AppGroup.apps))
    )
    return result.scalars().all()


@router.post("/", response_model=AppGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_app_group(
    child_id: uuid.UUID,
    body: AppGroupCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Create a new app group for a child."""
    await _verify_child_access(db, child_id, current_user)

    group = AppGroup(
        child_id=child_id,
        name=body.name,
        icon=body.icon,
        color=body.color,
        category=body.category,
        risk_level=body.risk_level,
        always_allowed=body.always_allowed,
        tan_allowed=body.tan_allowed,
        max_tan_bonus_per_day=body.max_tan_bonus_per_day,
    )
    db.add(group)
    await db.flush()
    await db.refresh(group, attribute_names=["apps"])
    await push_rules_to_child_devices(db, child_id)
    return group


@router.get("/{group_id}", response_model=AppGroupResponse)
async def get_app_group(
    child_id: uuid.UUID,
    group_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Get an app group with its apps."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup)
        .where(AppGroup.id == group_id, AppGroup.child_id == child_id)
        .options(selectinload(AppGroup.apps))
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App group not found",
        )

    return group


@router.put("/{group_id}", response_model=AppGroupResponse)
async def update_app_group(
    child_id: uuid.UUID,
    group_id: uuid.UUID,
    body: AppGroupUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Update an app group."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup)
        .where(AppGroup.id == group_id, AppGroup.child_id == child_id)
        .options(selectinload(AppGroup.apps))
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App group not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.flush()
    await db.refresh(group)
    await push_rules_to_child_devices(db, child_id)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_app_group(
    child_id: uuid.UUID,
    group_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Delete an app group and its apps (cascade)."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup).where(
            AppGroup.id == group_id,
            AppGroup.child_id == child_id,
        )
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App group not found",
        )

    await db.delete(group)
    await db.flush()
    await push_rules_to_child_devices(db, child_id)
    return None


@router.put("/{group_id}/apps", response_model=list[AppResponse])
async def set_apps_for_group(
    child_id: uuid.UUID,
    group_id: uuid.UUID,
    apps: list[AppCreate],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Replace all apps in a group with the provided list."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup)
        .where(AppGroup.id == group_id, AppGroup.child_id == child_id)
        .options(selectinload(AppGroup.apps))
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App group not found",
        )

    # Delete existing apps
    for existing_app in group.apps:
        await db.delete(existing_app)
    await db.flush()

    # Create new apps
    new_apps = []
    for app_data in apps:
        app_entry = AppGroupApp(
            group_id=group_id,
            app_name=app_data.app_name,
            app_package=app_data.app_package,
            app_executable=app_data.app_executable,
            platform=app_data.platform,
        )
        db.add(app_entry)
        new_apps.append(app_entry)

    await db.flush()
    for app_entry in new_apps:
        await db.refresh(app_entry)

    await push_rules_to_child_devices(db, child_id)
    return new_apps


@router.post("/{group_id}/apps", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def add_app_to_group(
    child_id: uuid.UUID,
    group_id: uuid.UUID,
    body: AppCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Add a single app to a group."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(AppGroup).where(
            AppGroup.id == group_id,
            AppGroup.child_id == child_id,
        )
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App group not found",
        )

    app_entry = AppGroupApp(
        group_id=group_id,
        app_name=body.app_name,
        app_package=body.app_package,
        app_executable=body.app_executable,
        platform=body.platform,
    )
    db.add(app_entry)
    await db.flush()
    await db.refresh(app_entry)
    await push_rules_to_child_devices(db, child_id)
    return app_entry
