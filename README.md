## Cabo Verde Biodiversidade Open Data API

An open API aggregating biodiversity observations, species
information, conservation status and protected areas for **Cape Verde**.

**v1 is deliberately stateless.** Every request fans out to public upstream APIs, normalises the responses
into one consistent schema, and caches them in memory for a few minutes.

```
                      ┌──────────────┐
             client──>│  API         │──> GBIF                (occurrences, taxonomy, IUCN)
                      │              │──> iNaturalist         (community observations)
                      │              │──> Wikipedia           (species descriptions)
                      └──────────────┘──> Protected Planet    (optional, token-gated)
```

## Quick start

```bash
uv sync
uv run main.py           # http://127.0.0.1:8000
```

- Portal: <http://127.0.0.1:8000/>
- Interactive docs: <http://127.0.0.1:8000/docs>
- OpenAPI schema: <http://127.0.0.1:8000/openapi.json>

No configuration is required. `cp .env.example .env` only if you want to
override defaults or add a Protected Planet token.

## Endpoints

| Endpoint                               | What it does                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------- |
| `GET /health`                          | Liveness plus cache hit-rate                                                                  |
| `GET /v1/species/search?q=`            | Search the GBIF backbone by scientific or common name                                         |
| `GET /v1/species/resolve?name=`        | Fuzzy-match a scientific name to a full profile                                               |
| `GET /v1/species/top?limit=`           | Most-recorded species in Cape Verde                                                           |
| `GET /v1/species/{key}`                | Merged profile: taxonomy, common names, IUCN status, Wikipedia summary, national record count |
| `GET /v1/species/{key}/conservation`   | IUCN Red List category alone                                                                  |
| `GET /v1/occurrences`                  | Records in Cape Verde — filter by taxon, name, year, basis of record, coordinates             |
| `GET /v1/occurrences/stats`            | National totals, breakdown by kingdom, basis of record and year                               |
| `GET /v1/observations`                 | Community observations from iNaturalist                                                       |
| `GET /v1/protected-areas`              | All 47 protected areas, filterable by island and legal category                               |
| `GET /v1/protected-areas/designations` | The five legal categories, with counts and total area                                         |
| `GET /v1/protected-areas/{id}`         | One protected area, with area, centroid, bbox and establishing decree                         |
| `GET /v1/islands`                      | The ten islands, with area and highest point                                                  |
| `GET /v1/sources`                      | Every upstream source, its licence, and whether it is enabled                                 |

Species and occurrence responses carry hypermedia `_links` — see
[Hypermedia (HATEOAS)](#hypermedia-hateoas).

A species profile assembles four upstream calls concurrently:

```bash
curl 'http://127.0.0.1:8000/v1/species/resolve?name=Calonectris%20edwardsii'
```

```json
{
  "gbif_key": 2481518,
  "scientific_name": "Calonectris edwardsii (Oustalet, 1883)",
  "vernacular_names": ["cagarra-de-cabo-verde", "Cape Verde Shearwater"],
  "taxonomy": { "class": "Aves", "family": "Procellariidae" },
  "conservation": { "category": "NEAR_THREATENED", "code": "NT" },
  "summary": {
    "extract": "The Cape Verde shearwater, or cagarra locally, is …"
  },
  "occurrence_count_cv": 1078
}
```

## Hypermedia (HATEOAS)

Species and occurrence responses carry a HAL-style `_links` object so a client
can navigate the API without hardcoding URL templates. Reference collections
(islands, sources, protected areas, stats) are leaves with nothing to link to,
so they stay plain.

A species links to everything you can do next with it:

```json
"_links": {
  "self":         { "href": "/v1/species/2481518", "title": "Full species profile" },
  "conservation": { "href": "/v1/species/2481518/conservation", "title": "IUCN Red List status" },
  "occurrences":  { "href": "/v1/occurrences?taxon_key=2481518", "title": "Records of this taxon in Cape Verde" },
  "observations": { "href": "/v1/observations?scientific_name=Calonectris+edwardsii", "title": "Community observations" },
  "gbif":         { "href": "https://www.gbif.org/species/2481518", "title": "GBIF species page" }
}
```

An occurrence links back at its taxon and out at the original record:

```json
"_links": {
  "species":             { "href": "/v1/species/2481518" },
  "species_occurrences": { "href": "/v1/occurrences?taxon_key=2481518" },
  "source_record":       { "href": "https://www.gbif.org/occurrence/5938415534" }
}
```

## Tests

```bash
uv run pytest
```

## Licence

Licensed under MIT for the code. Data licences are upstream's, not ours.
