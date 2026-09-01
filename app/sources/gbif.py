"""GBIF — the backbone of this API. No API key required."""

from __future__ import annotations

from typing import Any

from app.cache import cached
from app.clients import get_json, get_json_optional
from app.config import settings
from app.links import occurrence_links, species_links
from app.schemas import (
    ConservationStatus,
    Coordinates,
    Occurrence,
    Species,
    Taxonomy,
)

BASE = settings.gbif_base
CV = settings.country_code

# GBIF kingdom keys are stable and used to label facet output.
KINGDOMS = {
    1: "Animalia",
    2: "Archaea",
    3: "Fungi",
    4: "Plantae",
    5: "Protozoa",
    6: "Bacteria",
    7: "Chromista",
    8: "Viruses",
    0: "incertae sedis",
}


def _taxonomy(raw: dict[str, Any]) -> Taxonomy:
    return Taxonomy(
        kingdom=raw.get("kingdom"),
        phylum=raw.get("phylum"),
        **{"class": raw.get("class")},
        order=raw.get("order"),
        family=raw.get("family"),
        genus=raw.get("genus"),
    )


# Preferred languages for common names, best first. Cape Verde's working
# languages are Portuguese and Kriolu; English and Spanish are useful fallbacks.
_LANGS = ("por", "eng", "spa", None)


def _pick_vernacular(rows: list[dict[str, Any]]) -> list[str]:
    ranked: list[tuple[int, str]] = []
    for row in rows:
        name = row.get("vernacularName")
        if not name:
            continue
        lang = row.get("language")
        if lang not in _LANGS:
            continue
        ranked.append((_LANGS.index(lang), name))
    ranked.sort(key=lambda pair: pair[0])
    return list(dict.fromkeys(name for _, name in ranked))


def to_species(raw: dict[str, Any]) -> Species:
    vernacular = _pick_vernacular(raw.get("vernacularNames") or [])
    if raw.get("vernacularName"):
        vernacular.insert(0, raw["vernacularName"])
    key = raw.get("nubKey") or raw.get("key")
    return Species(
        gbif_key=key,
        scientific_name=raw.get("scientificName") or raw.get("canonicalName") or "unknown",
        canonical_name=raw.get("canonicalName"),
        authorship=(raw.get("authorship") or None),
        rank=raw.get("rank"),
        taxonomic_status=raw.get("taxonomicStatus"),
        synonym=bool(raw.get("synonym")),
        vernacular_names=list(dict.fromkeys(vernacular))[:8],
        taxonomy=_taxonomy(raw),
        links=species_links(key, raw.get("canonicalName")),
    )


def _media(raw: dict[str, Any]) -> list[str]:
    urls = [m.get("identifier") for m in raw.get("media") or [] if m.get("identifier")]
    if urls:
        return urls[:5]
    ext = (raw.get("extensions") or {}).get("http://rs.gbif.org/terms/1.0/Multimedia") or []
    return [
        m.get("http://purl.org/dc/terms/identifier")
        for m in ext
        if m.get("http://purl.org/dc/terms/identifier")
    ][:5]


def to_occurrence(raw: dict[str, Any]) -> Occurrence:
    lat, lon = raw.get("decimalLatitude"), raw.get("decimalLongitude")
    coords = (
        Coordinates(
            latitude=lat,
            longitude=lon,
            uncertainty_m=raw.get("coordinateUncertaintyInMeters"),
        )
        if lat is not None and lon is not None
        else None
    )
    key = raw.get("key")
    occurrence = Occurrence(
        id=str(key),
        source="gbif",
        scientific_name=raw.get("scientificName") or raw.get("species"),
        gbif_species_key=raw.get("speciesKey") or raw.get("acceptedTaxonKey") or raw.get("taxonKey"),
        event_date=raw.get("eventDate"),
        year=raw.get("year"),
        coordinates=coords,
        locality=raw.get("locality") or raw.get("verbatimLocality") or raw.get("waterBody"),
        basis_of_record=raw.get("basisOfRecord"),
        dataset=raw.get("datasetName"),
        dataset_key=raw.get("datasetKey"),
        recorded_by=raw.get("recordedBy"),
        license=raw.get("license"),
        media=_media(raw),
        url=f"https://www.gbif.org/occurrence/{key}" if key else None,
        taxonomy=_taxonomy(raw),
    )
    occurrence.links = occurrence_links(occurrence)
    return occurrence


@cached()
async def search_species(q: str, *, rank: str | None, limit: int, offset: int) -> dict[str, Any]:
    return await get_json(
        f"{BASE}/species/search",
        params={
            "q": q,
            "rank": rank,
            "limit": limit,
            "offset": offset,
            "status": "ACCEPTED",
            "datasetKey": "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c",  # GBIF Backbone Taxonomy
        },
        source="GBIF",
    )


@cached(ttl=settings.cache_ttl_long)
async def species_detail(key: int) -> dict[str, Any] | None:
    return await get_json(f"{BASE}/species/{key}", source="GBIF")


@cached(ttl=settings.cache_ttl_long)
async def vernacular_names(key: int) -> list[str]:
    data = await get_json_optional(f"{BASE}/species/{key}/vernacularNames", params={"limit": 100})
    return _pick_vernacular((data or {}).get("results", []))[:8]


@cached(ttl=settings.cache_ttl_long)
async def match_name(name: str) -> dict[str, Any] | None:
    """Fuzzy-match a scientific name to a GBIF backbone key."""
    data = await get_json_optional(f"{BASE}/species/match", params={"name": name, "strict": False})
    if not data or not data.get("usageKey"):
        return None
    return data


@cached(ttl=settings.cache_ttl_long)
async def iucn_category(key: int) -> ConservationStatus | None:
    data = await get_json_optional(f"{BASE}/species/{key}/iucnRedListCategory")
    if not data or not data.get("category"):
        return None
    return ConservationStatus(
        category=data.get("category"),
        code=data.get("code"),
        iucn_taxon_id=str(data["iucnTaxonID"]) if data.get("iucnTaxonID") else None,
    )


@cached()
async def search_occurrences(
    *,
    taxon_key: int | None = None,
    q: str | None = None,
    year: str | None = None,
    has_coordinate: bool | None = None,
    basis_of_record: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    return await get_json(
        f"{BASE}/occurrence/search",
        params={
            "country": CV,
            "taxonKey": taxon_key,
            "q": q,
            "year": year,
            "hasCoordinate": has_coordinate,
            "basisOfRecord": basis_of_record,
            "limit": limit,
            "offset": offset,
        },
        source="GBIF",
    )


@cached()
async def occurrence_count(taxon_key: int | None = None) -> int:
    data = await get_json(
        f"{BASE}/occurrence/search",
        params={"country": CV, "taxonKey": taxon_key, "limit": 0},
        source="GBIF",
    )
    return int(data.get("count", 0))


@cached()
async def facets(fields: list[str], *, facet_limit: int = 12) -> dict[str, list[dict[str, Any]]]:
    data = await get_json(
        f"{BASE}/occurrence/search",
        params={"country": CV, "limit": 0, "facetLimit": facet_limit, "facet": list(fields)},
        source="GBIF",
    )
    out: dict[str, list[dict[str, Any]]] = {}
    for facet in data.get("facets", []):
        out[facet["field"]] = [
            {"key": c["name"], "count": c["count"]} for c in facet.get("counts", [])
        ]
    return out


@cached()
async def top_species(limit: int = 20) -> list[dict[str, Any]]:
    """Most-recorded species in Cape Verde, from the speciesKey facet."""
    data = await get_json(
        f"{BASE}/occurrence/search",
        params={"country": CV, "limit": 0, "facetLimit": limit, "facet": "speciesKey"},
        source="GBIF",
    )
    for facet in data.get("facets", []):
        if facet["field"] == "SPECIES_KEY":
            return [{"key": int(c["name"]), "count": c["count"]} for c in facet.get("counts", [])]
    return []
