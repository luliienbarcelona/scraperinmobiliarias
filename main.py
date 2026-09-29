# -*- coding: utf-8 -*-
"""
Tier 1: scraping directo de las inmobiliarias más importantes (rápido y
confiable). GitHub Actions lo llama cada 5 minutos (ver
.github/workflows/scrape_fast.yml).
Para Tier 2 (más inmobiliarias, menos frecuente), ver main_tier2.py.
Para discovery (buscar inmobiliarias nuevas), ver main_discovery.py.
"""
import time

from config import FOTOCASA_ZONES, SEEN_FILE
from dedupe import load_seen, save_seen, check_listing, remember
from filters import passes_filters
from notify import send_telegram_message, format_listing_message
from sources import (
    loca_barcelona, fotocasa, finques_march, finques_bou, aproperties,
    finques_grau, selekta, shbarcelona, finques_teixidor,
)


def run_source(scrape_fn, zones: dict, all_listings: list):
    for zone_name, url in zones.items():
        try:
            found = scrape_fn(zone_name, url)
            print(f"  {zone_name}: {len(found)} anuncios encontrados")
            all_listings.extend(found)
        except Exception as e:
            print(f"  [ERROR] {zone_name}: {e}")
        time.sleep(2)


def run_citywide(scrape_fn, source_name: str, all_listings: list):
    """Para scrapers que traen todas las zonas en una sola llamada (piden
    una página citywide y filtran por barrio en el texto), en vez de una
    URL por barrio."""
    try:
        found = scrape_fn()
        print(f"  {source_name}: {len(found)} anuncios encontrados en tus zonas")
        all_listings.extend(found)
    except Exception as e:
        print(f"  [ERROR] {source_name}: {e}")
    time.sleep(2)


def main():
    all_listings = []

    print("Scrapeando fuentes citywide (long term)...")
    run_citywide(loca_barcelona.scrape_all_zones, "Loca Barcelona", all_listings)
    run_citywide(finques_march.scrape_all_zones, "Finques March", all_listings)
    run_citywide(finques_bou.scrape_all_zones, "Finques Bou", all_listings)
    run_citywide(aproperties.scrape_all_zones, "aProperties", all_listings)
    run_citywide(finques_grau.scrape_all_zones, "Finques Grau", all_listings)
    run_citywide(selekta.scrape_all_zones, "Selekta Properties", all_listings)
    run_citywide(shbarcelona.scrape_all_zones, "ShBarcelona", all_listings)
    run_citywide(finques_teixidor.scrape_all_zones, "Finques Teixidor", all_listings)

    print("Scrapeando Fotocasa...")
    run_source(fotocasa.scrape_zone, FOTOCASA_ZONES, all_listings)

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
    print("Listo.")


if __name__ == "__main__":
    main()
