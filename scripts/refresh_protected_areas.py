#!/usr/bin/env python3
"""Regenerate app/data/protected_areas.json from the official INGT dataset.

Source: "Rede de Áreas Protegidas de Cabo Verde", published by the Instituto
Nacional de Gestão do Território (INGT), 2023-06-12.

  Metadata record:
    https://metadados-ingt.gov.cv/geonetwork/srv/api/records/09bc0aac-3569-4095-85fe-e2516c2e00a4
  Data (WFS):
    https://geoservicos-ingt.gov.cv/geoserver/areas_especiais/ows

The service publishes its geometry in a projected national grid despite
declaring EPSG:4826, so we ask GeoServer to reproject to EPSG:4326 explicitly —
without `srsName` you get metres, not degrees.

Polygon geometry is deliberately *not* bundled: the full MultiPolygons are
~900 KB, and a client that needs them should fetch them from INGT directly (the
WFS URL is advertised at /v1/sources). We keep the attributes, an area-weighted
centroid and a bounding box, which is what a list or a map pin needs.

Usage:  uv run scripts/refresh_protected_areas.py
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

WFS = (
    "https://geoservicos-ingt.gov.cv/geoserver/areas_especiais/ows"
    "?service=WFS&version=1.0.0&request=GetFeature"
    "&typeName=areas_especiais:area_protegida"
    "&outputFormat=application/json&srsName=EPSG:4326"
)
OUT = Path(__file__).resolve().parent.parent / "app" / "data" / "protected_areas.json"

# The WFS reports islands in upper case; map them to the spellings used by
# /v1/islands so the two endpoints can be joined.
ISLANDS = {
    "BOA VISTA": "Boa Vista",
    "BRAVA": "Brava",
    "FOGO": "Fogo",
    "MAIO": "Maio",
    "SAL": "Sal",
    "SANTA LUZIA": "Santa Luzia",
    "SANTIAGO": "Santiago",
    "SANTO ANTÃO": "Santo Antão",
    "SÃO NICOLAU": "São Nicolau",
    "SÃO VICENTE": "São Vicente",
}


def slugify(value: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "pa-" + re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_.lower())).strip("-")


def ring_area_and_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Signed area and centroid of a closed ring, via the shoelace formula."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2.0
    if area == 0:
        return 0.0, ring[0][0], ring[0][1]
    return area, cx / (6.0 * area), cy / (6.0 * area)


def centroid_and_bbox(geometry: dict) -> tuple[dict, list[float]]:
    """Area-weighted centroid over every outer ring, plus the bounding box."""
    total = wx = wy = 0.0
    west = south = float("inf")
    east = north = float("-inf")

    for polygon in geometry["coordinates"]:
        outer = polygon[0]
        area, cx, cy = ring_area_and_centroid(outer)
        weight = abs(area)
        total += weight
        wx += cx * weight
        wy += cy * weight
        for ring in polygon:
            for x, y in ring:
                west, east = min(west, x), max(east, x)
                south, north = min(south, y), max(north, y)

    if total == 0:  # degenerate; fall back to the bbox centre
        wx, wy, total = (west + east) / 2, (south + north) / 2, 1.0

    return (
        {"latitude": round(wy / total, 6), "longitude": round(wx / total, 6)},
        [round(west, 6), round(south, 6), round(east, 6), round(north, 6)],
    )


def main() -> None:
    print(f"fetching {WFS.split('?')[0]} …")
    with urllib.request.urlopen(WFS, timeout=120) as response:
        collection = json.load(response)

    features = collection["features"]
    print(f"  {len(features)} features")

    areas = []
    seen: set[str] = set()
    for feature in features:
        props = feature["properties"]
        name = " ".join(props["designacao"].split())  # upstream has stray double spaces
        island = props["ilha"]
        if island not in ISLANDS:
            raise SystemExit(f"unmapped island {island!r} — update ISLANDS")

        slug = slugify(name)
        if slug in seen:  # names are unique today; stay safe if that changes
            slug = f"{slug}-{len(seen)}"
        seen.add(slug)

        centroid, bbox = centroid_and_bbox(feature["geometry"])
        area_ha = props.get("area_ha")

        areas.append(
            {
                "id": slug,
                "name": name,
                # Category is taken verbatim from INGT, including the one record
                # whose name and category disagree — see README.
                "designation": props["categorias"],
                "island": ISLANDS[island],
                "area_ha": round(area_ha, 2) if area_ha else None,
                "reported_area_km2": round(area_ha / 100, 3) if area_ha else None,
                "coordinates": centroid,
                "bbox": bbox,
                "legal_instrument": props.get("bo") or None,
                "legal_instrument_url": props.get("link_bo") or None,
            }
        )

    areas.sort(key=lambda a: (a["island"], a["name"]))
    OUT.write_text(json.dumps(areas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    total_km2 = sum(a["reported_area_km2"] or 0 for a in areas)
    print(f"wrote {OUT.relative_to(OUT.parent.parent.parent)}")
    print(f"  {len(areas)} areas across {len({a['island'] for a in areas})} islands")
    print(f"  {total_km2:,.1f} km² total")


if __name__ == "__main__":
    main()
