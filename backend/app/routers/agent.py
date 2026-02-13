"""Agent router.

Endpoints for device agents: heartbeat, usage reporting, rule fetching,
and WebSocket communication.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.usage import UsageEvent
from app.schemas.agent import (
    HeartbeatRequest,
    HeartbeatResponse,
    ResolvedRules,
    UsageEventRequest,
    UsageEventResponse,
)
from app.services.connection_manager import connection_manager
from app.services.rule_engine import get_current_rules

router = APIRouter(prefix="/agent", tags=["Device Agent"])


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_device_by_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_device_token: str = Header(..., description="Device authentication token"),
) -> Device:
    """Authenticate a device via the X-Device-Token header."""
    token_hash = _hash_token(x_device_token)

    result = await db.execute(
        select(Device).where(
            Device.device_token_hash == token_hash,
            Device.status == "active",
        )
    )
    device = result.scalar_one_or_none()

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive device token",
        )

    return device


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    body: HeartbeatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    device: Device = Depends(get_device_by_token),
):
    """Device sends a heartbeat to report its status."""
    device.last_seen = datetime.now(timezone.utc)
    await db.flush()

    return HeartbeatResponse(
        status="ok",
        server_time=datetime.now(timezone.utc),
    )


@router.post("/usage-event", response_model=UsageEventResponse)
async def report_usage_event(
    body: UsageEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    device: Device = Depends(get_device_by_token),
):
    """Report an app usage event from the device agent."""
    event = UsageEvent(
        device_id=device.id,
        child_id=device.child_id,
        app_package=body.app_package,
        app_group_id=body.app_group_id,
        event_type=body.event_type,
        started_at=body.started_at,
        ended_at=body.ended_at,
        duration_seconds=body.duration_seconds,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    return UsageEventResponse(id=event.id, status="recorded")


@router.get("/rules/current", response_model=ResolvedRules)
async def get_rules_for_device(
    db: Annotated[AsyncSession, Depends(get_db)],
    device: Device = Depends(get_device_by_token),
):
    """Get the current active rules resolved for this device."""
    rules = await get_current_rules(db, device.id)
    return rules


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time device agent communication.

    The device must send its device token as the first message after
    connecting. The server validates the token and then enters a
    bidirectional message loop.

    Server can push: rules_updated, block, unblock, tan_activated.
    Device can send: ping, heartbeat, usage_update, status_report.
    """
    await websocket.accept()
    device = None

    try:
        # First message must be the device token for authentication
        auth_message = await websocket.receive_text()
        token_hash = _hash_token(auth_message)

        result = await db.execute(
            select(Device).where(
                Device.device_token_hash == token_hash,
                Device.status == "active",
            )
        )
        device = result.scalar_one_or_none()

        if device is None:
            await websocket.send_json({"error": "Invalid device token"})
            await websocket.close(code=4001)
            return

        await websocket.send_json({
            "type": "auth_ok",
            "device_id": str(device.id),
        })

        # Update last seen
        device.last_seen = datetime.now(timezone.utc)
        await db.flush()

        # Register connection for bidirectional push
        await connection_manager.connect(device.id, device.child_id, websocket)

        # Message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })
            elif msg_type == "heartbeat":
                device.last_seen = datetime.now(timezone.utc)
                await db.flush()
                await websocket.send_json({
                    "type": "heartbeat_ack",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })
            elif msg_type == "usage_update":
                if data.get("app_package") and data.get("duration_seconds"):
                    event = UsageEvent(
                        device_id=device.id,
                        child_id=device.child_id,
                        app_package=data["app_package"],
                        app_group_id=uuid.UUID(data["app_group_id"]) if data.get("app_group_id") else None,
                        event_type="update",
                        duration_seconds=data["duration_seconds"],
                        started_at=datetime.now(timezone.utc),
                    )
                    db.add(event)
                    await db.flush()
                await websocket.send_json({
                    "type": "ack",
                    "received_type": "usage_update",
                })
            elif msg_type == "status_report":
                await websocket.send_json({
                    "type": "ack",
                    "received_type": "status_report",
                })
            else:
                # Unknown message type - acknowledge but do nothing
                await websocket.send_json({
                    "type": "ack",
                    "received_type": msg_type,
                })

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if device is not None:
            await connection_manager.disconnect(device.id, device.child_id)
