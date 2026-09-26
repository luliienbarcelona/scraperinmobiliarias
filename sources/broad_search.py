# -*- coding: utf-8 -*-
"""
Capa 2: búsqueda amplia con Google Programmable Search Engine.

Objetivo: agarrar inmobiliarias que no conocemos de antemano (como esa que
contactaste por mail para el piso de la Vila Olímpica). En vez de mantener
una lista de sitios, le preguntamos a Google qué tiene indexado para cada
zona y revisamos los resultados nuevos.

Limitación real, no técnica: si un piso nunca se publicó en ninguna página
web (por ejemplo, se ofreció solo boca a boca o por mail directo sin nunca
subirlo a un sitio), esto no lo va a encontrar. Tampoco aparece hasta que
Google lo indexe, lo cual a veces tarda días.

Requiere las secrets GOOGLE_API_KEY y GOOGLE_CSE_ID (ver README, Paso 5).
Corre cada 1-2 horas, no cada 5 min, por el límite de 100 consultas/día
del tier gratis de Google.
"""
import re
import requests

from config import GOOGLE_API_KEY, GOOGLE_CSE_ID, EXCLUDE_KEYWORDS

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

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
    si Google no los muestra en el snippet; en ese caso se marcan para revisar
    a mano en vez de descartarlos de una."""
    results = []

    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("[broad_search] Falta GOOGLE_API_KEY o GOOGLE_CSE_ID, se salta esta capa.")
        return results

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 10,
        "gl": "es",
        "lr": "lang_es",
    }

    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[broad_search] Error consultando Google para {zone_name}: {e}")
        return results

    for item in data.get("items", []):
        url = item.get("link", "")
        if not url or _is_excluded_domain(url):
            continue

        title = item.get("title", "")
        snippet = item.get("snippet", "")
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
            "source": "Búsqueda amplia (Google)",
            "is_short_term": _looks_like_short_term(full_text),
            "needs_review": price is None or m2 is None,
        })

    return results
