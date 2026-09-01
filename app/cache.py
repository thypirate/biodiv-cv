"""Tiny async TTL cache.

The whole point of this project's v1 is "no infrastructure": no Postgres, no
Redis. Upstream responses are held in a bounded in-process TTL cache, which is
enough to keep us inside upstream rate limits and to make repeat requests fast.
State is per-process and disposable — restart the app and it simply refills.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

from cachetools import TTLCache

from app.config import settings

P = ParamSpec("P")
T = TypeVar("T")

_stats = {"hits": 0, "misses": 0}
_caches: list[TTLCache] = []


def _key(prefix: str, args: tuple, kwargs: dict) -> str:
    blob = json.dumps([args, sorted(kwargs.items())], default=str, sort_keys=True)
    return f"{prefix}:{hashlib.sha1(blob.encode()).hexdigest()}"


def cached(ttl: int | None = None) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Cache an async function's result for `ttl` seconds.

    Concurrent callers that miss on the same key wait on a shared lock so we
    only ever have one in-flight request upstream per key.
    """

    def decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        store: TTLCache = TTLCache(maxsize=settings.cache_maxsize, ttl=ttl or settings.cache_ttl)
        _caches.append(store)
        locks: dict[str, asyncio.Lock] = {}
        guard = asyncio.Lock()
        prefix = f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = _key(prefix, args, kwargs)
            try:
                value = store[key]
                _stats["hits"] += 1
                return value
            except KeyError:
                pass

            async with guard:
                lock = locks.setdefault(key, asyncio.Lock())

            async with lock:
                # Another coroutine may have filled it while we waited.
                try:
                    value = store[key]
                    _stats["hits"] += 1
                    return value
                except KeyError:
                    pass
                _stats["misses"] += 1
                value = await fn(*args, **kwargs)
                store[key] = value
                return value

        return wrapper

    return decorator


def cache_stats() -> dict[str, Any]:
    total = _stats["hits"] + _stats["misses"]
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": round(_stats["hits"] / total, 3) if total else None,
        "entries": sum(len(c) for c in _caches),
        "namespaces": len(_caches),
    }


def cache_clear() -> None:
    for c in _caches:
        c.clear()
