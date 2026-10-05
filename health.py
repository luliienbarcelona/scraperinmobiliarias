# -*- coding: utf-8 -*-
"""
Salud por fuente para el Tier 1.

Problema que resuelve: hasta ahora, si el sitio de una inmobiliaria cambiaba
su HTML y el scraper empezaba a devolver 0 anuncios, o si tiraba error en
cada corrida, nadie se enteraba: el workflow terminaba en verde y Telegram
se quedaba callado igual que cuando simplemente no hay pisos nuevos. Con el
mercado tan flojo ahora, "no llega nada" es la situacion normal y eso tapa
las fuentes rotas.

Que hace: en cada corrida anota por fuente cuantos anuncios devolvio (ya
filtrados a tus zonas) o si fallo, y manda UN aviso por Telegram cuando una
fuente lleva demasiado tiempo en cero o dando error, y otro cuando se
recupera. Las ventanas se miden en tiempo, no en cantidad de corridas, asi
siguen valiendo si cambia la frecuencia del cron.

Filosofia: 0 anuncios en tus zonas puede ser normal (una inmobiliaria chica
puede pasar horas sin nada en tus barrios), por eso el umbral de cero es
largo. Un error repetido es mas sospechoso, por eso el umbral es corto.

Todo esta envuelto para que un problema aca NUNCA rompa la corrida principal.
"""
import json
import os
from datetime import datetime, timezone

HEALTH_FILE = "health.json"

ZERO_HOURS_KNOWN_GOOD = 12   # fuente que antes traia cosas y ahora no
ZERO_HOURS_NEVER_SEEN = 24   # fuente que todavia nunca trajo nada
ERROR_HOURS = 2              # error en cada corrida durante este tiempo


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts):
    return datetime.fromisoformat(ts) if ts else None


def load_health(path: str = HEALTH_FILE) -> dict:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[health] no pude leer {path}: {e}")
    return {}


def save_health(health: dict, path: str = HEALTH_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(health, f, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception as e:
        print(f"[health] no pude guardar {path}: {e}")


def record(health: dict, source: str, count: int, error: bool = False, now: datetime = None):
    """Actualiza el estado de `source` y devuelve un mensaje de aviso (str)
    si corresponde mandar uno ahora, o None. No manda nada por si misma."""
    now = now or _now()
    st = health.setdefault(source, {
        "ever_nonzero": False,
        "zero_since": None,
        "error_since": None,
        "alerted_zero": False,
        "alerted_error": False,
        "last_nonzero": None,
    })
    msgs = []

    if error:
        st["error_since"] = st["error_since"] or now.isoformat()
        since = _parse(st["error_since"])
        hours = (now - since).total_seconds() / 3600
        if hours >= ERROR_HOURS and not st["alerted_error"]:
            st["alerted_error"] = True
            msgs.append(
                f"⚠️ <b>{source}</b> da error en cada corrida hace ~{hours:.0f}h. "
                "Puede haber cambiado el sitio o estar caído."
            )
        return "\n".join(msgs) or None

    # corrida sin error
    recovered_from_error = st["alerted_error"]
    st["error_since"] = None
    st["alerted_error"] = False

    if count > 0:
        recovered_from_zero = st["alerted_zero"]
        st["ever_nonzero"] = True
        st["zero_since"] = None
        st["alerted_zero"] = False
        st["last_nonzero"] = now.isoformat()
        if recovered_from_error or recovered_from_zero:
            msgs.append(f"✅ <b>{source}</b> volvió a traer anuncios.")
        return "\n".join(msgs) or None

    st["zero_since"] = st["zero_since"] or now.isoformat()
    hours = (now - _parse(st["zero_since"])).total_seconds() / 3600
    limit = ZERO_HOURS_KNOWN_GOOD if st["ever_nonzero"] else ZERO_HOURS_NEVER_SEEN
    if hours >= limit and not st["alerted_zero"]:
        st["alerted_zero"] = True
        msgs.append(
            f"⚠️ <b>{source}</b> lleva ~{hours:.0f}h sin traer ningún anuncio en tus zonas. "
            "Puede ser mercado quieto o que el sitio cambió de formato."
        )
    if recovered_from_error and not msgs:
        msgs.append(f"✅ <b>{source}</b> ya no da error (sigue sin anuncios en tus zonas).")
    return "\n".join(msgs) or None
