# -*- coding: utf-8 -*-
"""
Scraper para www.locabarcelona.com

Cada card de propiedad en la página de listado es un <a> que envuelve un texto
tipo "Available 01.12.2026 1.429€ Título del piso Barrio . Calle Property ID XXXXX".
Los datos de m2/habitaciones vienen en el contenedor que sigue a ese link.
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS

PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m2', re.IGNORECASE)
BED_RE = re.compile(r'(\d+)\s?Bedroom', re.IGNORECASE)
REF_RE = re.compile(r'Property ID\s+(\S+)', re.IGNORECASE)


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


def scrape_zone(zone_name: str, url: str):
    listings = []
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[loca_barcelona] Error al pedir {url}: {e}")
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
        ref_match = REF_RE.search(text)
        if not price_match or not ref_match:
            continue

        seen_urls_this_page.add(href)
        price = float(price_match.group(1).replace(".", "").replace(",", "."))
        m2, beds = _find_m2_and_beds(a)

        listings.append({
            "zone": zone_name,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": beds,
            "url": href,
            "source": "Loca Barcelona",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
