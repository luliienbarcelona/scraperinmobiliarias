# -*- coding: utf-8 -*-
"""
Runner en loop para el Tier 1.

Por que existe: el cron de GitHub Actions "*/5" no se cumple (en la practica
corria cada ~19 min, con picos de 31). Para enterarnos rapido de un piso
nuevo, en vez de depender del cron, un solo job corre ~55 minutos y repite
el scraping cada ~2.5 minutos adentro. El cron (cada 30 min) solo sirve para
relanzar el job; con `concurrency` en el workflow los lanzamientos se encolan
y se ejecutan uno atras del otro, asi que no quedan huecos aunque GitHub
demore el cron.

Cuidado con las inmobiliarias: cada sitio se consulta una vez por iteracion
(~cada 2.5 min). Fotocasa, que es un portal grande con proteccion anti-bots,
se consulta solo 1 de cada FOTOCASA_EVERY iteraciones (~cada 10 min).

Estado: seen_listings.json se commitea y se pushea apenas cambia (o sea,
cuando hubo algo nuevo para avisar), para que si el job se corta no se
reenvien avisos. health.json se commitea al final y junto con esos commits.

Variables de entorno (opcionales, para pruebas):
  LOOP_INTERVAL_SECONDS (default 150), LOOP_DURATION_SECONDS (default 3300)
"""
import os
import random
import subprocess
import time

import main as tier1

INTERVAL = int(os.environ.get("LOOP_INTERVAL_SECONDS", "150"))
DURATION = int(os.environ.get("LOOP_DURATION_SECONDS", str(55 * 60)))
FOTOCASA_EVERY = 4
MIN_SLEEP = 20
SAFETY_MARGIN = 30  # no arrancar una iteracion si no hay tiempo de terminarla


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def _dirty(path: str) -> bool:
    return bool(_git("status", "--porcelain", path).stdout.strip())


def commit_state(files, message: str) -> bool:
    """Commitea y pushea los archivos de estado que hayan cambiado. Nunca
    levanta excepcion: un problema de git no debe tumbar el loop."""
    try:
        existing = [f for f in files if os.path.exists(f)]
        for f in existing:
            _git("add", f)
        if _git("diff", "--staged", "--quiet").returncode == 0:
            return False
        _git("commit", "-m", message)
        for attempt in range(2):
            _git("pull", "--rebase", "--autostash", "origin", "main")
            res = _git("push", "origin", "HEAD:main")
            if res.returncode == 0:
                return True
            print(f"[loop] push fallo (intento {attempt + 1}): {res.stderr.strip()[:200]}")
        return False
    except Exception as e:
        print(f"[loop] error de git: {e}")
        return False


def main():
    deadline = time.monotonic() + DURATION
    i = 0
    print(f"[loop] arrancando: intervalo {INTERVAL}s, duracion {DURATION}s")
    while True:
        started = time.monotonic()
        print(f"\n[loop] iteracion {i} ({time.strftime('%H:%M:%S')})")
        try:
            tier1.main(include_fotocasa=(i % FOTOCASA_EVERY == 0))
        except Exception as e:
            print(f"[loop] la iteracion {i} fallo: {e}")

        if _dirty("seen_listings.json"):
            commit_state(["seen_listings.json", "health.json"], "Actualizar anuncios vistos [skip ci]")

        i += 1
        elapsed = time.monotonic() - started
        wait = max(INTERVAL - elapsed, MIN_SLEEP) + random.uniform(0, 15)
        if time.monotonic() + wait + SAFETY_MARGIN >= deadline:
            break
        time.sleep(wait)

    commit_state(["seen_listings.json", "health.json"], "Actualizar anuncios vistos y salud [skip ci]")
    print(f"[loop] listo, {i} iteraciones")


if __name__ == "__main__":
    main()
