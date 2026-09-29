# -*- coding: utf-8 -*-
"""
Registro persistente de inmobiliarias (agencies.json), compartido por
main_tier2.py y main_discovery.py.

Cada entrada tiene los campos que pidió Luli: nombre, dominio, url de
alquiler, zonas, tier, activo, y estadísticas que se actualizan en cada
corrida (last_scrape, last_new_listing, failure_count). scraper_type
"custom" = tiene su propio archivo en sources/ (los de Tier 1 de siempre);
"generic" = lo scrapea sources/generic_agency.py a partir de un
href_pattern, sin necesidad de escribir código nuevo por cada inmobiliaria.
"""
import json
import os
from datetime import datetime, timezone

REGISTRY_FILE = "agencies.json"


def load_registry(path: str = REGISTRY_FILE) -> list:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_registry(entries: list, path: str = REGISTRY_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def mark_scraped(entry: dict, found_new: bool, ok: bool):
    entry["last_scrape"] = now_iso()
    if found_new:
        entry["last_new_listing"] = now_iso()
    if ok:
        entry["failure_count"] = 0
    else:
        entry["failure_count"] = entry.get("failure_count", 0) + 1


def domain_exists(entries: list, domain: str) -> bool:
    domain = domain.lower()
    return any(e.get("domain", "").lower() == domain for e in entries)


def add_candidate(entries: list, candidate: dict) -> bool:
    """Agrega una inmobiliaria nueva descubierta al registro, si no está ya
    (por dominio). Devuelve True si la agregó."""
    if domain_exists(entries, candidate["domain"]):
        return False
    entries.append(candidate)
    return True
