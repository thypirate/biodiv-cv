"""Route-level tests. Upstream adapters are stubbed so the suite never
touches the network."""

import pytest

from app.sources import gbif, inaturalist, protectedplanet
from tests.test_normalizers import GBIF_OCCURRENCE, GBIF_SPECIES


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "cache" in body


def test_islands(client):
    islands = client.get("/v1/islands").json()
    assert len(islands) == 10
    assert {i["group"] for i in islands} == {"Barlavento", "Sotavento"}


def test_sources_lists_licences(client):
    sources = {s["key"]: s for s in client.get("/v1/sources").json()}
    assert sources["gbif"]["enabled"] is True
    assert sources["protected-planet"]["requires_token"] is True


def test_protected_areas_serve_the_official_ingt_dataset(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    body = client.get("/v1/protected-areas").json()

    assert body["sources"] == ["ingt"]
    assert body["total"] == 47  # the full national network
    assert body["source"]["publisher"].startswith("Instituto Nacional")
    assert body["note"]
    assert all(a["data_quality"] == "ingt" for a in body["results"])
    assert round(body["total_area_km2"]) == 2078


def test_protected_areas_filter_by_island_and_designation(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)

    sal = client.get("/v1/protected-areas?island=Sal").json()
    assert sal["total"] == 11
    assert all(a["island"] == "Sal" for a in sal["results"])

    parks = client.get("/v1/protected-areas?designation=Parque Natural").json()
    assert parks["total"] == 13
    assert all(a["designation"] == "Parque Natural" for a in parks["results"])

    combined = client.get("/v1/protected-areas?island=Boa Vista&designation=Monumento").json()
    assert combined["total"] == 4


def test_protected_area_records_carry_real_attributes(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    area = client.get("/v1/protected-areas/pa-parque-natural-do-fogo").json()

    assert area["name"] == "Parque Natural do Fogo"
    assert area["island"] == "Fogo"
    assert area["designation"] == "Parque Natural"
    assert area["area_ha"] == pytest.approx(8459.1, abs=1)
    assert area["legal_instrument"]
    assert area["legal_instrument_url"].startswith("https://")
    # Centroid must sit on Fogo, not in the ocean off Brazil.
    assert 14.8 < area["coordinates"]["latitude"] < 15.1
    assert -24.6 < area["coordinates"]["longitude"] < -24.2
    west, south, east, north = area["bbox"]
    assert west < area["coordinates"]["longitude"] < east
    assert south < area["coordinates"]["latitude"] < north


def test_every_protected_area_centroid_is_inside_cape_verde(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    for area in client.get("/v1/protected-areas").json()["results"]:
        lat = area["coordinates"]["latitude"]
        lon = area["coordinates"]["longitude"]
        assert 14.0 < lat < 18.0, area["name"]
        assert -26.0 < lon < -22.0, area["name"]


def test_protected_area_islands_match_the_islands_endpoint(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    known = {i["name"] for i in client.get("/v1/islands").json()}
    used = {a["island"] for a in client.get("/v1/protected-areas").json()["results"]}
    assert used <= known, used - known


def test_designations_summary(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    rows = client.get("/v1/protected-areas/designations").json()
    assert {r["designation"] for r in rows} == {
        "Parque Natural",
        "Reserva Natural",
        "Reserva Natural Integral",
        "Monumento Natural",
        "Paisagem Protegida",
    }
    assert sum(r["count"] for r in rows) == 47
    assert rows[0]["count"] >= rows[-1]["count"]  # sorted by count, descending


def test_protected_area_not_found(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    assert client.get("/v1/protected-areas/nope").status_code == 404


def test_species_search(client, monkeypatch):
    async def fake(q, *, rank, limit, offset):
        return {"count": 1, "endOfRecords": True, "results": [GBIF_SPECIES]}

    monkeypatch.setattr(gbif, "search_species", fake)
    body = client.get("/v1/species/search?q=Calonectris").json()
    assert body["total"] == 1
    assert body["sources"] == ["gbif"]
    assert body["results"][0]["canonical_name"] == "Calonectris edwardsii"


def test_species_search_rejects_short_query(client):
    assert client.get("/v1/species/search?q=a").status_code == 422


def test_species_detail_merges_every_source(client, monkeypatch):
    async def detail(key):
        return GBIF_SPECIES

    async def names(key):
        return ["cagarra-de-cabo-verde"]

    async def iucn(key):
        from app.schemas import ConservationStatus

        return ConservationStatus(category="NEAR_THREATENED", code="NT")

    async def count(taxon_key=None):
        return 1078

    async def summary(name):
        from app.schemas import SpeciesSummary

        return SpeciesSummary(title="Cape Verde shearwater", extract="A seabird.")

    from app.sources import wikipedia

    monkeypatch.setattr(gbif, "species_detail", detail)
    monkeypatch.setattr(gbif, "vernacular_names", names)
    monkeypatch.setattr(gbif, "iucn_category", iucn)
    monkeypatch.setattr(gbif, "occurrence_count", count)
    monkeypatch.setattr(wikipedia, "summary", summary)

    body = client.get("/v1/species/2481518").json()
    assert body["conservation"]["code"] == "NT"
    assert body["summary"]["title"] == "Cape Verde shearwater"
    assert body["occurrence_count_cv"] == 1078
    assert body["gbif_url"].endswith("/2481518")


def test_species_detail_404(client, monkeypatch):
    async def missing(key):
        return None

    monkeypatch.setattr(gbif, "species_detail", missing)
    assert client.get("/v1/species/1").status_code == 404


def test_occurrences_resolve_name_to_taxon_key(client, monkeypatch):
    seen = {}

    async def match(name):
        return {"usageKey": 2481518}

    async def search(**kwargs):
        seen.update(kwargs)
        return {"count": 1, "endOfRecords": True, "results": [GBIF_OCCURRENCE]}

    monkeypatch.setattr(gbif, "match_name", match)
    monkeypatch.setattr(gbif, "search_occurrences", search)

    body = client.get("/v1/occurrences?scientific_name=Calonectris edwardsii").json()
    assert seen["taxon_key"] == 2481518
    assert body["results"][0]["source"] == "gbif"


def test_occurrences_unknown_name_404(client, monkeypatch):
    async def match(name):
        return None

    monkeypatch.setattr(gbif, "match_name", match)
    assert client.get("/v1/occurrences?scientific_name=Nope nope").status_code == 404


@pytest.mark.parametrize("limit", [0, 301])
def test_occurrences_limit_bounds(client, limit):
    assert client.get(f"/v1/occurrences?limit={limit}").status_code == 422


def test_observations_translate_offset_to_page(client, monkeypatch):
    seen = {}

    async def obs(**kwargs):
        seen.update(kwargs)
        return {"total_results": 100, "results": []}

    monkeypatch.setattr(inaturalist, "observations", obs)
    client.get("/v1/observations?limit=20&offset=40")
    assert seen["page"] == 3
    assert seen["per_page"] == 20


def test_species_carries_hypermedia_links(client, monkeypatch):
    async def fake(q, *, rank, limit, offset):
        return {"count": 100, "endOfRecords": False, "results": [GBIF_SPECIES]}

    monkeypatch.setattr(gbif, "search_species", fake)
    body = client.get("/v1/species/search?q=Calonectris&limit=10&offset=10").json()

    page = body["_links"]
    assert page["self"]["href"] == "/v1/species/search?q=Calonectris&limit=10&offset=10"
    assert page["prev"]["href"].endswith("offset=0")
    assert page["next"]["href"].endswith("offset=20")
    assert page["first"]["href"].endswith("offset=0")

    species = body["results"][0]["_links"]
    assert species["self"]["href"] == "/v1/species/2481518"
    assert species["conservation"]["href"] == "/v1/species/2481518/conservation"
    assert species["occurrences"]["href"] == "/v1/occurrences?taxon_key=2481518"
    assert species["gbif"]["href"].startswith("https://www.gbif.org/")


def test_last_page_has_no_next_link(client, monkeypatch):
    async def fake(q, *, rank, limit, offset):
        return {"count": 5, "endOfRecords": True, "results": []}

    monkeypatch.setattr(gbif, "search_species", fake)
    page = client.get("/v1/species/search?q=Calonectris&limit=10").json()["_links"]
    assert "next" not in page
    assert "prev" not in page


def test_occurrence_links_point_back_at_the_taxon(client, monkeypatch):
    async def search(**kwargs):
        return {"count": 1, "endOfRecords": True, "results": [GBIF_OCCURRENCE]}

    monkeypatch.setattr(gbif, "search_occurrences", search)
    links = client.get("/v1/occurrences").json()["results"][0]["_links"]
    assert links["species"]["href"] == "/v1/species/1234"
    assert links["species_occurrences"]["href"] == "/v1/occurrences?taxon_key=1234"
    assert links["source_record"]["href"].startswith("https://www.gbif.org/occurrence/")


def test_observation_without_gbif_key_links_to_resolve(client, monkeypatch):
    from tests.test_normalizers import INAT_OBSERVATION

    async def obs(**kwargs):
        return {"total_results": 1, "results": [INAT_OBSERVATION]}

    monkeypatch.setattr(inaturalist, "observations", obs)
    links = client.get("/v1/observations").json()["results"][0]["_links"]
    assert links["species"]["href"] == "/v1/species/resolve?name=Junonia+oenone"


def test_reference_endpoints_have_no_links(client, monkeypatch):
    async def no_token(**_):
        return None

    monkeypatch.setattr(protectedplanet, "list_areas", no_token)
    assert "_links" not in client.get("/v1/protected-areas").json()
    assert all("_links" not in i for i in client.get("/v1/islands").json())


def test_stats_survives_inaturalist_being_down(client, monkeypatch):
    """A national overview should not go dark because one secondary counter
    is unavailable — the GBIF figures are still perfectly good."""

    async def gbif_total(taxon_key=None):
        return 242334

    async def gbif_facets(fields, *, facet_limit=12):
        return {"KINGDOM_KEY": [{"key": "1", "count": 159368}]}

    async def inat_down():
        return None

    monkeypatch.setattr(gbif, "occurrence_count", gbif_total)
    monkeypatch.setattr(gbif, "facets", gbif_facets)
    monkeypatch.setattr(inaturalist, "observation_count", inat_down)

    body = client.get("/v1/occurrences/stats").json()
    assert body["gbif_occurrences"] == 242334
    assert body["inaturalist_observations"] is None
    assert body["unavailable_sources"] == ["inaturalist"]
    assert body["sources"] == ["gbif"]
    assert body["by_kingdom"] == [{"kingdom": "Animalia", "count": 159368}]
