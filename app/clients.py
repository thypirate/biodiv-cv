from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings

log = logging.getLogger("cvbio.http")

_client: httpx.AsyncClient | None = None


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
    if _client is None:  # pragma: no cover - only outside the app lifespan
        raise RuntimeError("HTTP client not initialised; use the app lifespan")
    return _client


def _encode(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _clean(params: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Drop None values and expand lists into repeated query params.

    Returned as a list of pairs because several upstreams (GBIF facets in
    particular) rely on the same key appearing more than once.
    """
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
                return response.json()
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


async def get_json_optional(url: str, **kwargs: Any) -> Any:
    """Like get_json but returns None instead of raising.

    Used for enrichment calls where a missing side-source should degrade the
    response, not fail it.
    """
    try:
        return await get_json(url, **kwargs)
    except HTTPException:
        return None
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("optional fetch failed for %s: %s", url, exc)
        return None
