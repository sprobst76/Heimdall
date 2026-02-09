"""Authentication router.

Endpoints for login, registration, token refresh, and logout.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.database import get_db
from app.models.family import Family
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_tokens_for_user(
    db: AsyncSession, user: User
) -> TokenResponse:
    """Create an access + refresh token pair and persist the refresh token."""
    access_token = create_access_token(data={"sub": str(user.id)})
    raw_refresh = create_refresh_token(data={"sub": str(user.id)})

    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_record)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate a user with email + password and return tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return await _create_tokens_for_user(db, user)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new parent user and create their family."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create family
    family = Family(name=body.family_name)
    db.add(family)
    await db.flush()

    # Create parent user
    user = User(
        family_id=family.id,
        name=body.name,
        role="parent",
        email=body.email,
        password_hash=get_password_hash(body.password),
    )
    db.add(user)
    await db.flush()

    return await _create_tokens_for_user(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange a valid refresh token for a new token pair (rotation)."""
    # Decode the refresh JWT to get the user id
    try:
        payload = decode_token(body.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Look up the stored refresh token by hash
    token_hash = _hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or already revoked",
        )

    expires = stored_token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Revoke the old token (rotation)
    stored_token.revoked = True
    await db.flush()

    # Fetch the user and issue new tokens
    user_result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return await _create_tokens_for_user(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Revoke the provided refresh token."""
    token_hash = _hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is not None:
        stored_token.revoked = True
        await db.flush()

    # Always return 204 regardless of whether the token was found
    return None
