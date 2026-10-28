#!/usr/bin/env bash
# Sube el commit de estado (anuncios vistos, registro) al repo con reintentos.
# Varios workflows commitean al mismo repo en paralelo; si otro empuja entre
# nuestro pull y nuestro push, el push se rechaza. Antes eso dejaba el job en
# rojo (mail de "All jobs have failed") aunque el scraping hubiera salido bien
# (caso real: Tier 2 JS, 2026-10-26 17:07 UTC). Reintentamos con pausa corta.
# Si no hay nada para subir, no hace nada.
for i in 1 2 3 4 5 6; do
  if git pull --rebase origin main && git push; then
    exit 0
  fi
  echo "[push_state] intento $i fallo, reintentando..."
  git rebase --abort 2>/dev/null || true
  sleep $((i * 4 + RANDOM % 5))
done
echo "[push_state] no pude subir el estado despues de 6 intentos"
exit 1
