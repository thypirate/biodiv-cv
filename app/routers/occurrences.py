from __future__ import annotations

import asyncio
import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.links import page_links
from app.schemas import Occurrence, Page
from app.sources import gbif, inaturalist

router = APIRouter(prefix="/v1", tags=["occurrences"])


@router.get("/occurrences", response_model=Page[Occurrence], summary="Biodiversity records in Cape Verde")
async def occurrences(
    request: Request,
    taxon_key: int | None = Query(None, description="GBIF taxon key to filter by"),
    scientific_name: str | None = Query(None, description="Resolved to a GBIF taxon key"),
    q: str | None = Query(None, description="Full-text search across the record"),
    year: str | None = Query(None, description="Year or range, e.g. 2020 or 2010,2020"),
    has_coordinate: bool | None = Query(None),
    basis_of_record: str | None = Query(None, description="e.g. HUMAN_OBSERVATION, PRESERVED_SPECIMEN"),
    limit: int = Query(20, ge=1, le=300),
    offset: int = Query(0, ge=0),
) -> Page[Occurrence]:
    if scientific_name and taxon_key is None:
        match = await gbif.match_name(scientific_name)
        if not match:
            raise HTTPException(status_code=404, detail=f"No GBIF match for '{scientific_name}'")
        taxon_key = match["usageKey"]

    data = await gbif.search_occurrences(
        taxon_key=taxon_key,
        q=q,
        year=year,
        has_coordinate=has_coordinate,
        basis_of_record=basis_of_record.upper() if basis_of_record else None,
        limit=limit,
        offset=offset,
    )
    return Page[Occurrence](
        total=data.get("count"),
        limit=limit,
        offset=offset,
        end_of_records=bool(data.get("endOfRecords")),
        results=[gbif.to_occurrence(row) for row in data.get("results", [])],
        sources=["gbif"],
        links=page_links(request, limit=limit, offset=offset, total=data.get("count")),
        retrievedAt=str(datetime.datetime.now()),
    )


@router.get("/occurrences/stats", summary="National overview of recorded biodiversity")
async def stats() -> dict[str, Any]:
    facet_fields = ["kingdomKey", "basisOfRecord", "year", "datasetKey"]
    total, facets, inat_total = await asyncio.gather(
        gbif.occurrence_count(),
        gbif.facets(facet_fields, facet_limit=12),
        inaturalist.observation_count(),
    )

    kingdoms = [
        {"kingdom": gbif.KINGDOMS.get(int(row["key"]), row["key"]), "count": row["count"]}
        for row in facets.get("KINGDOM_KEY", [])
    ]
    years = sorted(
        ({"year": int(r["key"]), "count": r["count"]} for r in facets.get("YEAR", [])),
        key=lambda r: r["year"],
    )

    return {
        "country": "Cape Verde",
        "gbif_occurrences": total,
        "inaturalist_observations": inat_total,
        "unavailable_sources": [] if inat_total is not None else ["inaturalist"],
        "by_kingdom": kingdoms,
        "by_basis_of_record": [
            {"basis": r["key"], "count": r["count"]} for r in facets.get("BASIS_OF_RECORD", [])
        ],
        "top_years": years,
        "sources": ["gbif"] + (["inaturalist"] if inat_total is not None else []),
    }


@router.get("/observations", response_model=Page[Occurrence], summary="Community observations (iNaturalist)")
async def observations(
    request: Request,
    scientific_name: str | None = Query(None, description="iNaturalist taxon name"),
    quality_grade: str | None = Query(None, description="research | needs_id | casual"),
    year: int | None = Query(None, ge=1700, le=2100),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[Occurrence]:
    # iNaturalist paginates by page number; translate offset into a page.
    page_number = offset // limit + 1
    data = await inaturalist.observations(
        taxon_name=scientific_name,
        quality_grade=quality_grade,
        year=year,
        page=page_number,
        per_page=limit,
    )
    results = [inaturalist.to_occurrence(row) for row in data.get("results", [])]
    total = data.get("total_results")
    return Page[Occurrence](
        total=total,
        limit=limit,
        offset=offset,
        end_of_records=total is not None and offset + len(results) >= total,
        results=results,
        sources=["inaturalist"],
        links=page_links(request, limit=limit, offset=offset, total=total),
    )
