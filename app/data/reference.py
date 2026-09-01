from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas import Island, ProtectedArea

DATA_DIR = Path(__file__).resolve().parent

ISLANDS: list[Island] = [
    Island(name="Santo Antão", group="Barlavento", area_km2=779.0, highest_point_m=1979, inhabited=True),
    Island(name="São Vicente", group="Barlavento", area_km2=227.0, highest_point_m=725, inhabited=True),
    Island(name="Santa Luzia", group="Barlavento", area_km2=35.0, highest_point_m=395, inhabited=False),
    Island(name="São Nicolau", group="Barlavento", area_km2=343.0, highest_point_m=1304, inhabited=True),
    Island(name="Sal", group="Barlavento", area_km2=216.0, highest_point_m=406, inhabited=True),
    Island(name="Boa Vista", group="Barlavento", area_km2=620.0, highest_point_m=387, inhabited=True),
    Island(name="Maio", group="Sotavento", area_km2=269.0, highest_point_m=436, inhabited=True),
    Island(name="Santiago", group="Sotavento", area_km2=991.0, highest_point_m=1394, inhabited=True),
    Island(name="Fogo", group="Sotavento", area_km2=476.0, highest_point_m=2829, inhabited=True),
    Island(name="Brava", group="Sotavento", area_km2=64.0, highest_point_m=976, inhabited=True),
]


@lru_cache
def protected_areas() -> tuple[ProtectedArea, ...]:
    """Cape Verde's 47 protected areas, from the official INGT dataset.

    Regenerate with `uv run scripts/refresh_protected_areas.py`.
    """
    raw = json.loads((DATA_DIR / "protected_areas.json").read_text(encoding="utf-8"))
    return tuple(ProtectedArea(**row, data_quality="ingt") for row in raw)


INGT_SOURCE = {
    "name": "Rede de Áreas Protegidas de Cabo Verde",
    "publisher": "Instituto Nacional de Gestão do Território (INGT)",
    "published": "2023-06-12",
    "metadata": (
        "https://metadados-ingt.gov.cv/geonetwork/srv/api/records/"
        "09bc0aac-3569-4095-85fe-e2516c2e00a4"
    ),
    "geometry": (
        "https://geoservicos-ingt.gov.cv/geoserver/areas_especiais/ows"
        "?service=WFS&version=1.0.0&request=GetFeature"
        "&typeName=areas_especiais:area_protegida"
        "&outputFormat=application/json&srsName=EPSG:4326"
    ),
}

INGT_NOTE = (
    "Official INGT dataset: all 47 protected areas, with legal category, area "
    "and establishing decree. Attributes are served verbatim. Polygon geometry "
    "is not bundled — fetch it from the WFS URL in `source.geometry`."
)
