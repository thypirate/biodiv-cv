from __future__ import annotations

import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

log = logging.getLogger(__name__)

redis: Redis | None = None


async def init_redis() -> None:
    """Connect at app startup. Never raises: an unreachable Redis is a
    degraded mode, not a boot failure."""
    global redis

    if not settings.redis_enabled:
        log.info("Redis disabled")
        redis = None
        return

    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        username=settings.redis_username,
        password=settings.redis_pwd,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    try:
        await client.ping()
    except (RedisError, OSError) as exc:
        log.warning(
            "Redis unavailable at %s:%s (%s);",
            settings.redis_host, settings.redis_port, exc,
        )
        await _quietly_close(client)
        redis = None
        return

    redis = client
    log.info("Redis connected at %s:%s db=%s",
             settings.redis_host, settings.redis_port, settings.redis_db)


async def close_redis() -> None:
    """Close the connection pool at app shutdown."""
    global redis
    if redis is not None:
        await _quietly_close(redis)
        redis = None


async def _quietly_close(client: Redis) -> None:
    try:
        await client.aclose()
    except (RedisError, OSError) as exc:
        log.warning("Error closing Redis: %s", exc)


def is_available() -> bool:
    return redis is not None


async def get_cache(key: str) -> str | None:
    if redis is None:
        return None
    try:
        return await redis.get(key)
    except RedisError as exc:
        log.warning("Redis GET %s failed: %s", key, exc)
        return None


async def set_cache(key: str, value: str, ttl: int | None = 300) -> bool:
    if redis is None:
        return False
    try:
        await redis.set(key, value, ex=ttl)   # ex=None => no expiry
        return True
    except RedisError as exc:
        log.warning("Redis SET %s failed: %s", key, exc)
        return False


async def expire_cache(key: str, ttl: int) -> bool:
    if redis is None:
        return False
    try:
        await redis.expire(key, ttl)
        return True
    except RedisError as exc:
        log.warning("Redis EXPIRE %s failed: %s", key, exc)
        return False


async def delete_cache(key: str) -> bool:
    if redis is None:
        return False
    try:
        await redis.delete(key)
        return True
    except RedisError as exc:
        log.warning("Redis DEL %s failed: %s", key, exc)
        return False
