"""Invitation Service.

Generate unique invitation codes for family join requests.
"""

import random

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import FamilyInvitation
from app.services.tan_service import WORD_LIST


def _generate_code() -> str:
    """Generate an invitation code like 'FREYA-4821'."""
    word = random.choice(WORD_LIST)
    digits = f"{random.randint(0, 9999):04d}"
    return f"{word}-{digits}"


async def generate_invitation_code(db: AsyncSession) -> str:
    """Generate a unique invitation code, retrying on collision."""
    for _ in range(10):
        code = _generate_code()
        result = await db.execute(
            select(FamilyInvitation).where(FamilyInvitation.code == code)
        )
        if result.scalar_one_or_none() is None:
            return code

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Einladungscode konnte nicht generiert werden",
    )
