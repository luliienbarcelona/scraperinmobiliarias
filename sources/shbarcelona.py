# -*- coding: utf-8 -*-
"""
Scraper para shbarcelona.com

OJO: este sitio también tiene alquiler de temporada y turístico. Por eso
NO usamos la página genérica de alquiler, sino esta URL puntual que ya
viene filtrada por "Alquiler de Larga Estancia" (1 a 5-7 años):
https://shbarcelona.com/es/rent/yearly?city=3430 (3430 = Barcelona).

Citywide, ~10 resultados, sin paginación visible. Cada card tiene un link
a /es/l/<slug>--<id> con precio, m2, habitaciones y barrio como texto
dentro del mismo link o su contenedor. Filtramos por zona con
sources/zone_match.py.
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts

URL = "https://shbarcelona.com/es/rent/yearly?city=3430"

CARD_HREF_RE = re.compile(r"/es/l/[^\"']+--\d+")
PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?Habitaci', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def scrape_all_zones():
    listings = []
    try:
        resp = requests.get(URL, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[shbarcelona] Error al pedir {URL}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=CARD_HREF_RE)

    seen_urls = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://shbarcelona.com" + href
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
            "source": "ShBarcelona",
            # Esta URL ya viene filtrada a "larga estancia" desde el sitio,
            # así que no la mandamos por EXCLUDE_KEYWORDS salvo que el texto
            # de la card diga explícitamente lo contrario.
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
