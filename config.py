# -*- coding: utf-8 -*-
"""
Configuración central del scraper de departamentos en Barcelona.
Para agregar o quitar una zona, o cambiar el presupuesto, tocá solo este archivo.
"""
import os

# --- Filtros de búsqueda ---
MAX_PRICE = 1600          # euros/mes
MIN_M2 = 50                # metros cuadrados
EXCLUDE_KEYWORDS = [
    "short-term", "short term", "temporal", "temporada",
    "per night", "por noche", "vacacional", "turístico", "turistico",
    "leisure", "holiday", "vacation",
]

ZONES = [
    "Eixample", "Sagrada Familia", "Poblenou", "El Clot",
    "Gracia", "Barceloneta", "Vila Olimpica",
]

# --- Capa 1: inmobiliarias conocidas, se scrapean directo cada 5 min ---
LOCA_BARCELONA_ZONES = {
    "Eixample": "https://www.locabarcelona.com/en/rental-agency-in-barcelona/apartment-eixample-barcelona/",
    "Sagrada Familia": "https://www.locabarcelona.com/en/property-for-rent/sagrada-familia/",
    "Poblenou": "https://www.locabarcelona.com/en/property-for-rent/poblenou/",
    "El Clot": "https://www.locabarcelona.com/en/property-for-rent/el-clot/",
    "Gracia": "https://www.locabarcelona.com/en/property-for-rent/gracia/",
    "Barceloneta": "https://www.locabarcelona.com/en/property-for-rent/barceloneta/",
    "Vila Olimpica": "https://www.locabarcelona.com/en/property-for-rent/vila-olimpica-del-poblenou/",
}

HOUSFY_ZONES = {
    "Eixample": "https://housfy.com/alquiler-inmuebles/barcelona/barcelona/eixample",
    "Poblenou": "https://housfy.com/alquiler-inmuebles/barcelona/barcelona/sant-marti/el-poblenou",
    "Gracia": "https://housfy.com/alquiler-inmuebles/barcelona/barcelona/gracia",
    "Barceloneta": "https://housfy.com/alquiler-inmuebles/barcelona/barcelona/ciutat-vella/la-barceloneta",
}

# --- Capa 2: búsqueda amplia (Google Programmable Search) para agarrar
# inmobiliarias que no conocemos de antemano. Corre cada 1-2 horas (ver
# .github/workflows/scrape_broad.yml) porque el tier gratis de Google
# permite 100 consultas/día, y una por zona cada 5 min se pasaría rápido.
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")
BROAD_SEARCH_QUERIES = {
    zone: f"alquiler piso {zone} Barcelona larga estancia" for zone in ZONES
}

# --- Telegram (se completan como GitHub Secrets, no hardcodear acá) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Archivos donde se guardan los anuncios ya vistos (para no repetir notificaciones) ---
SEEN_FILE = "seen_listings.json"
SEEN_FILE_BROAD = "seen_broad.json"

# --- Headers para simular un navegador real ---
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
