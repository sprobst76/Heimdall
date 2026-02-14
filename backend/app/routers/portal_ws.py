"""Parent Portal WebSocket router.

Provides a WebSocket endpoint for the parent dashboard to receive
real-time invalidation events instead of polling.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.services.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Portal WebSocket"])


@router.websocket("/ws")
async def portal_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for the parent portal.

    Protocol:
    1. Client connects and sends JWT access_token as first text message
    2. Server validates token, checks parent role
    3. On success: sends auth_ok, registers connection
    4. Server pushes invalidation events: { type: "invalidate", keys: [...] }
    5. Client can send "ping" → server replies "pong"
    """
    await websocket.accept()
    family_id = None

    try:
        # First message must be the JWT access token
        token = await websocket.receive_text()

        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            if user_id is None or token_type != "access":
                await websocket.send_json({"type": "auth_error", "detail": "Invalid token"})
                await websocket.close(code=4001)
                return
        except JWTError:
            await websocket.send_json({"type": "auth_error", "detail": "Invalid token"})
            await websocket.close(code=4001)
            return

        # Load user and verify parent role
        from app.models.user import User
        from uuid import UUID

        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if user is None or user.role != "parent":
            await websocket.send_json({"type": "auth_error", "detail": "Parent role required"})
            await websocket.close(code=4003)
            return

        family_id = user.family_id

        await websocket.send_json({
            "type": "auth_ok",
            "user_id": str(user.id),
            "family_id": str(family_id),
        })

        # Register connection
        await connection_manager.connect_parent(family_id, websocket)

        # Message loop
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if family_id is not None:
            await connection_manager.disconnect_parent(family_id, websocket)
