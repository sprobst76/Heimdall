"""Async Redis client singleton with graceful fallback.

If Redis is unavailable (e.g. in development or tests), all operations
are silently skipped — the application continues without caching.
"""

import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return the shared Redis client, or None if Redis is unavailable."""
    global _redis
    if _redis is None:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await client.ping()
            _redis = client
            logger.info("Redis connected at %s", settings.REDIS_URL)
        except Exception:
            logger.warning("Redis unavailable – caching disabled (%s)", settings.REDIS_URL)
            _redis = None
    return _redis


async def close_redis() -> None:
    """Close the Redis connection on application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")
