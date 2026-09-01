"""Normalisers are the part of this API that is genuinely ours, so they are
tested against captured upstream payload shapes rather than live calls."""

from app.sources import gbif, inaturalist

GBIF_OCCURRENCE = {
    "key": 5938415534,
    "scientificName": "Spoladea recurvalis (Fabricius, 1775)",
    "speciesKey": 1234,
    "eventDate": "2026-01-01",
    "year": 2026,
    "decimalLatitude": 16.9,
    "decimalLongitude": -25.0,
    "coordinateUncertaintyInMeters": 30.0,
    "locality": "Santo Antão",
    "basisOfRecord": "HUMAN_OBSERVATION",
    "datasetKey": "50c9509d-22c7-4a22-a47d-8c48425ef4a7",
    "datasetName": "iNaturalist research-grade observations",
    "recordedBy": "someone",
    "license": "http://creativecommons.org/licenses/by-nc/4.0/legalcode",
    "kingdom": "Animalia",
    "class": "Insecta",
    "extensions": {
        "http://rs.gbif.org/terms/1.0/Multimedia": [
            {"http://purl.org/dc/terms/identifier": "https://example.test/photo.jpg"}
        ]
    },
}

GBIF_SPECIES = {
    "key": 2481518,
    "nubKey": 2481518,
    "scientificName": "Calonectris edwardsii (Oustalet, 1883)",
    "canonicalName": "Calonectris edwardsii",
    "authorship": "(Oustalet, 1883)",
    "rank": "SPECIES",
    "taxonomicStatus": "ACCEPTED",
    "synonym": False,
    "kingdom": "Animalia",
    "class": "Aves",
    "family": "Procellariidae",
    "vernacularNames": [
        {"vernacularName": "Cape Verde Shearwater", "language": "eng"},
        {"vernacularName": "cagarra-de-cabo-verde", "language": "por"},
        {"vernacularName": "オオミズナギドリ", "language": "jpn"},
    ],
}

INAT_OBSERVATION = {
    "id": 394083334,
    "observed_on": "2026-08-23",
    "time_observed_at": "2026-08-23T11:49:46-01:00",
    "place_guess": "Ribeira Grande de Santiago, CV",
    "quality_grade": "research",
    "uri": "https://www.inaturalist.org/observations/394083334",
    "license_code": "cc-by-nc",
    "positional_accuracy": 3,
    "geojson": {"type": "Point", "coordinates": [-23.604, 14.917]},
    "user": {"login": "lasselehmann"},
    "taxon": {
        "name": "Junonia oenone",
        "preferred_common_name": "Blue-spot Pansy",
        "iconic_taxon_name": "Insecta",
    },
    "photos": [{"url": "https://example.test/photos/1/square.jpg"}],
}


def test_gbif_occurrence_normalises():
    occ = gbif.to_occurrence(GBIF_OCCURRENCE)
    assert occ.source == "gbif"
    assert occ.id == "5938415534"
    assert occ.coordinates.latitude == 16.9
    assert occ.coordinates.longitude == -25.0
    assert occ.dataset == "iNaturalist research-grade observations"
    assert occ.dataset_key == "50c9509d-22c7-4a22-a47d-8c48425ef4a7"
    assert occ.media == ["https://example.test/photo.jpg"]
    assert occ.taxonomy.class_ == "Insecta"
    assert occ.url.endswith("/5938415534")


def test_gbif_occurrence_without_coordinates():
    occ = gbif.to_occurrence({"key": 1, "scientificName": "X"})
    assert occ.coordinates is None
    assert occ.media == []


def test_gbif_species_prefers_portuguese_then_english():
    species = gbif.to_species(GBIF_SPECIES)
    assert species.gbif_key == 2481518
    assert species.vernacular_names[:2] == ["cagarra-de-cabo-verde", "Cape Verde Shearwater"]
    assert "オオミズナギドリ" not in species.vernacular_names
    assert species.taxonomy.class_ == "Aves"


def test_inat_observation_normalises():
    occ = inaturalist.to_occurrence(INAT_OBSERVATION)
    assert occ.source == "inaturalist"
    assert occ.vernacular_name == "Blue-spot Pansy"
    assert occ.coordinates.latitude == 14.917  # geojson is lon,lat — must not be swapped
    assert occ.coordinates.longitude == -23.604
    assert occ.year == 2026
    assert occ.iconic_taxon == "Insecta"
    assert occ.taxonomy.kingdom is None  # iconic taxon is not a kingdom
    assert occ.media == ["https://example.test/photos/1/medium.jpg"]
