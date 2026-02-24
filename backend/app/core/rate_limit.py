"""Shared rate limiter instance.

Uses Redis-backed storage when Redis is available so rate-limit counters
survive process restarts and work across multiple instances.
Falls back to in-memory storage (development / test environments).
"""

import logging

import redis as sync_redis
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _create_limiter() -> Limiter:
    from app.config import settings

    try:
        client = sync_redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        client.ping()
        client.close()
        logger.info("Rate limiter: Redis storage (%s)", settings.REDIS_URL)
        return Limiter(
            key_func=get_remote_address,
            default_limits=["100/minute"],
            storage_uri=settings.REDIS_URL,
        )
    except Exception:
        logger.warning("Rate limiter: Redis unavailable, using in-memory storage")
        return Limiter(key_func=get_remote_address, default_limits=["100/minute"])


limiter = _create_limiter()
