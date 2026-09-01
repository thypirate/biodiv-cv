from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.cache import cache_stats
from app.config import settings
from app.data.reference import ISLANDS
from app.schemas import Island, SourceInfo
from app.sources import protectedplanet

router = APIRouter(tags=["meta"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, Any]:
    return {"status": "ok", "version": settings.version, "cache": cache_stats()}


@router.get("/v1/islands", response_model=list[Island], summary="The islands of Cape Verde")
async def islands() -> list[Island]:
    return ISLANDS


@router.get("/v1/sources", response_model=list[SourceInfo], summary="Upstream data sources and licences")
async def sources() -> list[SourceInfo]:
    return [
        SourceInfo(
            key="gbif",
            name="Global Biodiversity Information Facility",
            url="https://www.gbif.org",
            license="Per-dataset (CC0 / CC BY / CC BY-NC)",
            used_for=["occurrences", "species", "taxonomy", "conservation status"],
        ),
        SourceInfo(
            key="inaturalist",
            name="iNaturalist",
            url="https://www.inaturalist.org",
            license="Per-observation (CC0 / CC BY / CC BY-NC)",
            used_for=["community observations", "common names", "photos"],
        ),
        SourceInfo(
            key="wikipedia",
            name="Wikipedia REST API",
            url="https://en.wikipedia.org",
            license="CC BY-SA 4.0",
            used_for=["species descriptions"],
        ),
        SourceInfo(
            key="ingt",
            name="Instituto Nacional de Gestão do Território — Rede de Áreas Protegidas de Cabo Verde",
            url="https://metadados-ingt.gov.cv/geonetwork/srv/api/records/09bc0aac-3569-4095-85fe-e2516c2e00a4",
            license="Cape Verde national spatial data infrastructure (INGT)",
            used_for=["protected areas"],
        ),
        SourceInfo(
            key="protected-planet",
            name="Protected Planet (WDPA)",
            url="https://www.protectedplanet.net",
            license="WDPA Terms of Use (non-commercial)",
            requires_token=True,
            enabled=protectedplanet.enabled(),
            used_for=["protected areas (overrides INGT when enabled)"],
        ),
    ]
