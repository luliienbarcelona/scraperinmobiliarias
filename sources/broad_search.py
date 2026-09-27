# -*- coding: utf-8 -*-
"""
Capa 2: búsqueda amplia con Brave Search API.

Objetivo: agarrar inmobiliarias que no conocemos de antemano (como esa que
contactaste por mail para el piso de la Vila Olímpica). En vez de mantener
una lista de sitios, le preguntamos a Brave qué tiene indexado para cada
zona y revisamos los resultados nuevos.

Se usa Brave en vez de Google porque Google discontinuó la opción "buscar
en toda la web" para buscadores creados nuevos (solo la conservan los que
ya la tenían activada de antes).

Limitación real, no técnica: si un piso nunca se publicó en ninguna página
web (por ejemplo, se ofreció solo boca a boca o por mail directo sin nunca
subirlo a un sitio), esto no lo va a encontrar. Tampoco aparece hasta que
Brave lo indexe, lo cual a veces tarda días.

Requiere la secret BRAVE_API_KEY (ver README, Paso 4). Corre cada 4-6 horas,
no cada 5 min, por el límite de 2000 consultas/mes del tier gratis.
"""
import re
import requests

from config import BRAVE_API_KEY, EXCLUDE_KEYWORDS

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Portales grandes que ya cubrimos (o vamos a cubrir) con scrapers dedicados,
# no tiene sentido que la capa amplia los traiga también.
EXCLUDE_DOMAINS = [
    "idealista.com", "fotocasa.es", "habitaclia.com", "pisos.com",
    "airbnb.", "booking.com", "spotahome.com", "enalquiler.com",
    "locabarcelona.com", "housfy.com",
]

PRICE_RE = re.compile(r'([\d]{1,3}(?:[.,]\d{3})*)\s?€')
M2_RE = re.compile(r'(\d+)\s?m[²2]', re.IGNORECASE)


def _is_excluded_domain(url: str) -> bool:
    return any(dom in url for dom in EXCLUDE_DOMAINS)


def _looks_like_short_term(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in EXCLUDE_KEYWORDS)


def search_zone(zone_name: str, query: str):
    """Devuelve resultados nuevos para una zona. price/m2 pueden venir en None
    si Brave no los muestra en el snippet; en ese caso se marcan para revisar
    a mano en vez de descartarlos de una."""
    results = []

    if not BRAVE_API_KEY:
        print("[broad_search] Falta BRAVE_API_KEY, se salta esta capa.")
        return results

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {
        "q": query,
        "count": 10,
        "country": "es",
        "search_lang": "es",
    }

    try:
        resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[broad_search] Error consultando Brave para {zone_name}: {e}")
        return results

    web_results = data.get("web", {}).get("results", [])

    for item in web_results:
        url = item.get("url", "")
        if not url or _is_excluded_domain(url):
            continue

        title = item.get("title", "")
        snippet = item.get("description", "")
        full_text = f"{title} {snippet}"

        price_match = PRICE_RE.search(full_text)
        m2_match = M2_RE.search(full_text)

        price = float(price_match.group(1).replace(".", "").replace(",", ".")) if price_match else None
        m2 = float(m2_match.group(1)) if m2_match else None

        results.append({
            "zone": zone_name,
            "title": title[:200],
            "snippet": snippet[:300],
            "price": price,
            "m2": m2,
            "url": url,
            "source": "Búsqueda amplia (Brave)",
            "is_short_term": _looks_like_short_term(full_text),
            "needs_review": price is None or m2 is None,
        })

    return results
