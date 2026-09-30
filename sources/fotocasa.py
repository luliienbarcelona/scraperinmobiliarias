# -*- coding: utf-8 -*-
"""
Scraper para fotocasa.es (reemplaza a Housfy, que pasó a cargar sus
resultados con JavaScript y ya no se puede leer con requests).

Cada card es un <a href="/en/rental/home/barcelona/.../<ID>/d"> cuyo texto
trae todo junto, por ejemplo:
"2.911 € /month Some Agency Flat of 159 m² in La Nova Esquerra de l'Eixample
 ... 5 rooms 3 bath 159 m² 6th floor Elevator Parking ... 86 days ago"
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS

CARD_HREF_RE = re.compile(r"/rental/home/[^\"']+/\d+/d")
PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m²', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?rooms?', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def scrape_zone(zone_name: str, url: str):
    listings = []
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[fotocasa] Error al pedir {url}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=CARD_HREF_RE)

    seen_urls_this_page = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.fotocasa.es" + href
        if href in seen_urls_this_page:
            continue

        text = a.get_text(" ", strip=True)
        price_match = PRICE_RE.search(text)
        m2_match = M2_RE.search(text)
        if not price_match or not m2_match:
            # Sin precio o sin m2 no podemos filtrar, se descarta esta card
            continue

        rooms_match = ROOMS_RE.search(text)

        seen_urls_this_page.add(href)
        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        m2 = float(m2_match.group(1).replace(",", "."))

        listings.append({
            "zone": zone_name,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": int(rooms_match.group(1)) if rooms_match else None,
            "url": href,
            "source": "Fotocasa",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
