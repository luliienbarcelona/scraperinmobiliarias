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
    "inmobiliaria {zone} Barcelona alquiler pisos",
    "pisos en alquiler {zone} Barcelona inmobiliaria web",
    "administrador de fincas alquiler pisos {zone} Barcelona web propia",
]
# OJO: "administració finques X lloguer" (a secas) se sacó: en la práctica
# trae sobre todo administradores de comunidades de vecinos, que no
# publican anuncios de alquiler con precio en su web (gestionan edificios,
# no inventario para alquilar). La versión con "alquiler pisos ... web
# propia" trae mejores resultados, así encontramos Finques Teixidor y
# borsalloguers.com a mano.

# Portales/agregadores y sitios ya evaluados a mano que no queremos que
# discovery proponga de nuevo (duplicaría lo que ya está en agencies.json,
# o son portales, no inmobiliarias individuales).
KNOWN_NON_CANDIDATES = [
    "idealista.com", "fotocasa.es", "habitaclia.com", "pisos.com",
    "yaencontre.com", "enalquiler.com", "milanuncios.com", "airbnb.",
    "booking.com", "spotahome.com", "nuroa.es", "trovit.es",
    "paginasamarillas.es", "spainhouses.net", "estatenearme.com",
    "kelify.com", "tucasa.com", "lucasfox.com", "lucasfox.es",
    "engelvoelkers.com", "wikipedia.org", "facebook.com", "instagram.com",
    "youtube.com", "linkedin.com", "x.com", "tiktok.com",
    # Confirmados a mano como de lujo o mal fit (auditoría 2026-09-29,
    # se colaron en la primera corrida de discovery porque el chequeo
    # automático todavía no filtraba por precio plausible):
    "bcn-advisors.com", "carolinamarti.es", "immobarcelo.es",
    "withfor.com", "diagonal111.com",
    # Confirmados a mano el 2026-09-30: urbanegroup.es es boutique de lujo
    # (solo venta, 400k-3.9M€), y api.cat solo devolvía garajes/locales,
    # nada de pisos (feedback directo de Luli).
    "urbanegroup.es", "api.cat",
]

PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)

# Techo para el chequeo automático (más laxo que MAX_PRICE de config.py,
# que es 1600): alcanza con que HAYA algún precio dentro de un rango
# razonable en la página, no que sea exactamente tu presupuesto. Esto es
# lo que faltaba: antes solo chequeaba "¿hay un precio?", sin mirar si el
# precio era de vivienda barata o de un ático de lujo.
DISCOVERY_PRICE_CEILING = 2200


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


def _check_one_page(url: str):
    """Devuelve (ok, motivo) para UNA página puntual."""
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"no responde ({e})"

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    m2_hit = M2_RE.search(text)
    zone_hit = match_zone(text)

    if not m2_hit:
        return False, "no se ve ningún m² en el HTML crudo (puede ser JS, o no tiene listado en esta página)"
    if zone_hit is None:
        return False, "no menciona ninguna de tus zonas en esta página"

    prices = [
        float(p.replace(".", "").replace(",", "."))
        for p in PRICE_RE.findall(text)
    ]
    plausible = [p for p in prices if p <= DISCOVERY_PRICE_CEILING]
    if not plausible:
        if prices:
            return False, f"los precios que aparecen son todos altos (mínimo encontrado: {min(prices):.0f}€), parece de lujo o venta"
        return False, "no se ve ningún precio en el HTML crudo"

    return True, f"tiene precio (ej. {min(plausible):.0f}€) y m² visibles, menciona {zone_hit}"


def quick_quality_check(url: str):
    """Chequeo automático, no perfecto: ¿la página tiene un precio
    razonable (no de lujo) + m² en HTML crudo, y menciona alguna de tus
    zonas? Sirve para no sumar al registro sitios que son puro JS, que
    solo tienen inventario de lujo, o que no tienen nada que ver con tu
    búsqueda.

    Prueba primero la URL puntual que dio Brave (puede ser una página
    interior sin listado) y, si falla, prueba la home del dominio como
    respaldo, porque a veces el listado real está ahí y no en la página
    que indexó el buscador. Devuelve (ok: bool, motivo: str)."""
    ok, reason = _check_one_page(url)
    if ok:
        return ok, reason

    domain = _domain_of(url)
    home_url = f"https://{domain}/"
    if home_url.rstrip("/") == url.rstrip("/"):
        return ok, reason  # ya probamos la home, no repetir

    ok_home, reason_home = _check_one_page(home_url)
    if ok_home:
        return ok_home, f"(vía home) {reason_home}"

    return False, f"{reason} / en la home tampoco: {reason_home}"
