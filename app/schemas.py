from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Link(BaseModel):
    """A HAL-style hypermedia link."""

    href: str
    title: str | None = None


class Linked(BaseModel):
    """Mixin for resources that carry a `_links` object.

    Pydantic reserves leading underscores for private attributes, so the field
    is named `links` and serialised under its `_links` alias.
    """

    links: dict[str, Link] = Field(default_factory=dict, alias="_links")

    model_config = {"populate_by_name": True}


class Page(Linked, Generic[T]):
    total: int | None = Field(None, description="Total matches upstream, when known")
    limit: int
    offset: int
    end_of_records: bool = False
    results: list[T]
    sources: list[str] = Field(default_factory=list, description="Upstream datasets used")
    retrievedAt: str | None = Field(None, description="Timestamp of the upstream query, when known")


class Taxonomy(BaseModel):
    kingdom: str | None = None
    phylum: str | None = None
    class_: str | None = Field(None, alias="class")
    order: str | None = None
    family: str | None = None
    genus: str | None = None

    model_config = {"populate_by_name": True}


class  Species(Linked):
    gbif_key: int | None = None
    scientific_name: str
    canonical_name: str | None = None
    authorship: str | None = None
    rank: str | None = None
    taxonomic_status: str | None = None
    synonym: bool = False
    vernacular_names: list[str] = Field(default_factory=list)
    taxonomy: Taxonomy = Field(default_factory=Taxonomy)


class ConservationStatus(BaseModel):
    category: str | None = Field(None, description="IUCN category name, e.g. LEAST_CONCERN")
    code: str | None = Field(None, description="IUCN code, e.g. LC")
    iucn_taxon_id: str | None = None
    source: str = "GBIF / IUCN Red List"


class SpeciesSummary(BaseModel):
    title: str | None = None
    description: str | None = None
    extract: str | None = None
    url: str | None = None
    thumbnail: str | None = None
    source: str = "Wikipedia (CC BY-SA 4.0)"


class SpeciesDetail(Species):
    conservation: ConservationStatus | None = None
    summary: SpeciesSummary | None = None
    occurrence_count_cv: int | None = Field(
        None, description="GBIF occurrence records for this taxon in Cape Verde"
    )
    gbif_url: str | None = None


class Coordinates(BaseModel):
    latitude: float
    longitude: float
    uncertainty_m: float | None = None


class Occurrence(Linked):
    id: str
    source: Literal["gbif", "inaturalist"]
    scientific_name: str | None = None
    vernacular_name: str | None = None
    gbif_species_key: int | None = None
    event_date: str | None = None
    year: int | None = None
    coordinates: Coordinates | None = None
    locality: str | None = None
    basis_of_record: str | None = None
    dataset: str | None = Field(None, description="Dataset title, when the source provides one")
    dataset_key: str | None = Field(None, description="Upstream dataset identifier")
    iconic_taxon: str | None = Field(None, description="Coarse group label, e.g. Aves, Insecta, Plantae")
    recorded_by: str | None = None
    license: str | None = None
    media: list[str] = Field(default_factory=list)
    url: str | None = None
    taxonomy: Taxonomy = Field(default_factory=Taxonomy)


class ProtectedArea(BaseModel):
    id: str
    name: str
    designation: str | None = Field(
        None, description="Legal category, e.g. Parque Natural, Reserva Natural Integral"
    )
    island: str | None = None
    iucn_category: str | None = None
    marine: bool | None = Field(
        None, description="Only populated from WDPA; INGT does not classify marine areas"
    )
    area_ha: float | None = None
    reported_area_km2: float | None = None
    year_established: int | None = None
    wdpa_id: int | None = None
    coordinates: Coordinates | None = Field(
        None, description="Area-weighted centroid, for a map pin"
    )
    bbox: list[float] | None = Field(
        None, description="[west, south, east, north] in EPSG:4326"
    )
    legal_instrument: str | None = Field(
        None, description="The decree that established or regulates the area"
    )
    legal_instrument_url: str | None = None
    url: str | None = None
    data_quality: Literal["ingt", "wdpa"] = "ingt"


class Island(BaseModel):
    id: str
    name: str
    group: Literal["Barlavento", "Sotavento"]
    area_km2: float
    highest_point_m: int
    inhabited: bool


class SourceInfo(BaseModel):
    key: str
    name: str
    url: str
    license: str
    requires_token: bool = False
    enabled: bool = True
    used_for: list[str] = Field(default_factory=list)

class Beach(BaseModel):
    id: str
    name: str
    island: dict[str, str]
    coordinates: Coordinates | None = None
    sand: str | None = None
