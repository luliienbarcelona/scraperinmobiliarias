# -*- coding: utf-8 -*-
"""
Guarda qué anuncios ya se notificaron, para no mandar el mismo dos veces.
Los archivos seen_*.json se commitean de vuelta al repo en cada corrida
de GitHub Actions (ver .github/workflows/).
"""
import json
import os


def load_seen(path: str):
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        try:
            return set(json.load(f))
        except json.JSONDecodeError:
            return set()


def save_seen(path: str, seen_set):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(seen_set), f, ensure_ascii=False, indent=2)
