# -*- coding: utf-8 -*-
"""
Scraper para monapart.com (Tier 1, citywide).

El sitio es una app de JavaScript, pero el navegador carga los datos de una
API JSON publica propia (robots.txt permite todo) que devuelve TODOS los
alquileres de Barcelona en una sola llamada (_qty enorme = sin paginar), asi
que no hace falta Playwright. Descubierto el 2026-10-14 sondeando el sitio:

  https://thecat.monapart.com/web/estates/rent/<clave publica del sitio>?province=barcelona&_qty=...

Cada resultado trae: reference, slug, status ("" = disponible, "reserved",
"rented"), estateType (flat/house/office/...), price, areaConstructed,
areaUsable, rooms, furnished y address {zone, zoneGroup}. La ficha publica
es https://www.monapart.com/viviendas/<reference>.

Filtros propios (solo por senal explicita, UNKNOWN != REJECT):
- status "rented": ya esta alquilado (el feed los deja publicados, ~29 de 33).
- estateType de oficina/local/parking/etc: no es vivienda.
"""
import re

import requests

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone

API_URL = (
    "https://thecat.monapart.com/web/estates/rent/f1e4a71a4a65838e436061fbedb1cc42"
    "?province=barcelona&_qty=9007199254740991"
)
LISTING_URL = "https://www.monapart.com/viviendas/{reference}"

NON_HOUSING_ESTATE_TYPES = {
    "office", "premises", "local", "commercial", "garage", "parking",
    "storage", "storeroom", "land", "building", "warehouse", "industrial",
}


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def parse_results(results: list) -> list:
    """Separado de la request para poder probarlo con un JSON guardado."""
    listings = []
    for x in results:
        if (x.get("status") or "").lower() == "rented":
            continue
        if (x.get("estateType") or "").lower() in NON_HOUSING_ESTATE_TYPES:
            continue
        ref = x.get("reference")
        price = _num(x.get("price"))
        if not ref or price is None:
            continue

        addr = x.get("address") or {}
        slug_text = re.sub(r"[-_]+", " ", x.get("slug") or "")
        # Primero el barrio (mas preciso), despues el distrito, despues el slug.
        zone = (
            match_zone(addr.get("zone") or "")
            or match_zone(addr.get("zoneGroup") or "")
            or match_zone(slug_text)
        )
        if zone is None:
            continue

        m2 = _num(x.get("areaConstructed")) or _num(x.get("areaUsable"))
        rooms = x.get("rooms")
        title = slug_text.capitalize()
        if addr.get("zone"):
            title += f" ({addr['zone']})"
        if (x.get("status") or "").lower() == "reserved":
            title += " [reservado]"

        listings.append({
            "zone": zone,
            "title": title[:200],
            "price": price,
            "m2": m2,
            "beds": int(rooms) if isinstance(rooms, (int, float)) else None,
            "url": LISTING_URL.format(reference=ref),
            "source": "Monapart",
            "is_short_term": _looks_like_short_term(slug_text),
        })
    return listings


def scrape_all_zones():
    try:
        resp = requests.get(API_URL, headers={**REQUEST_HEADERS, "Accept": "application/json"}, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except (requests.RequestException, ValueError) as e:
        print(f"[monapart] Error al pedir la API: {e}")
        raise  # que main.run_citywide lo cuente como error de la fuente
    return parse_results(results)
