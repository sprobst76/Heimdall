import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from sqlalchemy import select

from app.config import settings
from app.core.rate_limit import limiter
from app.routers import agent, analytics, app_groups, auth, children, day_types, devices, families, llm, portal_ws, quests, tan_schedules, tans, time_rules, totp, uploads, usage_rewards

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quest Scheduler background task
# ---------------------------------------------------------------------------
async def _quest_scheduler_loop() -> None:
    """Run quest scheduling at startup then daily at 00:05 UTC."""
    from app.database import async_session
    from app.services.quest_scheduler import schedule_daily_quests

    while True:
        try:
            async with async_session() as db:
                count = await schedule_daily_quests(db)
                await db.commit()
                logger.info("Quest scheduler: %d instances created", count)
        except Exception:
            logger.exception("Quest scheduler error")

        # Sleep until tomorrow 00:05 UTC
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=5, second=0, microsecond=0,
        )
        await asyncio.sleep((tomorrow - now).total_seconds())


# ---------------------------------------------------------------------------
# Usage Reward Scheduler background task
# ---------------------------------------------------------------------------
async def _usage_reward_loop() -> None:
    """Evaluate usage reward rules daily at 00:10 UTC."""
    from app.database import async_session
    from app.services.usage_reward_service import evaluate_daily_rewards

    while True:
        try:
            async with async_session() as db:
                count = await evaluate_daily_rewards(db)
                await db.commit()
                logger.info("Usage rewards: %d TANs generated", count)
        except Exception:
            logger.exception("Usage reward scheduler error")

        # Sleep until tomorrow 00:10 UTC
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=10, second=0, microsecond=0,
        )
        await asyncio.sleep((tomorrow - now).total_seconds())


# ---------------------------------------------------------------------------
# TAN Schedule background task
# ---------------------------------------------------------------------------
async def _tan_schedule_loop() -> None:
    """Generate scheduled TANs daily at 00:15 UTC."""
    from app.database import async_session
    from app.services.tan_scheduler import run_tan_schedules

    while True:
        try:
            async with async_session() as db:
                count = await run_tan_schedules(db)
                await db.commit()
                logger.info("TAN scheduler: %d TANs generated", count)
        except Exception:
            logger.exception("TAN scheduler error")

        # Sleep until tomorrow 00:15 UTC
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=15, second=0, microsecond=0,
        )
        await asyncio.sleep((tomorrow - now).total_seconds())


# ---------------------------------------------------------------------------
# Holiday Sync background task
# ---------------------------------------------------------------------------
async def _holiday_sync_loop() -> None:
    """Sync holidays once at startup, then yearly on Jan 1st."""
    from app.database import async_session
    from app.models.family import Family
    from app.services.holiday_service import sync_holidays_to_db

    while True:
        try:
            async with async_session() as db:
                families = (await db.execute(select(Family))).scalars().all()
                year = datetime.now(timezone.utc).year
                for family in families:
                    await sync_holidays_to_db(db, family.id, year)
                    await sync_holidays_to_db(db, family.id, year + 1)
                await db.commit()
                logger.info("Holiday sync: %d families synced", len(families))
        except Exception:
            logger.exception("Holiday sync error")

        # Sleep until Jan 1st next year 00:15 UTC
        now = datetime.now(timezone.utc)
        next_jan = now.replace(
            year=now.year + 1, month=1, day=1,
            hour=0, minute=15, second=0, microsecond=0,
        )
        await asyncio.sleep((next_jan - now).total_seconds())


# ---------------------------------------------------------------------------
# Lifespan context manager
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan: runs on startup and shutdown."""
    logger.info("Heimdall API started")
    scheduler_task = asyncio.create_task(_quest_scheduler_loop())
    reward_task = asyncio.create_task(_usage_reward_loop())
    tan_schedule_task = asyncio.create_task(_tan_schedule_loop())
    holiday_task = asyncio.create_task(_holiday_sync_loop())
    yield
    holiday_task.cancel()
    tan_schedule_task.cancel()
    reward_task.cancel()
    scheduler_task.cancel()
    logger.info("Heimdall API shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)


MAX_BODY_SIZE = 12 * 1024 * 1024  # 12 MB (slightly above 10 MB upload limit)


# -- Middleware ---------------------------------------------------------------
@app.middleware("http")
async def limit_request_body(request: Request, call_next):
    """Reject requests with Content-Length exceeding the limit."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
        )
    return await call_next(request)


@app.middleware("http")
async def fix_redirect_scheme(request: Request, call_next):
    """Ensure redirects use https when behind a TLS-terminating reverse proxy."""
    if request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Device-Token"],
)

# -- Rate limiting ------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": settings.APP_NAME}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(families.router, prefix=settings.API_V1_PREFIX)
app.include_router(children.router, prefix=settings.API_V1_PREFIX)
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)
app.include_router(app_groups.router, prefix=settings.API_V1_PREFIX)
app.include_router(time_rules.router, prefix=settings.API_V1_PREFIX)
app.include_router(day_types.router, prefix=settings.API_V1_PREFIX)
app.include_router(tans.router, prefix=settings.API_V1_PREFIX)
app.include_router(quests.router, prefix=settings.API_V1_PREFIX)
app.include_router(uploads.router, prefix=settings.API_V1_PREFIX)
app.include_router(llm.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(agent.router, prefix=settings.API_V1_PREFIX)
app.include_router(usage_rewards.router, prefix=settings.API_V1_PREFIX)
app.include_router(tan_schedules.router, prefix=settings.API_V1_PREFIX)
app.include_router(totp.router, prefix=settings.API_V1_PREFIX)
app.include_router(portal_ws.router, prefix=settings.API_V1_PREFIX)
