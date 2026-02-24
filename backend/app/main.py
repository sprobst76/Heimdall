import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limit import limiter
from app.database import get_db
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
# Data cleanup background task
# ---------------------------------------------------------------------------
async def _cleanup_loop() -> None:
    """Delete stale data daily at 03:00 UTC.

    - UsageEvents older than 90 days (analytics reports cover max 90 days)
    - TANs with status redeemed/expired older than 30 days (audit trail)
    """
    from app.database import async_session
    from app.models.tan import TAN
    from app.models.usage import UsageEvent

    while True:
        # Sleep until 03:00 UTC today (or tomorrow if already past)
        now = datetime.now(timezone.utc)
        target = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        try:
            cutoff_usage = datetime.now(timezone.utc) - timedelta(days=90)
            cutoff_tans = datetime.now(timezone.utc) - timedelta(days=30)

            async with async_session() as db:
                result_usage = await db.execute(
                    delete(UsageEvent).where(UsageEvent.started_at < cutoff_usage)
                )
                result_tans = await db.execute(
                    delete(TAN).where(
                        TAN.status.in_(["redeemed", "expired"]),
                        TAN.expires_at < cutoff_tans,
                    )
                )
                await db.commit()
                logger.info(
                    "Cleanup: %d usage events, %d TANs removed",
                    result_usage.rowcount,
                    result_tans.rowcount,
                )
        except Exception:
            logger.exception("Cleanup error")


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
    cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    cleanup_task.cancel()
    holiday_task.cancel()
    tan_schedule_task.cancel()
    reward_task.cancel()
    scheduler_task.cancel()
    from app.core.redis_client import close_redis
    await close_redis()
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


app.add_middleware(GZipMiddleware, minimum_size=1000)
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
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check with DB and Redis connectivity verification."""
    from app.core.redis_client import get_redis

    checks: dict[str, str] = {"db": "ok", "redis": "ok"}

    try:
        await db.execute(select(1))
    except Exception:
        checks["db"] = "error"

    try:
        redis = await get_redis()
        if redis is None:
            checks["redis"] = "unavailable"
        else:
            await redis.ping()
    except Exception:
        checks["redis"] = "error"

    # "unavailable" = optional service not configured; only "error" = degraded
    degraded = any(v == "error" for v in checks.values())
    return {"status": "degraded" if degraded else "ok", "app": settings.APP_NAME, **checks}


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
