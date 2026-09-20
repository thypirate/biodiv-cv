from __future__ import annotations

from app.cache import cached, cached_redis
from app.clients import get_json
from app.config import settings
from app.schemas import SpeciesSummary

BASE = settings.wikipedia_base


@cached_redis(ttl=settings.cache_ttl_long)
async def summary(title: str) -> SpeciesSummary | None:
    slug = title.strip().replace(" ", "_")
    data = await get_json(f"{BASE}/page/summary/{slug}", source="Wikipedia")
    if not data or data.get("type") == "disambiguation" or not data.get("extract"):
        return None
    return SpeciesSummary(
        title=data.get("title"),
        description=data.get("description"),
        extract=data.get("extract"),
        url=((data.get("content_urls") or {}).get("desktop") or {}).get("page"),
        thumbnail=(data.get("thumbnail") or {}).get("source"),
    )
