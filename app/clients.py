from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import HTTPException

from datetime import datetime, timezone

from collections.abc import Awaitable

from typing import TypeVar

from app.config import settings

log = logging.getLogger("cvbio.http")

T = TypeVar("T")

_client: httpx.AsyncClient | None = None

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

async def startup() -> None:
    global _client
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout),
        headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
        follow_redirects=True,
    )


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialised; use the app lifespan")
    return _client


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _clean(params: dict[str, Any] | None) -> list[tuple[str, str]]:

    if not params:
        return []
    out: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            out.extend((key, _encode(item)) for item in value if item is not None)
        else:
            out.append((key, _encode(value)))
    return out


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    source: str = "upstream",
) -> Any:
    """GET JSON with bounded retries on transient failures.

    Raises HTTPException(502/504) so a failing upstream surfaces as a clear
    gateway error rather than a 500.
    """
    attempts = settings.http_retries + 1
    last_exc: Exception | None = None

    for attempt in range(attempts):
        try:
            response = await client().get(url, params=_clean(params), headers=headers)
        except httpx.TimeoutException as exc:
            last_exc = exc
        except httpx.HTTPError as exc:
            last_exc = exc
        else:
            if response.status_code == 404:
                return None
            if response.status_code < 400:
                data = response.json()
                if isinstance(data, dict):
                    data["_retrieved_at"] = utc_now()
                return data
            if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                last_exc = httpx.HTTPStatusError(
                    f"{source} returned {response.status_code}", request=response.request, response=response
                )
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"{source} returned HTTP {response.status_code}",
                )

        if attempt < attempts - 1:
            await asyncio.sleep(0.4 * (2**attempt))

    log.warning("%s unreachable: %s", source, last_exc)
    raise HTTPException(status_code=504, detail=f"{source} did not respond in time")


async def optional(awaitable: Awaitable[T]) -> T | None:
    try:
        return await awaitable
    except HTTPException as exc:
        log.warning("optional source unavailable: %s", exc.detail)
        return None
