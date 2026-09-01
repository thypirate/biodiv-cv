from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.data.reference import INGT_NOTE, INGT_SOURCE, protected_areas
from app.schemas import ProtectedArea
from app.sources import protectedplanet

router = APIRouter(prefix="/v1/protected-areas", tags=["protected areas"])


async def _load() -> tuple[list[ProtectedArea], bool]:
    """Official INGT data by default; WDPA instead when a token is configured."""
    live = await protectedplanet.list_areas(limit=100)
    if live:
        return live, True
    return list(protected_areas()), False


@router.get("", summary="Protected areas of Cape Verde")
async def list_areas(
    island: str | None = Query(None, description="Filter by island name"),
    designation: str | None = Query(
        None, description="Filter by legal category, e.g. 'Parque Natural'"
    ),
    marine: bool | None = Query(None, description="WDPA only; INGT does not classify these"),
) -> dict[str, Any]:
    areas, from_wdpa = await _load()

    if island:
        needle = island.casefold()
        areas = [a for a in areas if a.island and needle in a.island.casefold()]
    if designation:
        needle = designation.casefold()
        areas = [a for a in areas if a.designation and needle in a.designation.casefold()]
    if marine is not None:
        areas = [a for a in areas if a.marine is marine]

    return {
        "total": len(areas),
        "total_area_km2": round(sum(a.reported_area_km2 or 0 for a in areas), 1),
        "results": areas,
        "sources": ["protected-planet"] if from_wdpa else ["ingt"],
        "source": None if from_wdpa else INGT_SOURCE,
        "note": None if from_wdpa else INGT_NOTE,
    }


@router.get("/designations", summary="Legal categories, with counts")
async def designations() -> list[dict[str, Any]]:
    areas, _ = await _load()
    counts: dict[str, dict[str, Any]] = {}
    for area in areas:
        if not area.designation:
            continue
        row = counts.setdefault(
            area.designation, {"designation": area.designation, "count": 0, "area_km2": 0.0}
        )
        row["count"] += 1
        row["area_km2"] += area.reported_area_km2 or 0
    for row in counts.values():
        row["area_km2"] = round(row["area_km2"], 1)
    return sorted(counts.values(), key=lambda r: -r["count"])


@router.get("/{area_id}", response_model=ProtectedArea, summary="A single protected area")
async def get_area(area_id: str) -> ProtectedArea:
    areas, _ = await _load()
    for area in areas:
        if area.id == area_id:
            return area
    raise HTTPException(status_code=404, detail=f"Protected area '{area_id}' not found")
