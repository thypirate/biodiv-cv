from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.data.reference import BEACH_SOURCES
from app.schemas import Beach
from app.rate_limiter import limiter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

router = APIRouter(prefix="/v1/beaches", tags=["beaches"])


@lru_cache
def _load_beaches() -> tuple[Beach, ...]:
    raw = json.loads((DATA_DIR / "beaches.json").read_text(encoding="utf-8"))
    return tuple(Beach(**row) for row in raw)

@router.get("", summary="Beaches of Cape Verde")
@limiter.limit("120/minute")
async def list_beaches(request: Request) -> dict[str, Any]:
    beaches = _load_beaches()
    return {
        "total": len(beaches),
        "results": beaches,
        "sources": BEACH_SOURCES,
    }

@router.get("/{beach_id}", response_model=Beach, summary="A single beach")
@limiter.limit("120/minute")
async def get_beach(request: Request, beach_id: str) -> Beach:
    beaches = _load_beaches()
    for beach in beaches:
        if beach.id == beach_id:
            return beach
    raise HTTPException(status_code=404, detail=f"Beach '{beach_id}' not found")
