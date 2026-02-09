from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Extract and validate the JWT from the Authorization header.

    Returns the User ORM instance for the authenticated user.

    Raises:
        HTTPException 401: If the token is missing, invalid, or the user
            does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Import here to avoid circular imports (models -> database -> dependencies)
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def require_parent(
    current_user=Depends(get_current_user),
):
    """Dependency that ensures the current user has the 'parent' role.

    Raises:
        HTTPException 403: If the user is not a parent.
    """
    if current_user.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent role required",
        )
    return current_user


async def require_child(
    current_user=Depends(get_current_user),
):
    """Dependency that ensures the current user has the 'child' role.

    Raises:
        HTTPException 403: If the user is not a child.
    """
    if current_user.role != "child":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Child role required",
        )
    return current_user


def require_family_member(family_id_param: str = "family_id"):
    """Factory that returns a dependency checking family membership.

    Verifies the authenticated user belongs to the family identified by
    the given path parameter.  Family membership is determined by the
    ``User.family_id`` foreign key.

    Args:
        family_id_param: The name of the path parameter containing the
            family UUID (default ``"family_id"``).

    Usage::

        @router.get("/families/{family_id}/tasks")
        async def list_tasks(
            family_id: UUID,
            user=Depends(require_family_member()),
        ):
            ...
    """

    async def _check_family_member(
        current_user=Depends(get_current_user),
        family_id: UUID | None = None,
    ):
        if family_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Family ID is required",
            )

        if current_user.family_id != family_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this family",
            )

        return current_user

    return _check_family_member
