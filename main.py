# -*- coding: utf-8 -*-
"""
Capa 1: scraping directo de inmobiliarias conocidas (rápido y confiable).
GitHub Actions lo llama cada 5 minutos (ver .github/workflows/scrape_fast.yml).
Para la Capa 2 (búsqueda amplia vía Brave), ver main_broad.py.
"""
import time

from config import MAX_PRICE, MIN_M2, FOTOCASA_ZONES, SEEN_FILE
from dedupe import load_seen, save_seen
from notify import send_telegram_message, format_listing_message
from sources import loca_barcelona, fotocasa, finques_march, finques_bou, aproperties, finques_grau


def passes_filters(listing: dict) -> bool:
    if listing.get("is_short_term"):
        return False
    price = listing.get("price")
    m2 = listing.get("m2")
    if price is None or price > MAX_PRICE:
        return False
    if m2 is not None and m2 < MIN_M2:
        return False
    return True


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

    print("Scrapeando Fotocasa...")
    run_source(fotocasa.scrape_zone, FOTOCASA_ZONES, all_listings)

    print(f"\nTotal de anuncios crudos encontrados: {len(all_listings)}")

    seen = load_seen(SEEN_FILE)
    new_matches = []

    for listing in all_listings:
        if listing["url"] in seen:
            continue
        seen.add(listing["url"])
        if passes_filters(listing):
            new_matches.append(listing)

    print(f"Nuevos que matchean los filtros: {len(new_matches)}")

    for listing in new_matches:
        send_telegram_message(format_listing_message(listing))
        time.sleep(1)

    save_seen(SEEN_FILE, seen)
    print("Listo.")


if __name__ == "__main__":
    main()
