"""Devices router.

Endpoints for managing devices assigned to children.
"""

import hashlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_parent
from app.database import get_db
from app.models.device import Device, DeviceCoupling
from app.models.user import User
from app.schemas.device import (
    DeviceCouplingCreate,
    DeviceCouplingResponse,
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
)

router = APIRouter(prefix="/children/{child_id}/devices", tags=["Devices"])


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(token.encode()).hexdigest()


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


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    child_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """List all devices for a child."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(Device).where(Device.child_id == child_id)
    )
    return result.scalars().all()


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_device(
    child_id: uuid.UUID,
    body: DeviceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Register a new device for a child. Returns the device_token once."""
    await _verify_child_access(db, child_id, current_user)

    # Check for duplicate device_identifier
    existing = await db.execute(
        select(Device).where(Device.device_identifier == body.device_identifier)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device identifier already registered",
        )

    # Generate a unique device token
    raw_token = secrets.token_urlsafe(48)

    device = Device(
        child_id=child_id,
        name=body.name,
        type=body.type,
        device_identifier=body.device_identifier,
        device_token_hash=_hash_token(raw_token),
        status="active",
    )
    db.add(device)
    await db.flush()
    await db.refresh(device)

    return {
        "device": DeviceResponse.model_validate(device),
        "device_token": raw_token,  # Only returned once at registration
    }


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    child_id: uuid.UUID,
    device_id: uuid.UUID,
    body: DeviceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user),
):
    """Update a device."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(Device).where(
            Device.id == device_id,
            Device.child_id == child_id,
        )
    )
    device = result.scalar_one_or_none()

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.flush()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    child_id: uuid.UUID,
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Remove a device. Requires parent role."""
    await _verify_child_access(db, child_id, current_user)

    result = await db.execute(
        select(Device).where(
            Device.id == device_id,
            Device.child_id == child_id,
        )
    )
    device = result.scalar_one_or_none()

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    await db.delete(device)
    await db.flush()
    return None


@router.put("/{device_id}/coupling", response_model=DeviceCouplingResponse)
async def set_device_coupling(
    child_id: uuid.UUID,
    device_id: uuid.UUID,
    body: DeviceCouplingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(require_parent),
):
    """Set device coupling for a child (shared screen-time budget)."""
    await _verify_child_access(db, child_id, current_user)

    # Verify the device belongs to this child
    result = await db.execute(
        select(Device).where(
            Device.id == device_id,
            Device.child_id == child_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Ensure the target device is included in the coupling list
    if device_id not in body.device_ids:
        body.device_ids.append(device_id)

    # Check if a coupling already exists for this child; update or create
    existing_result = await db.execute(
        select(DeviceCoupling).where(DeviceCoupling.child_id == child_id)
    )
    coupling = existing_result.scalar_one_or_none()

    if coupling is not None:
        coupling.device_ids = body.device_ids
        coupling.shared_budget = body.shared_budget
    else:
        coupling = DeviceCoupling(
            child_id=child_id,
            device_ids=body.device_ids,
            shared_budget=body.shared_budget,
        )
        db.add(coupling)

    await db.flush()
    await db.refresh(coupling)
    return coupling
