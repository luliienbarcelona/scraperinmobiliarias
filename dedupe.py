# -*- coding: utf-8 -*-
"""
Guarda qué anuncios ya se notificaron, para no mandar el mismo dos veces,
y ahora también su precio/m2 la última vez que se vio, para poder avisar
si baja el precio (pedido de Luli: no solo "nuevo", también "cambió").

Los archivos seen_*.json se commitean de vuelta al repo en cada corrida de
GitHub Actions (ver .github/workflows/).

Formato: {"<url o fingerprint>": {"price": 1450.0, "m2": 60.0}, ...}
"""
import hashlib
import json
import os


def _fingerprint(listing: dict) -> str:
    """Para el caso raro de que una fuente no traiga URL propia por anuncio:
    arma un identificador estable con zona+precio+m2+título."""
    base = "|".join([
        str(listing.get("zone", "")),
        str(listing.get("price", "")),
        str(listing.get("m2", "")),
        str(listing.get("title", ""))[:80],
    ])
    return "fp:" + hashlib.sha1(base.encode("utf-8")).hexdigest()


def listing_key(listing: dict) -> str:
    url = listing.get("url")
    return url if url else _fingerprint(listing)


def load_seen(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    if isinstance(data, list):
        # Formato viejo (antes de agregar detección de cambio de precio):
        # una lista plana de URLs. La migramos sin precio guardado, así no
        # se pierde el historial de "ya visto" al actualizar este archivo.
        return {url: {"price": None, "m2": None} for url in data}
    return data


def save_seen(path: str, seen: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2, sort_keys=True)


def check_listing(seen: dict, listing: dict):
    """Devuelve (status, key). status es uno de:
    - "new": no lo habíamos visto
    - "price_drop": ya lo conocíamos y bajó de precio
    - "seen": ya lo conocíamos, sin cambios relevantes
    """
    key = listing_key(listing)

    if key not in seen:
        return "new", key

    prev_price = seen[key].get("price")
    price = listing.get("price")
    if price is not None and prev_price is not None and price < prev_price:
        return "price_drop", key

    return "seen", key


def remember(seen: dict, listing: dict, key: str):
    seen[key] = {"price": listing.get("price"), "m2": listing.get("m2")}
