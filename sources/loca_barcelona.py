# -*- coding: utf-8 -*-
"""
Scraper para www.locabarcelona.com

Antes pedíamos una URL por barrio (property-for-rent/<zona>/), pero esas
páginas mezclan alquileres de corto y largo plazo sin avisarlo en la card,
por eso te estaban llegando anuncios short-term. En cambio, pedimos la
única página que el sitio ya filtra por estado "long term rental"
(property-status/long-term-rental/) y de ahí separamos por zona buscando
el nombre del barrio en el texto de cada card.
"""
import re
import unicodedata
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS, ZONES

LONG_TERM_URL = "https://www.locabarcelona.com/en/property-status/long-term-rental/"

PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m2', re.IGNORECASE)
BED_RE = re.compile(r'(\d+)\s?Bedroom', re.IGNORECASE)

# Alias en español/con o sin tilde para matchear el nombre del barrio en el
# texto de la card (que viene en inglés en este sitio).
ZONE_ALIASES = {
    "Eixample": ["eixample"],
    "Sagrada Familia": ["sagrada familia", "sagrada família"],
    "Poblenou": ["poblenou", "poble nou"],
    "El Clot": ["el clot", "clot"],
    "Gracia": ["gracia", "gràcia"],
    "Barceloneta": ["barceloneta"],
    "Vila Olimpica": ["vila olimpica", "vila olímpica"],
}


def _normalize(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def _match_zone(text: str):
    norm = _normalize(text)
    for zone in ZONES:
        for alias in ZONE_ALIASES.get(zone, [zone]):
            if _normalize(alias) in norm:
                return zone
    return None


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def _find_m2_and_beds(anchor):
    node = anchor
    for _ in range(5):
        node = node.parent
        if node is None:
            break
        text = node.get_text(" ", strip=True)
        m2_match = M2_RE.search(text)
        if m2_match:
            bed_match = BED_RE.search(text)
            m2 = float(m2_match.group(1).replace(",", "."))
            beds = int(bed_match.group(1)) if bed_match else None
            return m2, beds
    return None, None


def scrape_all_zones():
    """Devuelve los anuncios de long-term rental que matchean alguna de
    nuestras zonas configuradas (ZONES en config.py). Una sola request para
    toda la ciudad, no una por barrio."""
    listings = []
    try:
        resp = requests.get(LONG_TERM_URL, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[loca_barcelona] Error al pedir {LONG_TERM_URL}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=re.compile(r"/property/"))

    seen_urls_this_page = set()
    for a in anchors:
        href = a.get("href")
        if not href or href in seen_urls_this_page:
            continue
        text = a.get_text(" ", strip=True)
        price_match = PRICE_RE.search(text)
        if not price_match:
            continue

        zone = _match_zone(text)
        if zone is None:
            continue  # no es ninguna de las zonas que te interesan

        seen_urls_this_page.add(href)
        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        m2, beds = _find_m2_and_beds(a)

        listings.append({
            "zone": zone,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": beds,
            "url": href,
            "source": "Loca Barcelona",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
