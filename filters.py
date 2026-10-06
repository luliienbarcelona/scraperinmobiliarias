# -*- coding: utf-8 -*-
"""
Filtro compartido por los tres scrapers (Tier 1, Tier 2, discovery).

Filosofía (pedida por Luli): SPEED + RECALL por encima de la clasificación
perfecta. Un dato faltante (precio, m2, tipo de alquiler) NUNCA es motivo
de rechazo por sí solo. Solo se rechaza cuando hay una señal EXPLÍCITA de
que el piso no sirve: precio confirmado por encima del máximo, m2
confirmados por debajo del mínimo, o texto que dice claramente "temporada"
o "no se admiten mascotas".

Todo lo demás se manda a Telegram, marcado como "desconocido" en vez de
descartado en silencio.
"""
import re
from urllib.parse import urlparse

from config import (
    MAX_PRICE, MIN_M2, EXCLUDE_KEYWORDS,
    PETS_REJECT_KEYWORDS, PETS_OK_KEYWORDS, LONG_TERM_HINTS,
    NON_HOUSING_KEYWORDS,
)


# Tipos de inmueble que NO son vivienda. Se buscan en la URL porque varios
# sitios ponen el tipo ahi y no en el texto de la tarjeta (ej. Finques
# Teixidor: ".../eixample-dret-diputacio-despacho.htm"). Cuidado con los
# falsos positivos: un piso "con garaje" o "con parking" SI es vivienda, asi
# que el tipo solo cuenta si es un directorio entero de la URL, si es lo
# PRIMERO del slug ("garaje-en-alquiler-en-...") o lo ULTIMO ("...-local").
_NON_HOUSING_TYPES = (
    "oficina", "oficinas", "despacho", "despachos", "local", "locales",
    "local-comercial", "locales-comerciales", "garaje", "garajes", "garatge",
    "garatges", "parking", "parkings", "aparcamiento", "aparcamientos",
    "trastero", "trasteros", "traster", "trasters", "nave", "naves",
    "nave-industrial", "almacen", "almacenes", "coworking",
    "boxplaza-de-garaje", "plaza-de-garaje", "plaza-de-parking",
)


def _url_is_non_housing(url) -> bool:
    if not url:
        return False
    path = urlparse(str(url)).path.lower()
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return False
    *dirs, last = segments
    if any(seg in _NON_HOUSING_TYPES for seg in dirs):
        return True
    slug = re.sub(r"\.(html?|php|cfm|aspx?)$", "", last)
    for t in _NON_HOUSING_TYPES:
        if slug == t or slug.startswith(t + "-") or slug.endswith("-" + t):
            return True
    return False


_NON_HOUSING_TITLE_STARTS = (
    "oficina", "despacho", "local ", "local-", "locales", "garaje", "garatge",
    "parking", "trastero", "traster", "nave ", "nave-", "almacen", "almacén",
    "coworking", "plaza de garaje", "plaza de parking", "plaza de aparcamiento",
)


def _title_starts_non_housing(title) -> bool:
    """El tipo de inmueble suele ir PRIMERO en el titulo ("Oficina en ...").
    Solo cuenta al principio: "Piso con despacho" o "Piso con garaje" son
    viviendas y no deben rechazarse."""
    t = re.sub(r"^[^a-zA-ZÀ-ÿ]+", "", str(title or "")).lower()
    return t.startswith(_NON_HOUSING_TITLE_STARTS)


def _text_of(listing: dict) -> str:
    return " ".join(str(listing.get(k, "")) for k in ("title", "snippet")).lower()


def enrich_listing(listing: dict) -> dict:
    """Agrega flags al listing para el mensaje de Telegram. No filtra nada,
    solo anota lo que se pudo inferir del texto disponible."""
    text = _text_of(listing)

    listing["is_non_housing"] = (
        any(kw in text for kw in NON_HOUSING_KEYWORDS)
        or _url_is_non_housing(listing.get("url"))
        or _title_starts_non_housing(listing.get("title"))
    )

    listing["pets_rejected"] = any(kw in text for kw in PETS_REJECT_KEYWORDS)
    if listing["pets_rejected"]:
        listing["pets_status"] = "rejected"
    elif any(kw in text for kw in PETS_OK_KEYWORDS):
        listing["pets_status"] = "allowed"
    else:
        listing["pets_status"] = "unspecified"

    if listing.get("is_short_term"):
        listing["rental_type"] = "short_term"
    elif any(kw in text for kw in LONG_TERM_HINTS):
        listing["rental_type"] = "long_term"
    else:
        listing["rental_type"] = "unknown"

    return listing


def passes_filters(listing: dict) -> bool:
    """True si el piso se puede notificar. Solo rechaza por señal explícita,
    nunca por dato faltante."""
    enrich_listing(listing)

    if listing.get("is_short_term"):
        return False
    if listing["is_non_housing"]:
        return False
    if listing["pets_rejected"]:
        return False

    price = listing.get("price")
    if price is not None and price > MAX_PRICE:
        return False

    m2 = listing.get("m2")
    if m2 is not None and m2 < MIN_M2:
        return False

    return True
