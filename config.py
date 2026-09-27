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

# Housfy quedó afuera de la Capa 1: pasó a cargar los resultados con
# JavaScript y ya no se puede leer con requests (ver notas en el README).
HOUSFY_ZONES = {}

FOTOCASA_ZONES = {
    "Eixample": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/eixample/l",
    "Sagrada Familia": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/sagrada-familia/l",
    "Poblenou": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/el-poblenou/l",
    "El Clot": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/el-clot/l",
    "Gracia": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/gracia/l",
    "Barceloneta": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/la-barceloneta/l",
    "Vila Olimpica": "https://www.fotocasa.es/en/rental/flats/barcelona-capital/la-vila-olimpica-del-poblenou/l",
}

# --- Capa 2: búsqueda amplia (Brave Search API) para agarrar inmobiliarias
# que no conocemos de antemano. Corre cada 4-6 horas (ver
# .github/workflows/scrape_broad.yml). El tier gratis de Brave permite
# 2000 consultas/mes; con 7 zonas cada 6 horas usamos ~840/mes, con margen.
# (Google Custom Search se descartó: discontinuó "buscar en toda la web"
# para buscadores nuevos, solo lo conservan los que ya lo tenían activado.)
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
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
