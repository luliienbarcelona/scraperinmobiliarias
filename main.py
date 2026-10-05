# -*- coding: utf-8 -*-
"""
Tier 1: scraping directo de las inmobiliarias más importantes (rápido y
confiable). Lo ejecuta run_tier1_loop.py en loop dentro de un job de
GitHub Actions (ver .github/workflows/scrape_fast.yml).
Para Tier 2 (más inmobiliarias, menos frecuente), ver main_tier2.py.
Para discovery (buscar inmobiliarias nuevas), ver main_discovery.py.
"""
import time

from config import FOTOCASA_ZONES, SEEN_FILE
from dedupe import load_seen, save_seen, check_listing, remember
from filters import passes_filters
import health
from notify import send_telegram_message, format_listing_message
from sources import (
    loca_barcelona, fotocasa, finques_march, finques_bou, aproperties,
    finques_grau, selekta, shbarcelona, finques_teixidor,
)


def _safe_record(state: dict, alerts: list, source: str, count: int, error: bool):
    """La salud nunca puede romper la corrida principal."""
    try:
        msg = health.record(state, source, count, error=error)
        if msg:
            alerts.append(msg)
    except Exception as e:
        print(f"[health] {source}: {e}")


def run_source(scrape_fn, zones: dict, all_listings: list, source_name: str = None,
               state: dict = None, alerts: list = None):
    total, errors = 0, 0
    for zone_name, url in zones.items():
        try:
            found = scrape_fn(zone_name, url)
            print(f"  {zone_name}: {len(found)} anuncios encontrados")
            all_listings.extend(found)
            total += len(found)
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {zone_name}: {e}")
        time.sleep(2)
    if state is not None and source_name:
        # Error solo si fallaron TODAS las zonas (una zona suelta caida no cuenta).
        _safe_record(state, alerts, source_name, total, error=(errors == len(zones) and errors > 0))


def run_citywide(scrape_fn, source_name: str, all_listings: list,
                 state: dict = None, alerts: list = None):
    """Para scrapers que traen todas las zonas en una sola llamada (piden
    una página citywide y filtran por barrio en el texto), en vez de una
    URL por barrio."""
    count, error = 0, False
    try:
        found = scrape_fn()
        count = len(found)
        print(f"  {source_name}: {count} anuncios encontrados en tus zonas")
        all_listings.extend(found)
    except Exception as e:
        error = True
        print(f"  [ERROR] {source_name}: {e}")
    if state is not None:
        _safe_record(state, alerts, source_name, count, error)
    time.sleep(2)


def main(include_fotocasa: bool = True):
    all_listings = []
    health_state = health.load_health()
    health_alerts = []

    print("Scrapeando fuentes citywide (long term)...")
    run_citywide(loca_barcelona.scrape_all_zones, "Loca Barcelona", all_listings, health_state, health_alerts)
    run_citywide(finques_march.scrape_all_zones, "Finques March", all_listings, health_state, health_alerts)
    run_citywide(finques_bou.scrape_all_zones, "Finques Bou", all_listings, health_state, health_alerts)
    run_citywide(aproperties.scrape_all_zones, "aProperties", all_listings, health_state, health_alerts)
    run_citywide(finques_grau.scrape_all_zones, "Finques Grau", all_listings, health_state, health_alerts)
    run_citywide(selekta.scrape_all_zones, "Selekta Properties", all_listings, health_state, health_alerts)
    run_citywide(shbarcelona.scrape_all_zones, "ShBarcelona", all_listings, health_state, health_alerts)
    run_citywide(finques_teixidor.scrape_all_zones, "Finques Teixidor", all_listings, health_state, health_alerts)

    if include_fotocasa:
        print("Scrapeando Fotocasa...")
        run_source(fotocasa.scrape_zone, FOTOCASA_ZONES, all_listings, "Fotocasa", health_state, health_alerts)

    print(f"\nTotal de anuncios crudos encontrados: {len(all_listings)}")

    seen = load_seen(SEEN_FILE)
    to_notify = []  # (status, listing)

    for listing in all_listings:
        status, key = check_listing(seen, listing)
        if status == "seen":
            continue
        if not passes_filters(listing):
            # Igual lo recordamos, así no lo re-evaluamos cada corrida.
            remember(seen, listing, key)
            continue
        to_notify.append((status, listing))
        remember(seen, listing, key)

    print(f"Nuevos/actualizados que matchean los filtros: {len(to_notify)}")

    for status, listing in to_notify:
        send_telegram_message(format_listing_message(listing, status=status))
        time.sleep(1)

    save_seen(SEEN_FILE, seen)

    # Salud por fuente: guardar estado y avisar si alguna lleva mucho en cero o con error.
    health.save_health(health_state)
    for msg in health_alerts:
        send_telegram_message(msg)
        time.sleep(1)
    print("Listo.")


if __name__ == "__main__":
    main()
