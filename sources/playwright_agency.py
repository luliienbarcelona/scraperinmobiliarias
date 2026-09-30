# -*- coding: utf-8 -*-
"""
Scraper para inmobiliarias cuyo LISTADO carga con JavaScript y que no
tienen (o no confirmamos) un sitemap con fichas server-side (ver
sources/sitemap_agency.py, que es más liviano y hay que probar primero).
Esto es el último recurso: abre un navegador headless de verdad
(Playwright + Chromium), espera a que cargue, y recién ahí lee el HTML
final, con el mismo patrón de "card" que usa generic_agency.py (ancestor
con precio+m2 juntos).

Mucho más lento y pesado que generic_agency/sitemap_agency (por eso corre
en su propio workflow, cada 30 min, no cada 15 -ver
.github/workflows/scrape_tier2_js.yml- y por eso requirements-js.txt y el
paso "playwright install chromium" están separados de los del resto, para
no pagar ese costo en las corridas rápidas que no lo necesitan).

Entry en agencies.json necesita lo mismo que un "generic": rental_url,
href_pattern (opcional, usa DEFAULT_HREF_RE de generic_agency si no hay),
domain_prefix (opcional). No soporta paginación por ahora (max_pages se
ignora): si una inmobiliaria de esta lista tiene mucho volumen y hace
falta paginar, se agrega soporte de "click en Siguiente" más adelante.
"""
import re

from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts
from sources.generic_agency import DEFAULT_HREF_RE

PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?(?:hab|dormitor|habitaci)', re.IGNORECASE)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def render_html(url: str, wait_ms: int = 4000) -> str:
    """Abre la URL en Chromium headless, espera a que la red se calme (o
    wait_ms como tope) y devuelve el HTML final ya renderizado. Función
    separada para que discover_agencies.py la pueda reusar en el chequeo
    de candidatos nuevos sin duplicar la lógica de Playwright."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=REQUEST_HEADERS.get("User-Agent"))
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=wait_ms)
            except Exception:
                pass  # algunos sitios nunca quedan "idle" (polling, ads, etc.), no pasa nada
            html = page.content()
        finally:
            browser.close()
    return html


def _parse_cards(html: str, href_pattern, domain_prefix: str):
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a", href=href_pattern)

    listings = []
    seen_urls = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = domain_prefix.rstrip("/") + href
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
        listings.append({
            "zone": zone,
            "title": text[:200],
            "price": float(price_match.group(1).replace(".", "").replace(",", ".")),
            "m2": float(m2_match.group(1).replace(",", ".")),
            "beds": int(rooms_match.group(1)) if rooms_match else None,
            "url": href,
            "source": None,
            "is_short_term": _looks_like_short_term(text),
        })

    return listings


def scrape_agency(entry: dict):
    """Devuelve (listings, ok). No pagina (ver docstring del módulo)."""
    href_pattern = re.compile(entry["href_pattern"]) if entry.get("href_pattern") else DEFAULT_HREF_RE
    domain_prefix = entry.get("domain_prefix") or ("https://" + entry["domain"])

    try:
        html = render_html(entry["rental_url"])
    except Exception as e:
        print(f"    [ERROR] Playwright en {entry['rental_url']}: {e}")
        return [], False

    listings = _parse_cards(html, href_pattern, domain_prefix)
    for listing in listings:
        listing["source"] = entry["name"]

    return listings, True
