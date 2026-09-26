# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                              # install deps (creates .venv)
uv run main.py                       # dev server with reload at http://127.0.0.1:8000
uv run pytest                        # run the whole suite
uv run pytest tests/test_routes.py   # one file
uv run pytest -k resolve             # tests matching an expression
uv run uvicorn app.main:app          # run without the reload wrapper
```

Interactive docs at `/docs`, OpenAPI at `/openapi.json`. Ruff is configured (line-length 110, py311) but not wired into CI; CI only runs `uv run pytest` (see `.github/workflows/deploy.yml`).

## Architecture

A **stateless** FastAPI service that aggregates public biodiversity data for Cape Verde. It owns no database — every response is either fetched live from an upstream API, served from a cache, or read from bundled seed data. This shapes everything below.

**Request flow:** `routers/` (HTTP shape, validation, filtering) → `sources/` (one module per upstream: gbif, inaturalist, wikipedia, protectedplanet) → `clients.get_json` (the single shared `httpx.AsyncClient`). Routers must not call `httpx` directly.

**Two independent cache layers** (`app/cache.py`), both keyed by a SHA1 of the function's args:
- `@cached(ttl=)` — in-process `TTLCache`, per-worker. Uses a per-key async lock to prevent stampedes (concurrent misses collapse into one upstream call).
- `@cached_redis(ttl=)` — used by the `sources/` functions. Calls the upstream first; on **any exception** it falls back to the last good Redis value if present (stale-if-error). Fresh results are written to Redis in a fire-and-forget background task. This means a flaky upstream degrades to stale data rather than a 500.

**Graceful degradation is the core design principle:**
- Redis is optional. `redis_db.py` never raises — an unreachable Redis is a degraded mode, not a boot failure. Tests/CI run with `CVBIO_REDIS_ENABLED=false` (set in `tests/conftest.py`).
- Upstream failures in `clients.get_json` surface as `HTTPException` 502/504 (never a bare 500), with bounded exponential-backoff retries on 429/5xx/timeouts.
- `clients.optional(awaitable)` swallows that `HTTPException` and returns `None`, so *enrichment* sources (Wikipedia summary, IUCN status, iNaturalist counts) can fail without taking down the whole response. Endpoints fan out to multiple sources with `asyncio.gather` and merge whatever came back — see `species._build_detail`.

**Reference vs. live data:** Islands are hardcoded in `app/data/reference.py`. Protected areas and beaches are bundled JSON (`app/data/*.json`, loaded via `lru_cache`). Protected areas have a live/seed switch: if `CVBIO_PROTECTED_PLANET_TOKEN` is set, `protected_areas` endpoints serve live WDPA data; otherwise they serve the bundled INGT seed list and say so in the payload (`sources`, `source`, `note` fields). Regenerate the seed with `uv run scripts/refresh_protected_areas.py`.

**HATEOAS:** Species and occurrence responses carry a HAL-style `_links` object built in `app/links.py`. Reference collections (islands, sources, beaches) are leaves and stay plain. When adding fields to `Species`/`Occurrence`, keep the link builders in sync.

**Rate limiting** (`app/rate_limiter.py`): slowapi with a global default (`120/minute`) plus tighter per-route limits (`20/minute` on the expensive species/occurrence routes). Storage is Redis when enabled, in-memory fallback otherwise. Routes needing a limit take a `request: Request` param; `/health` and `/` are `@limiter.exempt`. `limiter.reset()` is called between tests.

**Config** (`app/config.py`): pydantic-settings, env prefix `CVBIO_`, reads `.env`. A single `settings` singleton is imported everywhere. `cors_origins` accepts either a JSON list or a plain comma-separated string.

## Project Boundaries

### In scope

- **Aggregating and attributing upstream data** for Cape Verde — GBIF/iNaturalist/Wikipedia/WDPA are merged and served with provenance intact. Keep `/v1/sources` and per-payload `source`/`license` fields accurate when adding a source; never claim or relicense.
- **Read-only `GET` endpoints** over that data (CORS `allow_methods=["GET"]`).
- **Best-effort enrichment.** A failing Wikipedia/IUCN/iNaturalist call must degrade to a partial response (via `clients.optional`), never a hard failure. Only the primary GBIF lookup for a route is allowed to 404/502.
- **Bundled seed data as a fallback** so protected-areas/beaches work without live tokens (`app/data/*.json`). Prefer live sources where one exists; regenerate seeds with the scripts rather than hand-editing.

### Out of scope

- **Persistence or user state.** The service is stateless by design — Redis and the in-process `TTLCache` are caches only, never a source of truth. No database, sessions, auth, or writes; if a cache is cold or absent, every endpoint must still work by fetching live or reading bundled seed data.
- **Mutating endpoints.** No `POST`/`PUT`/`DELETE`.
- **Anything beyond Cape Verde.** Scope is fixed to `country_code="CV"` / the iNaturalist place id in `config.py`. It is not a general-purpose biodiversity API.
- **Background work.** No workers, schedulers, or cross-request shared mutable state beyond the caches. Single process per replica; scale horizontally by replica.

## Conventions

- All source/client code is `async`; use `await clients.get_json(...)`, not `httpx` directly.
- New upstream integration = a new module in `app/sources/` whose fetch functions are wrapped in `@cached_redis` and pass a `source=` label to `get_json` (used in error messages).
- Response shapes are pydantic models in `app/schemas.py`; `Page[T]` is the generic paginated envelope.
- Deployment is Docker (`Dockerfile`) on Railway (`railway.toml`), one process per replica. The in-process cache is per-replica, so scaling out means each replica warms its own cache — scale with replicas, not workers.
