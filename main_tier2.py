# -*- coding: utf-8 -*-
"""
Tier 2: monitorea todas las inmobiliarias "generic" del registro
(agencies.json) que estén activas. GitHub Actions lo llama cada ~15 min
(ver .github/workflows/scrape_tier2.yml).

Arranca vacío hasta que agencies_registry.py tenga entradas con
"scraper_type": "generic" y "tier": 2 — se van sumando a medida que las
vamos verificando (ver main_discovery.py, que las propone automáticamente).
"""
import time

from config import SEEN_FILE_TIER2
from dedupe import load_seen, save_seen, check_listing, remember
from filters import passes_filters
from notify import send_telegram_message, format_listing_message
from agencies_registry import load_registry, save_registry, mark_scraped
from sources import generic_agency


def main():
    entries = load_registry()
    tier2_entries = [
        e for e in entries
        if e.get("tier") == 2 and e.get("active") and e.get("scraper_type") == "generic"
    ]

    print(f"Inmobiliarias Tier 2 activas: {len(tier2_entries)}")
    if not tier2_entries:
        print("Todavía no hay ninguna. main_discovery.py las va sumando de a poco.")
        return

    seen = load_seen(SEEN_FILE_TIER2)
    to_notify = []

    for entry in tier2_entries:
        print(f"Scrapeando {entry['name']}...")
        try:
            listings, ok = generic_agency.scrape_agency(entry)
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
        time.sleep(2)

    print(f"\nNuevos/actualizados que matchean los filtros: {len(to_notify)}")

    for status, listing in to_notify:
        send_telegram_message(format_listing_message(listing, status=status))
        time.sleep(1)

    save_seen(SEEN_FILE_TIER2, seen)
    save_registry(entries)
    print("Listo.")


if __name__ == "__main__":
    main()
