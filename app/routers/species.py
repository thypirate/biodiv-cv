from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from app.links import page_links
from app.schemas import ConservationStatus, Page, Species, SpeciesDetail
from app.sources import gbif, wikipedia

router = APIRouter(prefix="/v1/species", tags=["species"])


@router.get("/search", response_model=Page[Species], summary="Search species by name")
async def search(
    request: Request,
    q: str = Query(..., min_length=2, description="Scientific or common name fragment"),
    rank: str | None = Query(None, description="GBIF rank filter, e.g. SPECIES, GENUS, FAMILY"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page[Species]:
    data = await gbif.search_species(q, rank=rank.upper() if rank else None, limit=limit, offset=offset)
    return Page[Species](
        total=data.get("count"),
        limit=limit,
        offset=offset,
        end_of_records=bool(data.get("endOfRecords")),
        results=[gbif.to_species(row) for row in data.get("results", [])],
        sources=["gbif"],
        links=page_links(request, limit=limit, offset=offset, total=data.get("count")),
        retrievedAt=str(datetime.datetime.now()),

    )


@router.get("/top", response_model=list[SpeciesDetail], summary="Most-recorded species in Cape Verde")
async def top(limit: int = Query(10, ge=1, le=50)) -> list[SpeciesDetail]:
    counts = await gbif.top_species(limit)
    details = await asyncio.gather(
        *(_build_detail(row["key"], with_summary=False) for row in counts),
        return_exceptions=True,
    )
    out: list[SpeciesDetail] = []
    for row, detail in zip(counts, details):
        if isinstance(detail, SpeciesDetail):
            detail.occurrence_count_cv = row["count"]
            out.append(detail)
    return out


@router.get("/resolve", response_model=SpeciesDetail, summary="Resolve a scientific name to a species")
async def resolve(name: str = Query(..., min_length=3)) -> SpeciesDetail:
    match = await gbif.match_name(name)
    if not match:
        raise HTTPException(status_code=404, detail=f"No GBIF backbone match for '{name}'")
    return await _build_detail(match["usageKey"])


@router.get("/{key}", response_model=SpeciesDetail, summary="Species profile")
async def detail(key: int) -> SpeciesDetail:
    return await _build_detail(key)


@router.get("/{key}/conservation", response_model=ConservationStatus, summary="IUCN Red List status")
async def conservation(key: int) -> ConservationStatus:
    status = await gbif.iucn_category(key)
    if status is None:
        raise HTTPException(status_code=404, detail="No IUCN Red List assessment linked to this taxon")
    return status


async def _build_detail(key: int, *, with_summary: bool = True) -> SpeciesDetail:
    """Fan out to every enrichment source at once, then merge."""
    raw = await gbif.species_detail(key)
    if not raw:
        raise HTTPException(status_code=404, detail=f"GBIF species {key} not found")

    base = gbif.to_species(raw)
    lookup_name = base.canonical_name or base.scientific_name

    names, status, count, summary = await asyncio.gather(
        gbif.vernacular_names(key),
        gbif.iucn_category(key),
        gbif.occurrence_count(key),
        wikipedia.summary(lookup_name) if with_summary else _none(),
    )

    return SpeciesDetail(
        **base.model_dump(by_alias=True, exclude={"vernacular_names"}),
        vernacular_names=names or base.vernacular_names,
        conservation=status,
        summary=summary,
        occurrence_count_cv=count,
        gbif_url=f"https://www.gbif.org/species/{key}",
    )


async def _none() -> None:
    return None
