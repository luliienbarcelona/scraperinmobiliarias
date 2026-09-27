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
