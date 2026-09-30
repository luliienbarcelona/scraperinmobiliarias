# -*- coding: utf-8 -*-
"""
Tier 2 "JS": igual que main_tier2.py, pero solo para las inmobiliarias
del registro con "scraper_type": "playwright" (las que necesitan un
navegador real para ver algo). Corre cada 30 min, no cada 15
(ver .github/workflows/scrape_tier2_js.yml), porque abrir Chromium por
cada inmobiliaria es varias veces más lento que un request normal.

Comparte seen_tier2.json con main_tier2.py (son la misma noción de "ya
visto", no hace falta separarlos): una ficha ya notificada por un lado no
se vuelve a notificar por el otro aunque cambiara de scraper_type.
"""
import time

from config import SEEN_FILE_TIER2
from dedupe import load_seen, save_seen, check_listing, remember
from filters import passes_filters
from notify import send_telegram_message, format_listing_message
from agencies_registry import load_registry, save_registry, mark_scraped
from sources import playwright_agency


def main():
    entries = load_registry()
    js_entries = [
        e for e in entries
        if e.get("tier") == 2 and e.get("active") and e.get("scraper_type") == "playwright"
    ]

    print(f"Inmobiliarias Tier 2 (JS) activas: {len(js_entries)}")
    if not js_entries:
        print("Todavía no hay ninguna que necesite Playwright.")
        return

    seen = load_seen(SEEN_FILE_TIER2)
    to_notify = []

    for entry in js_entries:
        print(f"Scrapeando (con navegador) {entry['name']}...")
        try:
            listings, ok = playwright_agency.scrape_agency(entry)
        except Exception as e:
            print(f"  [ERROR] {entry['name']}: {e}")
            listings, ok = [], False

        found_new = False
        for listing in listings:
            status, key = check_listing(seen, listing)
            if status == "seen":
                continue
            if not passes_filters(listing):
                remember(seen, listing, key)
                continue
            to_notify.append((status, listing))
            remember(seen, listing, key)
            found_new = True

        mark_scraped(entry, found_new, ok)

    print(f"\nNuevos/actualizados que matchean los filtros: {len(to_notify)}")

    for status, listing in to_notify:
        send_telegram_message(format_listing_message(listing, status=status))
        time.sleep(1)

    save_seen(SEEN_FILE_TIER2, seen)
    save_registry(entries)
    print("Listo.")


if __name__ == "__main__":
    main()
