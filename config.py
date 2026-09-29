# -*- coding: utf-8 -*-
"""
Configuración central del scraper de departamentos en Barcelona.
Para agregar o quitar una zona, o cambiar el presupuesto, tocá solo este archivo.
"""
import os

# --- Filtros de búsqueda ---
MAX_PRICE = 1600
MIN_M2 = 50
EXCLUDE_KEYWORDS = [
    "short-term", "short term", "temporal", "temporada",
    "per night", "por noche", "vacacional", "turístico", "turistico",
    "leisure", "holiday", "vacation",
]

ZONES = [
    "Eixample", "Sagrada Familia", "Poblenou", "El Clot",
    "Gracia", "Barceloneta", "Vila Olimpica",
]

HOUSFY_ZONES = {}

FOTOCASA_ZONES = {
    "Eixample": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/eixample/l",
    "Sagrada Familia": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/sagrada-familia/l",
    "Poblenou": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/el-poblenou/l",
    "El Clot": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/el-clot/l",
    "Gracia": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/gracia/l",
    "Barceloneta": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/la-barceloneta/l",
    "Vila Olimpica": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/la-vila-olimpica-del-poblenou/l"
}

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BROAD_SEARCH_QUERIES = {
    zone: f"alquiler piso {zone} Barcelona larga estancia" for zone in ZONES
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SEEN_FILE = "seen_listings.json"
SEEN_FILE_BROAD = "seen_broad.json"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
