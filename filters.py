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
from config import (
    MAX_PRICE, MIN_M2, EXCLUDE_KEYWORDS,
    PETS_REJECT_KEYWORDS, PETS_OK_KEYWORDS, LONG_TERM_HINTS,
)


def _text_of(listing: dict) -> str:
    return " ".join(str(listing.get(k, "")) for k in ("title", "snippet")).lower()


def enrich_listing(listing: dict) -> dict:
    """Agrega flags al listing para el mensaje de Telegram. No filtra nada,
    solo anota lo que se pudo inferir del texto disponible."""
    text = _text_of(listing)

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
    if listing["pets_rejected"]:
        return False

    price = listing.get("price")
    if price is not None and price > MAX_PRICE:
        return False

    m2 = listing.get("m2")
    if m2 is not None and m2 < MIN_M2:
        return False

    return True
