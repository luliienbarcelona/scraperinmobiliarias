# -*- coding: utf-8 -*-
"""
Scraper para aproperties.es

~73 resultados en total para Barcelona, paginados de a ~24
(?p=2, ?p=3, ...). Cada card dice algo como "Piso en alquiler en Gran Via
Corts Catalanes (Eixample Esquerra)...Superficie 130 m2 Dormitorios 3
Baños 2 2.401,85 €". Filtramos por zona con sources/zone_match.py.
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts

BASE_URL = "https://www.aproperties.es/pisos-alquiler-barcelona"
MAX_PAGES = 5  # corta antes si una página no trae anuncios nuevos

CARD_HREF_RE = re.compile(r"/barcelona/[^\"']*-en-alquiler-en-[^\"']+")
PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s?€')
M2_RE = re.compile(r'Superficie\s+(\d+(?:[.,]\d+)?)\s?m2', re.IGNORECASE)
ROOMS_RE = re.compile(r'Dormitorios\s+(\d+)', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def _scrape_page(url: str):
    listings = []
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[aproperties] Error al pedir {url}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=CARD_HREF_RE)

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.aproperties.es" + href

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

        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        m2 = float(m2_match.group(1).replace(",", "."))

        listings.append({
            "zone": zone,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": int(rooms_match.group(1)) if rooms_match else None,
            "url": href,
            "source": "aProperties",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings, len(anchors)


def scrape_all_zones():
    all_listings = []
    seen_urls = set()

    for page in range(1, MAX_PAGES + 1):
        url = BASE_URL if page == 1 else f"{BASE_URL}?p={page}"
        page_listings, anchor_count = _scrape_page(url)
        if anchor_count == 0:
            break  # ya no hay más cards, se acabaron las páginas
        for listing in page_listings:
            if listing["url"] in seen_urls:
                continue
            seen_urls.add(listing["url"])
            all_listings.append(listing)
        # anchor_count > 0 pero ninguno matcheó tu zona: igual seguimos a la
        # próxima página, puede que ahí sí haya de tus barrios.

    return all_listings
