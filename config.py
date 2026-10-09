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
    # catalan
    "turístic", "turistic", "per nit", "vacances", "estada curta", "curta durada",
]

# Frases que indican explícitamente que NO se aceptan mascotas. Si un anuncio
# no dice nada de mascotas, no se rechaza (ver filters.py: dato faltante
# nunca es motivo de rechazo).
PETS_REJECT_KEYWORDS = [
    "no se admiten mascotas", "no admite mascotas", "no mascotas",
    "sin mascotas", "prohibido mascotas", "no pets", "pets not allowed",
    "no animales", "sense mascotes", "no es permeten mascotes",
    "not allowed pets",
    # catalan (el apostrofo tipografico se normaliza en filters.py)
    "no s'admeten mascotes", "no s'accepten mascotes", "no admet mascotes",
    "no mascotes", "prohibit mascotes", "no animals", "no s'admeten animals",
]

# Si dice explícitamente que sí se aceptan, lo mostramos en el mensaje en
# vez de "no especificado" (pero esto nunca se usa para filtrar).
PETS_OK_KEYWORDS = [
    "se admiten mascotas", "mascotas permitidas", "pet friendly",
    "pets allowed", "admite mascotas", "es permeten mascotes",
    "s'admeten mascotes", "s'accepten mascotes", "mascotes permeses",
    "admet mascotes", "accepta mascotes",
]

# Frases que indican que el alquiler es de larga estancia (uso para marcar
# el tipo de alquiler como conocido en vez de "desconocido" en el mensaje
# de Telegram; no se usa para filtrar, EXCLUDE_KEYWORDS ya se encarga de
# rechazar lo que es claramente corto plazo).
LONG_TERM_HINTS = [
    "larga estancia", "larga duracion", "larga duración",
    "vivienda habitual", "long term", "long-term", "arrendamiento habitual",
    "residencial", "uso residencial",
    "llarga estada", "llarga durada", "habitatge habitual", "ús residencial",
    "us residencial", "lloguer d'habitatge",
]

# Luli busca PISOS para vivir, no locales/oficinas/garajes/trasteros que a
# veces se cuelan porque comparten sitio web con las viviendas. Si el texto
# dice explícitamente que es uno de estos, se rechaza (mismo criterio que
# EXCLUDE_KEYWORDS: solo se descarta por señal explícita).
NON_HOUSING_KEYWORDS = [
    "local comercial", "local en alquiler", "local para alquilar",
    "alquiler de local", "alquiler local",
    "oficina en alquiler", "alquiler de oficina", "alquiler oficina",
    "nave industrial", "alquiler de nave", "alquiler nave",
    "garaje en alquiler", "plaza de garaje", "alquiler de garaje",
    "alquiler garaje", "parking en alquiler",
    "trastero en alquiler", "alquiler de trastero", "alquiler trastero",
    "plaza de aparcamiento", "plaza de parking",
    # Catalan
    "local en lloguer", "lloguer de local", "lloguer local",
    "oficina en lloguer", "oficines en lloguer", "lloguer d'oficina",
    "lloguer d´oficina", "lloguer oficina", "despatx en lloguer",
    "lloguer de despatx", "nau industrial", "lloguer de nau",
    "garatge en lloguer", "lloguer de garatge", "lloguer garatge",
    "plaça de garatge", "plaça de pàrquing", "plaça d'aparcament",
    "pàrquing en lloguer", "parking en lloguer", "traster en lloguer",
    "lloguer de traster", "lloguer traster",
    # OJO: palabras sueltas como "garaje", "garatge" o "trastero" se SACARON
    # (2026-10-09): rechazaban cualquier piso cuya tarjeta dijera "con plaza
    # de garaje". Los garajes/trasteros reales los atrapan las frases de
    # arriba, el tipo en la URL y el titulo que arranca con el tipo (ver
    # filters.py).
]

ZONES = [
    "Eixample", "Sagrada Familia", "Poblenou", "El Clot",
    "Gracia", "Barceloneta", "Vila Olimpica",
]

# --- Capa 1: inmobiliarias conocidas, se scrapean directo cada 5 min ---
# Loca Barcelona ya no usa una URL por barrio: esas páginas mezclaban corto
# y largo plazo. Ahora sources/loca_barcelona.py pide una sola URL (la de
# long-term rental) y separa por zona buscando el nombre del barrio en el
# texto de cada card.

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
SEEN_FILE = "seen_listings.json"          # Tier 1 (cada 5 min)
SEEN_FILE_TIER2 = "seen_tier2.json"       # Tier 2 (cada ~15 min, registro en agencies.json)
SEEN_FILE_BROAD = "seen_broad.json"       # ya no se usa (broad search viejo); queda por compatibilidad

# --- Headers para simular un navegador real ---
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
