from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from pathlib import Path

from app import clients
from app.config import settings
from app.routers import beaches, meta, occurrences, protected_areas, species

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

DESCRIPTION = """
Open, stateless API aggregating biodiversity data for **Cape Verde** 🇨🇻.

This service stores nothing. Every request is answered by fanning out to public
upstream APIs (GBIF, iNaturalist, Wikipedia, optionally Protected Planet),
normalising the responses and caching them in memory for a short while. There is
no database, no queue and no background worker — one process is the whole system.

Data belongs to the upstream providers; see `/v1/sources` for licences and
please cite them in anything you build.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await clients.startup()
    yield
    await clients.shutdown()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "cv-biodiv-open-data-api", "url": "https://github.com/"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(meta.router)
app.include_router(species.router)
app.include_router(occurrences.router)
app.include_router(protected_areas.router)
app.include_router(beaches.router)


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/", include_in_schema=False)
async def root():
    """The portal is a single static page that talks to this same API."""
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return RedirectResponse("/docs")
