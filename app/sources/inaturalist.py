"""iNaturalist — the community-observation layer. No API key required."""

from __future__ import annotations

from typing import Any

from app.cache import cached
from app.clients import get_json, get_json_optional
from app.config import settings
from app.links import occurrence_links
from app.schemas import Coordinates, Occurrence

BASE = settings.inat_base
PLACE_ID = settings.inat_place_id


def _photos(raw: dict[str, Any]) -> list[str]:
    urls = []
    for photo in raw.get("photos") or []:
        url = photo.get("url")
        if url:
            # iNat returns the square thumbnail; ask for something usable.
            urls.append(url.replace("/square.", "/medium."))
    return urls[:5]


def to_occurrence(raw: dict[str, Any]) -> Occurrence:
    taxon = raw.get("taxon") or {}
    geo = raw.get("geojson") or {}
    coords = None
    if geo.get("type") == "Point" and len(geo.get("coordinates") or []) == 2:
        lon, lat = geo["coordinates"]
        coords = Coordinates(
            latitude=lat, longitude=lon, uncertainty_m=raw.get("positional_accuracy")
        )
    observed_on = raw.get("observed_on")
    occurrence = Occurrence(
        id=str(raw.get("id")),
        source="inaturalist",
        scientific_name=taxon.get("name"),
        vernacular_name=taxon.get("preferred_common_name"),
        event_date=raw.get("time_observed_at") or observed_on,
        year=int(observed_on[:4]) if observed_on else None,
        coordinates=coords,
        locality=raw.get("place_guess"),
        basis_of_record="HUMAN_OBSERVATION",
        dataset=f"iNaturalist ({raw.get('quality_grade')})",
        dataset_key="inaturalist",
        iconic_taxon=taxon.get("iconic_taxon_name"),
        recorded_by=(raw.get("user") or {}).get("login"),
        license=raw.get("license_code"),
        media=_photos(raw),
        url=raw.get("uri"),
    )
    occurrence.links = occurrence_links(occurrence)
    return occurrence


@cached()
async def observations(
    *,
    taxon_name: str | None = None,
    taxon_id: int | None = None,
    quality_grade: str | None = None,
    year: int | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    return await get_json(
        f"{BASE}/observations",
        params={
            "place_id": PLACE_ID,
            "taxon_name": taxon_name,
            "taxon_id": taxon_id,
            "quality_grade": quality_grade,
            "year": year,
            "page": page,
            "per_page": per_page,
            "order_by": "observed_on",
            "order": "desc",
        },
        source="iNaturalist",
    )


@cached(ttl=settings.cache_ttl_long)
async def species_counts(limit: int = 20) -> dict[str, Any]:
    return await get_json(
        f"{BASE}/observations/species_counts",
        params={"place_id": PLACE_ID, "per_page": limit},
        source="iNaturalist",
    )


@cached(ttl=settings.cache_ttl_long)
async def observation_count() -> int | None:
    """Total observations, or None if iNaturalist is unreachable.

    Used only for the national overview, where it is one figure among many —
    losing it should not take the whole endpoint down with it.
    """
    data = await get_json_optional(
        f"{BASE}/observations",
        params={"place_id": PLACE_ID, "per_page": 0},
        source="iNaturalist",
    )
    if not data:
        return None
    return int(data.get("total_results", 0))
