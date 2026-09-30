# -*- coding: utf-8 -*-
"""
Scraper para inmobiliariaenbarcelona.finquesbou.es

Inventario chico (unos pocos alquileres a la vez), pero fácil de leer.
Solo pisos/viviendas (se excluyen locales, parkings y naves por el patrón
del link). Cada card trae algo como "Piso en X de 175 m2 --- 2.508 € ---
Referencia: ...".
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts

URL = "https://inmobiliariaenbarcelona.finquesbou.es/propiedades/alquiler/defecto"

CARD_HREF_RE = re.compile(r"/propiedad/(piso|vivienda|atico|duplex)-[^\"']+", re.IGNORECASE)
PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m2', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?(?:Habitaciones|Hab\.)', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def scrape_all_zones():
    listings = []
    try:
        resp = requests.get(URL, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[finques_bou] Error al pedir {URL}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=CARD_HREF_RE)

    seen_urls = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://inmobiliariaenbarcelona.finquesbou.es" + href
        if href in seen_urls:
            continue

        text = None
        for candidate in ancestor_texts(a, levels=4):
            if PRICE_RE.search(candidate) and M2_RE.search(candidate):
                text = candidate
                break
        if text is None:
            continue

        zone = match_zone(text)
        if zone is None:
            continue

        price_match = PRICE_RE.search(text)
        m2_match = M2_RE.search(text)
        rooms_match = ROOMS_RE.search(text)

        seen_urls.add(href)
        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        m2 = float(m2_match.group(1).replace(",", "."))

        listings.append({
            "zone": zone,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": int(rooms_match.group(1)) if rooms_match else None,
            "url": href,
            "source": "Finques Bou",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
