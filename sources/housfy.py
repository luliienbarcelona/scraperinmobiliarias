# -*- coding: utf-8 -*-
"""
Scraper para housfy.com

Cada card es un <a href="/alquiler-pisos/p/..."> cuyo texto trae todo junto:
"Piso en Calle X, Barrio, Barcelona1.537 €85 m²4 Habs.2 Baños"
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS

CARD_RE = re.compile(
    r'([\d]{1,3}(?:[.,]\d{3})*)\s?€.*?([\d]+(?:[.,]\d+)?)\s?m²\s*(\d+)\s?Habs?\.',
    re.IGNORECASE
)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def scrape_zone(zone_name: str, url: str):
    listings = []
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[housfy] Error al pedir {url}: {e}")
        return listings

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=re.compile(r"/alquiler-(pisos|casas|bajos)/p/"))

    seen_urls_this_page = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://housfy.com" + href
        if href in seen_urls_this_page:
            continue

        text = a.get_text(" ", strip=True)
        match = CARD_RE.search(text)
        if not match:
            continue

        seen_urls_this_page.add(href)
        price_str, m2_str, beds_str = match.groups()
        price = float(price_str.replace(".", "").replace(",", "."))
        m2 = float(m2_str.replace(",", "."))

        listings.append({
            "zone": zone_name,
            "title": text[:200],
            "price": price,
            "m2": m2,
            "beds": int(beds_str),
            "url": href,
            "source": "Housfy",
            "is_short_term": _looks_like_short_term(text),
        })

    return listings
