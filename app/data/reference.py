from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas import Island, ProtectedArea

DATA_DIR = Path(__file__).resolve().parent

ISLANDS: list[Island] = [
    Island(id="santo-antao", name="Santo Antão", group="Barlavento", area_km2=779.0, highest_point_m=1979, inhabited=True),
    Island(id="sao-vicente", name="São Vicente", group="Barlavento", area_km2=227.0, highest_point_m=725, inhabited=True),
    Island(id="santa-luzia", name="Santa Luzia", group="Barlavento", area_km2=35.0, highest_point_m=395, inhabited=False),
    Island(id="sao-nicolau", name="São Nicolau", group="Barlavento", area_km2=343.0, highest_point_m=1304, inhabited=True),
    Island(id="sal", name="Sal", group="Barlavento", area_km2=216.0, highest_point_m=406, inhabited=True),
    Island(id="boa-vista", name="Boa Vista", group="Barlavento", area_km2=620.0, highest_point_m=387, inhabited=True),
    Island(id="maio", name="Maio", group="Sotavento", area_km2=269.0, highest_point_m=436, inhabited=True),
    Island(id="santiago", name="Santiago", group="Sotavento", area_km2=991.0, highest_point_m=1394, inhabited=True),
    Island(id="fogo", name="Fogo", group="Sotavento", area_km2=476.0, highest_point_m=2829, inhabited=True),
    Island(id="brava", name="Brava", group="Sotavento", area_km2=64.0, highest_point_m=976, inhabited=True),
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

BEACH_SOURCES = {
    "s1": {
      "name": "Wikipedia — List of beaches of Cape Verde",
      "url": "https://en.wikipedia.org/wiki/List_of_beaches_of_Cape_Verde"
    },
    "s2": {
      "name": "Paulina on the Road — 20 Best Beaches in Cape Verde",
      "url": "https://paulinaontheroad.com/best-beaches-in-cape-verde/"
    },
    "s3": {
      "name": "CapeVerde.co.uk — Best beaches in Sal and Boa Vista",
      "url": "https://www.capeverde.co.uk/blog/the-best-beaches-in-sal-and-boa-vista"
    },
    "s4": {
      "name": "VOIHotels — Best beaches in Cape Verde",
      "url": "https://www.voihotels.com/en/travel-stories/best-beaches-cape-verde"
    },
    "s5": {
      "name": "Made For Travellers — Which Cape Verde island has the best beaches",
      "url": "https://madefortravellers.com/cape-verde-island-best-beaches/"
    },
    "s6": {
      "name": "CaboWork — 10 Best Beaches in Cape Verde",
      "url": "https://cabowork.com/beaches-in-cape-verde/"
    },
    "s7": {
      "name": "The Trip Verdict — Best Beaches in Cabo Verde",
      "url": "https://www.thetripverdict.com/best-beaches-in-cabo-verde"
    },
    "s9": {
      "name": "Barcelo Guide — Beaches on the island of Santiago",
      "url": "https://www.barcelo.com/guia-turismo/en/cape-verde/praia-cabo-verde/things-to-do/beaches-island-of-santiago/"
    },
    "s10": {
      "name": "CapeVerdeIslands.org — Top 5 beaches of Cape Verde",
      "url": "https://capeverdeislands.org/top-5-beaches-cape-verde-2"
    },
    "s12": {
      "name": "CaboVerde-Info.com — Praias (per-island beach counts)",
      "url": "https://www.caboverde-info.com/Identidade/Geografia/Artigos/Praias"
    },
    "s13": {
      "name": "Wikipedia — Quebra Canela",
      "url": "https://en.wikipedia.org/wiki/Quebra_Canela"
    },
    "s14": {
      "name": "Wikipedia — Prainha, Praia",
      "url": "https://en.wikipedia.org/wiki/Prainha,_Praia"
    },
    "s15": {
      "name": "La Conciergerie — 5 best beaches in Santiago Island",
      "url": "https://www.laconciergerie.cv/discover-the-5-best-beaches-in-santiago-island-cape-verde-2/"
    },
    "s16": {
      "name": "Wikipedia — Praia dos Flamengos",
      "url": "https://en.wikipedia.org/wiki/Praia_dos_Flamengos"
    },
    "s17": {
      "name": "Cape Verde Travel Guide — São Vicente island",
      "url": "https://caboverdetravelguide.com/en/sao-vicente-island/"
    },
    "s18": {
      "name": "Villa Maio / Discover Cape Verde — Beach adventures",
      "url": "https://www.villamaio.com/most-beautiful-beach-adventures-cape-verde/"
    },
    "s19": {
      "name": "Visit Cabo Verde — 18 praias secretas",
      "url": "https://www.visit-caboverde.com/blog/18-praias-secretas-em-cabo-verde-para-explorar"
    },
    "s20": {
      "name": "Ilha de Fogo — Praias",
      "url": "https://ilhadefogo.org/praias-2/"
    },
    "s21": {
      "name": "Ilha de Fogo — Município de São Filipe",
      "url": "https://ilhadefogo.org/sobre-o-fogo/municipio-de-sao-filipe/"
    },
    "s22": {
      "name": "Visit Cabo Verde — Melhores locais para descontrair (Santo Antão)",
      "url": "https://www.visit-caboverde.com/blog/destino-de-praia-e-puro-relaxamento-melhores-locais-para-descontrair-nas-ilhas-de-cabo-verde"
    },
    "s23": {
      "name": "Visit Cabo Verde — São Nicolau island",
      "url": "https://www.visit-caboverde.com/en/islands/sao-nicolau-island"
    },
    "s24": {
      "name": "Wikipedia — Praia Branca",
      "url": "https://en.wikipedia.org/wiki/Praia_Branca"
    },
    "s25": {
      "name": "Aproxima Viagem — Boavista, a ilha da tranquilidade",
      "url": "https://www.aproximaviagem.pt/la-fora/boavista-ilha-da-tranquilidade/"
    },
    "s26": {
      "name": "Alma de Viajante — Visitar a ilha da Boa Vista",
      "url": "https://www.almadeviajante.com/visitar-ilha-boa-vista-cabo-verde/"
    },
    "s27": {
      "name": "Viajar Entre Viagens — Boa Vista",
      "url": "https://viajarentreviagens.pt/cabo-verde/boa-vista-a-ilha-da-felicidade/"
    },
    "s28": {
      "name": "VagaMundos — Boa Vista (Praia d'Cruz festival)",
      "url": "https://www.vagamundos.pt/visitar-ilha-da-boa-vista-roteiro/"
    },
    "s29": {
      "name": "TopAtlantico blog — Conheça todas as ilhas",
      "url": "https://blog.topatlantico.pt/ferias-na-praia/cabo-verde-nao-e-so-sal-e-boa-vista-conheca-todas-as-ilhas"
    },
    "s31": {
      "name": "isitourism-caboverde — Brava, a ilha das flores",
      "url": "https://isitourism-caboverde.com/st_location/cabo-verde/brava/"
    },
    "s33": {
      "name": "VagaMundos — Visitar a Ilha do Sal (Porto Antigo)",
      "url": "https://www.vagamundos.pt/visitar-ilha-do-sal-roteiro/"
    },
    "s34": {
      "name": "Glitter Guide / SAPO — Santiago (São Francisco)",
      "url": "https://sapo.pt/artigo/glitter-guide-cabo-verde-69e3658f2a6983a5f92bf7a7"
    },
    "s35": {
      "name": "Wikipedia — Praia de Santa Maria",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Santa_Maria"
    },
    "s36": {
      "name": "Wikipedia — Ponta Preta (Southern Sal)",
      "url": "https://en.wikipedia.org/wiki/Ponta_Preta_(Southern_Sal)"
    },
    "s37": {
      "name": "Wikipedia — Ponta da Fragata / Costa da Fragata",
      "url": "https://en.wikipedia.org/wiki/Ponta_da_Fragata"
    },
    "s38": {
      "name": "Wikipedia — Praia de Chaves",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Chaves"
    },
    "s39": {
      "name": "Wikipedia — Praia de Santa Mónica",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Santa_M%C3%B3nica"
    },
    "s40": {
      "name": "Wikipedia — Praia de Carquejinha",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Carquejinha"
    },
    "s41": {
      "name": "Wikipedia — Praia de Atalanta (Cabo Santa Maria shipwreck)",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Atalanta"
    },
    "s42": {
      "name": "Wikipedia — Sal Rei",
      "url": "https://en.wikipedia.org/wiki/Sal_Rei"
    },
    "s43": {
      "name": "Wikipedia — Praia de Cabral",
      "url": "https://en.wikipedia.org/wiki/Praia_de_Cabral"
    },
    "s44": {
      "name": "Wikipedia — Baía de Tarrafal (Santiago)",
      "url": "https://en.wikipedia.org/wiki/Ba%C3%ADa_de_Tarrafal"
    },
    "s45": {
      "name": "Wikipedia — Ribeira da Prata (Santiago)",
      "url": "https://en.wikipedia.org/wiki/Ribeira_da_Prata"
    },
    "s46": {
      "name": "Wikipedia — Matiota (Praia da Laginha, Mindelo)",
      "url": "https://en.wikipedia.org/wiki/Matiota"
    },
    "s47": {
      "name": "Wikipedia — Baía das Gatas",
      "url": "https://en.wikipedia.org/wiki/Ba%C3%ADa_das_Gatas"
    },
    "s48": {
      "name": "Wikipedia — São Pedro, Cape Verde",
      "url": "https://en.wikipedia.org/wiki/S%C3%A3o_Pedro,_Cape_Verde"
    },
    "s49": {
      "name": "Wikipedia — Porto Inglês (Cidade do Maio)",
      "url": "https://en.wikipedia.org/wiki/Porto_Ingl%C3%AAs"
    },
    "s50": {
      "name": "Wikipedia — Tarrafal de Monte Trigo (Santo Antão)",
      "url": "https://en.wikipedia.org/wiki/Tarrafal_de_Monte_Trigo"
    },
    "s51": {
      "name": "Wikipedia — Ponta do Sol, Cape Verde (Santo Antão)",
      "url": "https://en.wikipedia.org/wiki/Ponta_do_Sol,_Cape_Verde"
    },
    "s52": {
      "name": "Wikipedia — Tarrafal de São Nicolau",
      "url": "https://en.wikipedia.org/wiki/Tarrafal_de_S%C3%A3o_Nicolau,_Cape_Verde"
    },
    "s53": {
      "name": "Wikipedia — Juncalinho",
      "url": "https://en.wikipedia.org/wiki/Juncalinho"
    },
    "s54": {
      "name": "Wikipedia — Boa Vista, Cape Verde (island beach list)",
      "url": "https://en.wikipedia.org/wiki/Boa_Vista,_Cape_Verde"
    },
    "s55": {
      "name": "Wikipedia — Santa Maria, Cape Verde (town)",
      "url": "https://en.wikipedia.org/wiki/Santa_Maria,_Cape_Verde"
    },
    "s56": {
      "name": "Wikipedia — Praia (capital)",
      "url": "https://en.wikipedia.org/wiki/Praia"
    },
    "s57": {
      "name": "Wikipedia — Ribeira do Calhau (Calhau, São Vicente)",
      "url": "https://en.wikipedia.org/wiki/Ribeira_do_Calhau"
    },
    "s58": {
      "name": "Wikipedia — São Filipe, Cape Verde",
      "url": "https://en.wikipedia.org/wiki/S%C3%A3o_Filipe,_Cape_Verde"
    },
    "s59": {
      "name": "Wikipedia — Fogo, Cape Verde",
      "url": "https://en.wikipedia.org/wiki/Fogo,_Cape_Verde"
    }
  }
