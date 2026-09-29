# -*- coding: utf-8 -*-
"""
Scraper para finquesteixidor.com

Citywide, ~23 resultados sin paginación. Cada card tiene un link tipo
/ca/alquiler-pisos-barcelona.cfm/ID/<num>/CAT/<slug>.htm con precio, m2 y
barrio (ej "SANT ANTONI", "EIXAMPLE DRET") en el texto del contenedor.
Algún que otro anuncio dice "temporada" (se filtra con EXCLUDE_KEYWORDS,
no hace falta nada especial acá).
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts

URL = "https://www.finquesteixidor.com/ca/alquiler-barcelona.cfm"

CARD_HREF_RE = re.compile(r"/ca/alquiler-pisos-barcelona\.cfm/ID/\d+/CAT/[^\"']+\.htm")
PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?hab', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def scrape_all_zones():
    listings = []
    try:
        resp = requests.get(URL, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[finques_teixidor] Error al pedir {URL}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=CARD_HREF_RE)

    seen_urls = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.finquesteixidor.com" + href
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
            "source": "Finques Teixidor",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
