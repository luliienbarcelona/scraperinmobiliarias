# -*- coding: utf-8 -*-
"""
Discovery: busca inmobiliarias nuevas (no pisos sueltos) y las suma al
registro (agencies.json) si pasan un chequeo automático básico. Corre 1-2
veces por día (ver .github/workflows/scrape_discovery.yml), no hace falta
más seguido: el objetivo es ir ampliando el universo de Tier 2 de a poco,
no buscar pisos en tiempo real (eso lo hacen Tier 1 y Tier 2).

Filosofía (acordada con Luli): filtro automático + aviso. No espera
aprobación manual para activar una fuente nueva, pero SIEMPRE avisa por
Telegram qué sumó y qué descartó, para que quede auditable.

El chequeo automático (discover_agencies.quick_quality_check) ahora prueba
en cascada: HTML plano -> sitemap -> Playwright (ver ese archivo). Según
cuál método funcionó, la entrada nueva queda con distinto scraper_type:
"generic" (HTML plano, la mayoría), "sitemap" o "playwright" (JS real,
va a la cola de main_tier2_js.py en vez de main_tier2.py).
"""
import time

from agencies_registry import load_registry, save_registry, domain_exists, add_candidate
from notify import send_telegram_message
from sources import discover_agencies


def main():
    entries = load_registry()

    print("Buscando inmobiliarias nuevas...")
    candidates = discover_agencies.search_candidate_domains()
    print(f"Candidatos encontrados (antes de filtrar por el registro): {len(candidates)}")

    added = []
    rejected = []

    for domain, url in candidates:
        if domain_exists(entries, domain):
            continue  # ya lo conocíamos (activo o ya descartado antes)

        ok, reason, method, extra = discover_agencies.quick_quality_check(url)
        time.sleep(1)

        if ok:
            new_entry = {
                "name": domain,
                "domain": domain,
                "rental_url": url,
                "source_type": "agency",
                "scraper_type": method,  # "generic", "sitemap" o "playwright"
                "module": None,
                "href_pattern": None,  # generic_agency.py / playwright_agency.py usan un patrón genérico por defecto
                "tier": 2,
                "active": True,
                "last_scrape": None,
                "last_new_listing": None,
                "failure_count": 0,
                "notes": f"Sumada automáticamente por discovery, vía {method} ({reason}). Revisar a mano si conviene afinar el patrón.",
            }
            if method == "sitemap" and extra:
                new_entry["sitemap_urls"] = extra["sitemap_urls"]
                new_entry["url_filter_pattern"] = extra["url_filter_pattern"]
                new_entry["max_new_per_run"] = 40
            if add_candidate(entries, new_entry):
                added.append(f"{domain} (vía {method})")
        else:
            rejected_entry = {
                "name": domain,
                "domain": domain,
                "rental_url": url,
                "source_type": "agency",
                "scraper_type": None,
                "module": None,
                "tier": None,
                "active": False,
                "last_scrape": None,
                "last_new_listing": None,
                "failure_count": 0,
                "notes": f"Descartada por discovery automático: {reason}.",
            }
            if add_candidate(entries, rejected_entry):
                rejected.append(domain)

    print(f"Sumadas a Tier 2: {len(added)}")
    print(f"Descartadas: {len(rejected)}")

    if added or rejected:
        lines = ["🔎 <b>Discovery de inmobiliarias</b>"]
        if added:
            lines.append("\n✅ Sumadas a Tier 2 (activas):")
            lines.extend(f"• {d}" for d in added)
        if rejected:
            lines.append("\n❌ Revisadas y descartadas:")
            lines.extend(f"• {d}" for d in rejected)
        send_telegram_message("\n".join(lines))

    save_registry(entries)
    print("Listo.")


if __name__ == "__main__":
    main()
