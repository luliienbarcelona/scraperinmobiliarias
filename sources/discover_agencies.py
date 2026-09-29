# -*- coding: utf-8 -*-
"""
Discovery: busca inmobiliarias NUEVAS (no pisos sueltos) con Brave Search,
zona por zona. A cada dominio nuevo le hace un chequeo automático rápido
(¿tiene precio+m2 en el HTML crudo? ¿menciona alguna de tus zonas?) y si
pasa, se suma solo a agencies.json en Tier 2, activa, para que
main_tier2.py la empiece a monitorear con el scraper genérico. Si no pasa,
igual queda anotada (inactiva) para no re-evaluar el mismo dominio en cada
corrida.

Esto reemplaza al broad_search.py viejo, que buscaba pisos sueltos por
Google/Brave (señal débil, ver notas en el README). Ahora Brave se usa
para encontrar SITIOS, no anuncios.
"""
import re
import requests
from bs4 import BeautifulSoup

from config import BRAVE_API_KEY, REQUEST_HEADERS, ZONES
from sources.zone_match import match_zone

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

DISCOVERY_QUERY_TEMPLATES = [
    "inmobiliaria {zone} Barcelona alquiler",
    "administració finques {zone} lloguer",
]

# Portales/agregadores y sitios ya evaluados a mano que no queremos que
# discovery proponga de nuevo (duplicaría lo que ya está en agencies.json,
# o son portales, no inmobiliarias individuales).
KNOWN_NON_CANDIDATES = [
    "idealista.com", "fotocasa.es", "habitaclia.com", "pisos.com",
    "yaencontre.com", "enalquiler.com", "milanuncios.com", "airbnb.",
    "booking.com", "spotahome.com", "nuroa.es", "trovit.es",
    "paginasamarillas.es", "spainhouses.net", "estatenearme.com",
    "kelify.com", "tucasa.com", "lucasfox.com", "engelvoelkers.com",
    "wikipedia.org", "facebook.com", "instagram.com", "youtube.com",
    "linkedin.com", "x.com", "tiktok.com",
]

PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)


def _domain_of(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1).lower() if m else url.lower()


def search_candidate_domains():
    """Devuelve una lista de (domain, url) únicos por dominio, recorriendo
    todas las zonas. No filtra por lo que ya está en el registro (eso lo
    hace main_discovery.py, que sí conoce agencies.json)."""
    seen_domains = set()
    candidates = []

    if not BRAVE_API_KEY:
        print("[discover_agencies] Falta BRAVE_API_KEY, se salta.")
        return candidates

    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}

    for zone in ZONES:
        for template in DISCOVERY_QUERY_TEMPLATES:
            query = template.format(zone=zone)
            params = {"q": query, "count": 10, "country": "es", "search_lang": "es"}
            try:
                resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                print(f"  [ERROR] Brave para '{query}': {e}")
                continue

            for item in data.get("web", {}).get("results", []):
                url = item.get("url", "")
                domain = _domain_of(url)
                if not domain or domain in seen_domains:
                    continue
                if any(known in domain for known in KNOWN_NON_CANDIDATES):
                    continue
                seen_domains.add(domain)
                candidates.append((domain, url))

    return candidates


def quick_quality_check(url: str):
    """Chequeo automático rápido, no perfecto: ¿la página tiene indicios de
    precio+m2 en HTML crudo, y menciona alguna de tus zonas? Sirve para no
    sumar al registro sitios que son puro JS, o que no tienen nada que ver
    con tu búsqueda. Devuelve (ok: bool, motivo: str)."""
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"no responde ({e})"

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    has_price = bool(PRICE_RE.search(text))
    has_m2 = bool(M2_RE.search(text))
    zone_hit = match_zone(text)

    if not (has_price and has_m2):
        return False, "no se ve precio+m2 en el HTML crudo (puede ser JS, o no tiene listado en esta página)"
    if zone_hit is None:
        return False, "no menciona ninguna de tus zonas en esta página"

    return True, f"tiene precio+m2 visibles y menciona {zone_hit}"
