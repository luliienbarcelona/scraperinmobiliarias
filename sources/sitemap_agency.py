# -*- coding: utf-8 -*-
"""
Scraper para inmobiliarias que cargan el LISTADO con JavaScript pero
publican un sitemap.xml con la URL de cada ficha individual. La ficha
individual de estos sitios suele ser HTML server-side incluso cuando el
listado no lo es (caso confirmado: Tecnocasa), así que en vez de scrapear
el listado, recorremos el sitemap y leemos cada ficha nueva directo.

Para no tener que golpear cientos de fichas en cada corrida (algunas
inmobiliarias grandes tienen cientos de propiedades en toda España), se
guarda en un archivo separado (sitemap_seen.json, por dominio) qué URLs
de sitemap ya se evaluaron al menos una vez -se haya aceptado el piso o
no-, y en cada corrida solo se procesan las URLs que aparecen en el
sitemap y todavía no se evaluaron. La primera corrida de una inmobiliaria
nueva puede tardar más (o recortar con max_new_per_run) hasta que el
"seen" se pone al día; de ahí en adelante solo mira lo nuevo.

Entry en agencies.json necesita:
- "scraper_type": "sitemap"
- "sitemap_urls": lista de URLs (sitemap índice o ya de fichas; si es un
  índice de sitemaps .xml/.xml.gz, este módulo entra un nivel solo)
- "url_filter_pattern": regex opcional para quedarse solo con fichas de
  alquiler (ej. Tecnocasa: fichas en /alquiler/... vs /venta/...). Si no
  se da, se procesan todas las URLs del sitemap (más caro y con riesgo de
  mezclar venta).
- "max_new_per_run": tope de fichas nuevas a evaluar por corrida (default
  40), para no disparar cientos de requests en la primera corrida.
"""
import gzip
import json
import os
import re

import requests
from bs4 import BeautifulSoup

from config import REQUEST_HEADERS, EXCLUDE_KEYWORDS
from sources.zone_match import match_zone

PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)
ROOMS_RE = re.compile(r'(\d+)\s?(?:hab|dormitor|habitaci)', re.IGNORECASE)

SITEMAP_SEEN_FILE = "sitemap_seen.json"


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def load_sitemap_seen() -> dict:
    if not os.path.exists(SITEMAP_SEEN_FILE):
        return {}
    with open(SITEMAP_SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sitemap_seen(data: dict):
    with open(SITEMAP_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _fetch_sitemap_locs(url: str):
    """Descarga un sitemap (.xml o .xml.gz, con o sin Content-Encoding
    correcto) y devuelve la lista de URLs en sus tags <loc>."""
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    content = resp.content
    if url.endswith(".gz"):
        try:
            content = gzip.decompress(content)
        except OSError:
            pass  # por si requests ya lo descomprimió solo vía Content-Encoding
    # Regex en vez de BeautifulSoup(content, "xml"): ese modo necesita el
    # paquete "lxml" instalado aparte (no está en requirements.txt), y un
    # sitemap es XML simple, sacar los <loc>...</loc> con regex alcanza.
    text = content.decode("utf-8", errors="ignore")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.IGNORECASE)


def _collect_property_urls(entry: dict):
    """Recorre el/los sitemap hasta juntar todas las URLs de ficha que
    matcheen url_filter_pattern (si hay). Entra un nivel si lo que
    encuentra son más sitemaps (índice), no fichas."""
    pattern = re.compile(entry["url_filter_pattern"]) if entry.get("url_filter_pattern") else None
    to_visit = list(entry["sitemap_urls"])
    property_urls = []
    visited = set()

    while to_visit:
        sm_url = to_visit.pop()
        if sm_url in visited:
            continue
        visited.add(sm_url)
        try:
            locs = _fetch_sitemap_locs(sm_url)
        except requests.RequestException as e:
            print(f"    [ERROR] sitemap {sm_url}: {e}")
            continue

        # Si casi todo lo que hay son otros .xml/.xml.gz, es un índice:
        # hay que entrar un nivel más en vez de tratarlos como fichas.
        looks_like_index = locs and sum(
            1 for l in locs if l.endswith((".xml", ".xml.gz"))
        ) > len(locs) * 0.8
        if looks_like_index:
            to_visit.extend(locs)
            continue

        for loc in locs:
            if pattern and not pattern.search(loc):
                continue
            property_urls.append(loc)

    return property_urls


def scrape_agency(entry: dict):
    """Devuelve (listings, ok). Nunca debería levantar excepción hacia
    afuera: un fallo en el sitemap o en una ficha puntual no tiene que
    tirar abajo el resto de la corrida de Tier 2."""
    try:
        property_urls = _collect_property_urls(entry)
    except Exception as e:
        print(f"    [ERROR] no se pudo leer el sitemap de {entry['domain']}: {e}")
        return [], False

    seen_map = load_sitemap_seen()
    domain_seen = set(seen_map.get(entry["domain"], []))

    new_urls = [u for u in property_urls if u not in domain_seen]
    max_new = entry.get("max_new_per_run", 40)
    to_process = new_urls[:max_new]

    print(
        f"    sitemap: {len(property_urls)} fichas totales, "
        f"{len(new_urls)} nuevas, evaluando {len(to_process)} esta corrida"
    )

    listings = []
    for url in to_process:
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    [ERROR] ficha {url}: {e}")
            continue

        domain_seen.add(url)  # se marca como evaluada aunque no pase ningún filtro

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        zone = match_zone(text)
        if zone is None:
            continue

        price_match = PRICE_RE.search(text)
        m2_match = M2_RE.search(text)
        if not (price_match and m2_match):
            continue
        rooms_match = ROOMS_RE.search(text)

        listings.append({
            "zone": zone,
            "title": text[:200],
            "price": float(price_match.group(1).replace(".", "").replace(",", ".")),
            "m2": float(m2_match.group(1).replace(",", ".")),
            "beds": int(rooms_match.group(1)) if rooms_match else None,
            "url": url,
            "source": entry["name"],
            "is_short_term": _looks_like_short_term(text),
        })

    seen_map[entry["domain"]] = list(domain_seen)
    save_sitemap_seen(seen_map)

    return listings, True
