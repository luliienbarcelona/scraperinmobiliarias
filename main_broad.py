# -*- coding: utf-8 -*-
"""
Capa 2: búsqueda amplia vía Google, para agarrar inmobiliarias que no
conocemos de antemano. GitHub Actions lo llama cada 1-2 horas (ver
.github/workflows/scrape_broad.yml) por el límite de consultas gratis
de Google (100/día).

A diferencia de la Capa 1, acá no siempre se puede leer el precio o los
m2 del snippet de Google. Cuando falta ese dato, el anuncio se notifica
igual pero marcado como "revisar a mano", en vez de descartarlo.
"""
import time

from config import MAX_PRICE, MIN_M2, BROAD_SEARCH_QUERIES, SEEN_FILE_BROAD
from dedupe import load_seen, save_seen
from notify import send_telegram_message, format_listing_message
from sources import broad_search


def passes_filters(listing: dict) -> bool:
    if listing.get("is_short_term"):
        return False
    price = listing.get("price")
    m2 = listing.get("m2")
    # Si Google no mostró precio o m2 en el snippet, no lo descartamos:
    # se notifica marcado como "revisar a mano" (ver notify.py).
    if price is not None and price > MAX_PRICE:
        return False
    if m2 is not None and m2 < MIN_M2:
        return False
    return True


def main():
    all_listings = []

    print("Buscando en Google por zona...")
    for zone_name, query in BROAD_SEARCH_QUERIES.items():
        try:
            found = broad_search.search_zone(zone_name, query)
            print(f"  {zone_name}: {len(found)} resultados")
            all_listings.extend(found)
        except Exception as e:
            print(f"  [ERROR] {zone_name}: {e}")
        time.sleep(1)

    print(f"\nTotal de resultados crudos: {len(all_listings)}")

    seen = load_seen(SEEN_FILE_BROAD)
    new_matches = []

    for listing in all_listings:
        if listing["url"] in seen:
            continue
        seen.add(listing["url"])
        if passes_filters(listing):
            new_matches.append(listing)

    print(f"Nuevos que matchean (o necesitan revisión manual): {len(new_matches)}")

    for listing in new_matches:
        send_telegram_message(format_listing_message(listing))
        time.sleep(1)

    save_seen(SEEN_FILE_BROAD, seen)
    print("Listo.")


if __name__ == "__main__":
    main()
