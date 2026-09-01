from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CVBIO_", extra="ignore")

    app_name: str = "Cape Verde Biodiversity Open Data API"
    version: str = "0.1.0"
    country_code: str = "CV"

    # Upstream base URLs
    gbif_base: str = "https://api.gbif.org/v1"
    inat_base: str = "https://api.inaturalist.org/v1"
    wikipedia_base: str = "https://en.wikipedia.org/api/rest_v1"
    protected_planet_base: str = "https://api.protectedplanet.net/v3"

    # iNaturalist place id for Cape Verde (admin_level 0). Override if it ever changes.
    inat_place_id: int = 9445

    # Optional: unlocks live WDPA protected-area data. Without it the API serves
    # the bundled seed list and says so in the payload.
    protected_planet_token: str | None = None

    # HTTP behaviour
    http_timeout: float = 20.0
    http_retries: int = 2
    user_agent: str = "cv-biodiv-open-data-api/0.1 (+https://github.com/)"

    # In-process cache
    cache_ttl: int = 900          # 15 min for normal lookups
    cache_ttl_long: int = 86400   # 24 h for near-static reference data
    cache_maxsize: int = 4096

    # NoDecode so we can accept a plain comma-separated string as well as JSON.
    # Typing `https://a.example,https://b.example` into a hosting dashboard is
    # the obvious thing to do, and it should not crash-loop the container.
    cors_origins: Annotated[list[str], NoDecode] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if text.startswith("["):  # JSON list
            import json

            return json.loads(text)
        return [item.strip() for item in text.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
