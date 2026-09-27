# -*- coding: utf-8 -*-
"""
Utilidad compartida para los scrapers que traen resultados de toda
Barcelona en una sola página (o unas pocas, paginadas) en vez de una URL
por barrio: identifican a qué zona de las tuyas (ZONES en config.py)
pertenece cada card buscando el nombre del barrio en el texto, con o sin
tilde. Usado por Loca Barcelona, Finques March, Finques Bou, aProperties
y Finques Grau.
"""
import unicodedata

from config import ZONES

ZONE_ALIASES = {
    "Eixample": ["eixample"],
    "Sagrada Familia": ["sagrada familia", "sagrada família"],
    "Poblenou": ["poblenou", "poble nou"],
    "El Clot": ["el clot", "clot"],
    "Gracia": ["gracia", "gràcia"],
    "Barceloneta": ["barceloneta"],
    "Vila Olimpica": ["vila olimpica", "vila olímpica"],
}


def normalize(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def match_zone(text: str):
    norm = normalize(text)
    for zone in ZONES:
        for alias in ZONE_ALIASES.get(zone, [zone]):
            if normalize(alias) in norm:
                return zone
    return None


def ancestor_texts(tag, levels: int = 4):
    """Texto del tag y de sus contenedores padre, hasta `levels` niveles,
    empezando por el más cercano (el propio tag). Sirve para cuando el
    precio o los m2 no están dentro del <a> sino en un div que lo envuelve."""
    texts = []
    node = tag
    for _ in range(levels + 1):
        if node is None:
            break
        texts.append(node.get_text(" ", strip=True))
        node = getattr(node, "parent", None)
    return texts
