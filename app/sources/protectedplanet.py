"""Protected Planet (WDPA) — optional, token-gated.

Without a token the API falls back to the bundled seed list and labels the
payload accordingly, so v1 still runs with zero configuration.
"""

from __future__ import annotations

from typing import Any

from app.cache import cached
from app.clients import get_json_optional
from app.config import settings
from app.schemas import Coordinates, ProtectedArea

BASE = settings.protected_planet_base


def enabled() -> bool:
    return bool(settings.protected_planet_token)


def _to_area(raw: dict[str, Any]) -> ProtectedArea:
    designations = raw.get("designation") or {}
    iucn = raw.get("iucn_category") or {}
    lat, lon = raw.get("latitude"), raw.get("longitude")
    locations = raw.get("locations") or []
    wdpa_id = raw.get("wdpa_id")
    return ProtectedArea(
        id=str(wdpa_id or raw.get("id")),
        name=raw.get("name") or raw.get("original_name") or "unnamed",
        designation=designations.get("name") if isinstance(designations, dict) else None,
        island=(locations[0].get("sub_location", {}) or {}).get("name") if locations else None,
        iucn_category=iucn.get("name") if isinstance(iucn, dict) else None,
        marine=raw.get("marine"),
        reported_area_km2=raw.get("reported_area"),
        wdpa_id=wdpa_id,
        coordinates=Coordinates(latitude=lat, longitude=lon) if lat and lon else None,
        url=raw.get("links", {}).get("protected_planet") if isinstance(raw.get("links"), dict) else None,
        data_quality="wdpa",
    )


@cached(ttl=settings.cache_ttl_long)
async def list_areas(limit: int = 50, page: int = 1) -> list[ProtectedArea] | None:
    if not enabled():
        return None
    data = await get_json_optional(
        f"{BASE}/protected_areas",
        params={
            "token": settings.protected_planet_token,
            "country": "CPV",  # ISO-3 for Cape Verde
            "per_page": limit,
            "page": page,
        },
        source="Protected Planet",
    )
    if not data or "protected_areas" not in data:
        return None
    return [_to_area(row) for row in data["protected_areas"]]
