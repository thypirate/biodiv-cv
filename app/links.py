from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from app.schemas import Link

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import Request

    from app.schemas import Occurrence


def species_links(key: int | None, canonical_name: str | None = None) -> dict[str, Link]:
    """Everything you can do next with a species."""
    if not key:
        return {}
    links = {
        "self": Link(href=f"/v1/species/{key}", title="Full species profile"),
        "conservation": Link(
            href=f"/v1/species/{key}/conservation", title="IUCN Red List status"
        ),
        "occurrences": Link(
            href=f"/v1/occurrences?taxon_key={key}",
            title="Records of this taxon in Cape Verde",
        ),
        "gbif": Link(href=f"https://www.gbif.org/species/{key}", title="GBIF species page"),
    }
    if canonical_name:
        query = urlencode({"scientific_name": canonical_name})
        links["observations"] = Link(
            href=f"/v1/observations?{query}", title="Community observations"
        )
    return links


def occurrence_links(occurrence: "Occurrence") -> dict[str, Link]:
    """A record points back at its taxon and out at the source record."""
    links: dict[str, Link] = {}
    if occurrence.url:
        links["source_record"] = Link(
            href=occurrence.url, title=f"Original record on {occurrence.source}"
        )
    key = occurrence.gbif_species_key
    if key:
        links["species"] = Link(href=f"/v1/species/{key}", title="Species profile")
        links["species_occurrences"] = Link(
            href=f"/v1/occurrences?taxon_key={key}", title="Other records of this taxon"
        )
    elif occurrence.scientific_name:
        query = urlencode({"name": occurrence.scientific_name})
        links["species"] = Link(
            href=f"/v1/species/resolve?{query}", title="Resolve this name to a species"
        )
    return links


def page_links(
    request: "Request", *, limit: int, offset: int, total: int | None
) -> dict[str, Link]:
    """Pagination links derived from the request that produced the page."""

    def at(new_offset: int) -> str:
        params = dict(request.query_params)
        params["limit"] = str(limit)
        params["offset"] = str(new_offset)
        return f"{request.url.path}?{urlencode(params)}"

    links = {
        "self": Link(href=at(offset), title="This page"),
        "first": Link(href=at(0), title="First page"),
    }
    if offset > 0:
        links["prev"] = Link(href=at(max(0, offset - limit)), title="Previous page")
    if total is None or offset + limit < total:
        links["next"] = Link(href=at(offset + limit), title="Next page")
    return links
