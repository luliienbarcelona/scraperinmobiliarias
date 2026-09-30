# -*- coding: utf-8 -*-
"""
Scraper genérico para Tier 2: en vez de escribir un archivo Python por cada
inmobiliaria nueva (como los de Tier 1), esto scrapea cualquier sitio a
partir de su entrada en agencies.json (rental_url + href_pattern, y
opcionalmente paginación).

Mismo patrón que ya usan aproperties.py y selekta.py: busca <a> que
matcheen el patrón del link a la ficha, mira el texto del contenedor padre
(ancestor_texts), saca precio/m2/habitaciones con regex, y filtra por zona
con sources/zone_match.py.

No todas las inmobiliarias van a andar con esto (algunas cargan todo con
JavaScript, o tienen un HTML sin patrón claro). Cuando una entrada falla
seguido queda registrado en agencies.json (failure_count), para poder
desactivarla más adelante sin perder el resto.
"""
import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone, ancestor_texts

PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?(?:hab|dormitor|habitaci)', re.IGNORECASE)

# Para inmobiliarias descubiertas automáticamente (discovery), donde todavía
# no le escribimos un href_pattern a mano: acepta cualquier link que no sea
# obviamente basura (nav, contacto, legal). Como igual exigimos precio+m2
# juntos en el texto del contenedor, esto filtra bastante solo.
DEFAULT_HREF_RE = re.compile(
    r'^(?!.*(mailto:|tel:|javascript:|^#|/blog|/contacto|/aviso-legal|'
    r'/politica|/cookies|/nosotros|/quienes-somos|/quienes somos|/legal|'
    r'/privacidad|/aviso|#)).+$',
    re.IGNORECASE,
)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def _scrape_page(url: str, href_pattern, domain_prefix: str):
    """Devuelve (listings, anchor_count, ok). ok=False si la request falló
    (para distinguir de "0 resultados porque se acabaron las páginas")."""
    listings = []
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    [ERROR] {url}: {e}")
        return listings, 0, False

    soup = BeautifulSoup(resp.text, "html.parser")
    anchors = soup.find_all("a", href=href_pattern)

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
            "source": None,  # lo completa scrape_agency con el nombre del registro
            "is_short_term": _looks_like_short_term(text),
        })

    return listings, len(anchors), True


def scrape_agency(entry: dict):
    """entry viene de agencies.json (scraper_type == "generic"). Necesita
    "rental_url" y "href_pattern" (regex, como string). Opcional:
    "domain_prefix" (default: https://<domain>), "max_pages" (default 1),
    "page_template" (ej: "{base}?p={page}", para paginar).
    Devuelve (listings, ok)."""
    href_pattern = re.compile(entry["href_pattern"]) if entry.get("href_pattern") else DEFAULT_HREF_RE
    base_url = entry["rental_url"]
    domain_prefix = entry.get("domain_prefix") or ("https://" + entry["domain"])
    max_pages = entry.get("max_pages", 1)
    page_template = entry.get("page_template")

    all_listings = []
    seen_urls = set()
    any_ok = False

    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        elif page_template:
            url = page_template.format(base=base_url, page=page)
        else:
            break

        page_listings, anchor_count, ok = _scrape_page(url, href_pattern, domain_prefix)
        any_ok = any_ok or ok
        if anchor_count == 0:
            break
        for listing in page_listings:
            if listing["url"] in seen_urls:
                continue
            seen_urls.add(listing["url"])
            listing["source"] = entry["name"]
            all_listings.append(listing)

    return all_listings, any_ok
