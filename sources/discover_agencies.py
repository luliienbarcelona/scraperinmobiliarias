# -*- coding: utf-8 -*-
"""
Discovery: busca inmobiliarias NUEVAS (no pisos sueltos) con Brave Search,
zona por zona. A cada dominio nuevo le hace un chequeo automático en
CASCADA, de más liviano a más pesado, hasta encontrar una forma de leer
precio+m2 (o hasta agotar las opciones):

  1. HTML plano (requests + BeautifulSoup) - la mayoría de los sitios
     "normales" pasan por aquí. Barato y rápido.
  2. Sitemap - si el listado carga por JS pero el sitio publica un
     sitemap.xml con la URL de cada ficha, y esa ficha individual SÍ es
     HTML server-side (caso confirmado: Tecnocasa). Un poco más caro
     (varios requests), pero nada de navegador.
  3. Playwright (Chromium headless) - último recurso, para sitios que de
     verdad necesitan ejecutar JS para mostrar algo. El más caro con
     diferencia, por eso solo se usa cuando 1 y 2 ya fallaron.

Si pasa por 2 o 3, la entrada que se suma a agencies.json queda marcada
con el scraper_type correspondiente ("sitemap" o "playwright") para que
main_tier2.py (scraper_type sitemap/generic, cada 15 min) o
main_tier2_js.py (scraper_type playwright, cada 30 min) sepan cuál usar.

Si no pasa por ninguno, igual queda anotada (inactiva) para no
re-evaluar el mismo dominio en cada corrida.
"""
import json
import os
import re
import gzip

import requests
from bs4 import BeautifulSoup

from config import BRAVE_API_KEY, REQUEST_HEADERS, ZONES
from sources.zone_match import match_zone

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

DISCOVERY_QUERY_TEMPLATES = [
    "inmobiliaria {zone} Barcelona alquiler pisos",
    "pisos en alquiler {zone} Barcelona inmobiliaria web",
    "administrador de fincas alquiler pisos {zone} Barcelona web propia",
    "pisos en alquiler particular {zone} Barcelona",
    "agencia inmobiliaria pisos alquiler {zone} Barcelona contacto",
]
# Mismas busquedas pero en catalan: muchas inmobiliarias chicas de barrio
# (ej. Lex Gestio Poblenou) tienen el sitio SOLO en catalan ("pisos en
# lloguer", "immobiliaria") y las busquedas en castellano no las traen. Se
# consultan con search_lang="ca" y el nombre del barrio en catalan.
DISCOVERY_QUERY_TEMPLATES_CA = [
    "immobiliària {zone} Barcelona lloguer pisos",
    "pisos de lloguer {zone} Barcelona immobiliària web",
    "agència immobiliària lloguer pisos {zone} Barcelona contacte",
]

# Nombre del barrio como se escribe en catalan (config.ZONES esta en
# castellano y sin tildes). Los que no estan aca se usan tal cual.
ZONE_NAMES_CA = {
    "Gracia": "Gràcia",
    "Sagrada Familia": "Sagrada Família",
    "Vila Olimpica": "Vila Olímpica",
}

# OJO: "administració finques X lloguer" (a secas) se sacó: en la práctica
# trae sobre todo administradores de comunidades de vecinos, que no
# publican anuncios de alquiler con precio en su web (gestionan edificios,
# no inventario para alquilar). La versión con "alquiler pisos ... web
# propia" trae mejores resultados, así encontramos Finques Teixidor y
# borsalloguers.com a mano.

# Sub-barrios que te interesan pero que config.ZONES no incluye como
# término de búsqueda propio (ahí solo están para el matching de texto,
# vía ZONE_ALIASES). Para discovery sí conviene buscarlos por su nombre
# específico: Brave da resultados distintos para "Fort Pienc" que para
# "Eixample" a secas, y así encontramos inmobiliarias más chicas y
# especializadas que quedan tapadas por las grandes cuando buscás el
# nombre del barrio madre.
DISCOVERY_EXTRA_ZONES = [
    "Fort Pienc", "Sant Antoni", "Parc i la Llacuna",
    "Vila Olímpica del Poblenou", "Camp de l'Arpa",
]

# Pool completo de combinaciones (zona, template). OJO con el presupuesto
# de Brave (free tier: 2000 consultas/mes): NO hay que recorrer todo este
# pool en cada corrida, hay que rotar (ver ROTATION_BATCH_SIZE más abajo)
# para no pasarse del límite gratis.
# Las de catalan van AL FINAL a proposito: asi las combinaciones en
# castellano conservan su posicion y el puntero de rotacion que ya esta
# guardado en discovery_state.json sigue apuntando a lo mismo.
ALL_QUERY_COMBOS = [
    (zone, template)
    for zone in (ZONES + DISCOVERY_EXTRA_ZONES)
    for template in DISCOVERY_QUERY_TEMPLATES
] + [
    (zone, template)
    for zone in (ZONES + DISCOVERY_EXTRA_ZONES)
    for template in DISCOVERY_QUERY_TEMPLATES_CA
]


def _query_lang(template: str) -> str:
    return "ca" if template in DISCOVERY_QUERY_TEMPLATES_CA else "es"


def _build_query(zone: str, template: str):
    """Devuelve (query, search_lang) para una combinacion (zona, template)."""
    lang = _query_lang(template)
    zone_txt = ZONE_NAMES_CA.get(zone, zone) if lang == "ca" else zone
    return template.format(zone=zone_txt), lang

# Cuántas combinaciones probar POR CORRIDA. Con 24/corrida x 2
# corridas/día x 30 días = 1440 consultas/mes, deja margen contra el tope
# de 2000. El pool completo (96 combos: 12 zonas x 5 templates en
# castellano + 12 zonas x 3 en catalan) se termina de recorrer en 4
# corridas (~2 días), y después arranca de nuevo desde el principio: así cada corrida prueba algo distinto en vez
# de repetir siempre las mismas 21 consultas de antes.
ROTATION_BATCH_SIZE = 24
DISCOVERY_STATE_FILE = "discovery_state.json"


def _load_rotation_offset() -> int:
    if not os.path.exists(DISCOVERY_STATE_FILE):
        return 0
    try:
        with open(DISCOVERY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("query_offset", 0)
    except (json.JSONDecodeError, OSError):
        return 0


def _save_rotation_offset(offset: int):
    with open(DISCOVERY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"query_offset": offset % len(ALL_QUERY_COMBOS)}, f)


def _next_query_batch():
    """Devuelve la tanda de (zona, template) para esta corrida, y avanza
    (y guarda) el puntero de rotación para la próxima."""
    offset = _load_rotation_offset()
    total = len(ALL_QUERY_COMBOS)
    batch = [ALL_QUERY_COMBOS[(offset + i) % total] for i in range(min(ROTATION_BATCH_SIZE, total))]
    _save_rotation_offset(offset + ROTATION_BATCH_SIZE)
    return batch

# Portales/agregadores y sitios ya evaluados a mano que no queremos que
# discovery proponga de nuevo (duplicaría lo que ya está en agencies.json,
# o son portales, no inmobiliarias individuales).
KNOWN_NON_CANDIDATES = [
    "idealista.com", "fotocasa.es", "habitaclia.com", "pisos.com",
    "yaencontre.com", "enalquiler.com", "milanuncios.com", "airbnb.",
    "booking.com", "spotahome.com", "nuroa.es", "trovit.es",
    "paginasamarillas.es", "spainhouses.net", "estatenearme.com",
    "kelify.com", "tucasa.com", "lucasfox.com", "lucasfox.es",
    "engelvoelkers.com", "wikipedia.org", "facebook.com", "instagram.com",
    "youtube.com", "linkedin.com", "x.com", "tiktok.com",
    # Confirmados a mano como de lujo o mal fit (auditoría 2026-09-29,
    # se colaron en la primera corrida de discovery porque el chequeo
    # automático todavía no filtraba por precio plausible):
    "bcn-advisors.com", "carolinamarti.es", "immobarcelo.es",
    "withfor.com", "diagonal111.com",
    # Confirmados a mano el 2026-09-30: urbanegroup.es es boutique de lujo
    # (solo venta, 400k-3.9M€), y api.cat solo devolvía garajes/locales,
    # nada de pisos (feedback directo de Luli).
    "urbanegroup.es", "api.cat",
    # Confirmado el 2026-10-04: agenciasinmobiliarias.com.es es un
    # directorio/portal de inmobiliarias (perfiles de agencias), no una
    # inmobiliaria individual con pisos propios.
    "agenciasinmobiliarias.com.es",
    # Confirmado a mano el 2026-09-30: skyflats.es no tiene precio en
    # ningún HTML propio (deriva a Idealista para verlo).
    "skyflats.es",
]

PRICE_RE = re.compile(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{2,6})(?:[.,]\d{1,2})?\s?€')
M2_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s?m[²2]', re.IGNORECASE)

# Techo para el chequeo automático (más laxo que MAX_PRICE de config.py,
# que es 1600): alcanza con que HAYA algún precio dentro de un rango
# razonable en la página, no que sea exactamente tu presupuesto.
DISCOVERY_PRICE_CEILING = 2200

# Rutas típicas de sitemap a probar cuando robots.txt no lo indica.
COMMON_SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml"]

# Cuántas fichas de sitemap muestrear como máximo antes de decidir si el
# dominio pasa el chequeo (no hace falta revisar las 500, con que 1-2
# tengan precio+m2+zona ya sabemos que el patrón funciona).
SITEMAP_SAMPLE_SIZE = 8


def _domain_of(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1).lower() if m else url.lower()


def search_candidate_domains():
    """Devuelve una lista de (domain, url) únicos por dominio. En vez de
    recorrer siempre las mismas zona x template, usa una tanda rotada del
    pool completo (ALL_QUERY_COMBOS) para no repetir exactamente lo mismo
    en cada corrida (ver ROTATION_BATCH_SIZE). No filtra por lo que ya
    está en el registro (eso lo hace main_discovery.py, que sí conoce
    agencies.json)."""
    seen_domains = set()
    candidates = []

    if not BRAVE_API_KEY:
        print("[discover_agencies] Falta BRAVE_API_KEY, se salta.")
        return candidates

    headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY}
    batch = _next_query_batch()
    print(f"[discover_agencies] Probando {len(batch)} combinaciones de esta tanda (de {len(ALL_QUERY_COMBOS)} en total)")

    for zone, template in batch:
        query, lang = _build_query(zone, template)
        data = None
        for attempt_lang in ([lang, "es"] if lang != "es" else ["es"]):
            params = {"q": query, "count": 10, "country": "es", "search_lang": attempt_lang}
            try:
                resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=20)
                if resp.status_code == 422 and attempt_lang != "es":
                    # Brave no acepto este idioma: reintentar la misma busqueda como "es".
                    print(f"  [WARN] Brave rechazo search_lang={attempt_lang}, reintento con es")
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.RequestException as e:
                print(f"  [ERROR] Brave para '{query}': {e}")
                break
        if data is None:
            continue

        for item in data.get("web", {}).get("results", []):
            url = item.get("url", "")
            domain = _domain_of(url)
            if not domain or domain in seen_domains:
                continue
            if any(known in domain for known in KNOWN_NON_CANDIDATES):
                continue
            seen_domains.add(domain)
            candidates.append((domain, url))

    return candidates


def _extract_plausible_price(text: str):
    prices = [
        float(p.replace(".", "").replace(",", "."))
        for p in PRICE_RE.findall(text)
    ]
    plausible = [p for p in prices if p <= DISCOVERY_PRICE_CEILING]
    return plausible, prices


def _check_one_page(url: str):
    """Paso 1 (HTML plano). Devuelve (ok, motivo) para UNA página puntual."""
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"no responde ({e})"

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    m2_hit = M2_RE.search(text)
    zone_hit = match_zone(text)

    if not m2_hit:
        return False, "no se ve ningún m² en el HTML crudo (puede ser JS, o no tiene listado en esta página)"
    if zone_hit is None:
        return False, "no menciona ninguna de tus zonas en esta página"

    plausible, prices = _extract_plausible_price(text)
    if not plausible:
        if prices:
            return False, f"los precios que aparecen son todos altos (mínimo encontrado: {min(prices):.0f}€), parece de lujo o venta"
        return False, "no se ve ningún precio en el HTML crudo"

    return True, f"tiene precio (ej. {min(plausible):.0f}€) y m² visibles, menciona {zone_hit}"


def _check_html_plano(url: str):
    """Prueba primero la URL puntual que dio Brave y, si falla, la home
    del dominio como respaldo (a veces el listado real está ahí)."""
    ok, reason = _check_one_page(url)
    if ok:
        return ok, reason

    domain = _domain_of(url)
    home_url = f"https://{domain}/"
    if home_url.rstrip("/") == url.rstrip("/"):
        return ok, reason

    ok_home, reason_home = _check_one_page(home_url)
    if ok_home:
        return ok_home, f"(vía home) {reason_home}"

    return False, f"{reason} / en la home tampoco: {reason_home}"


def _fetch_sitemap_locs(url: str):
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    content = resp.content
    if url.endswith(".gz"):
        try:
            content = gzip.decompress(content)
        except OSError:
            pass
    # Regex en vez de BeautifulSoup(content, "xml"): ese modo necesita el
    # paquete "lxml" instalado aparte (no está en requirements.txt y no
    # hace falta agregarlo solo para esto), y un sitemap es XML simple,
    # sacar los <loc>...</loc> con regex alcanza y sobra.
    text = content.decode("utf-8", errors="ignore")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.IGNORECASE)


def _find_sitemap_index_urls(domain: str):
    """Busca sitemaps declarados en robots.txt; si no hay, prueba rutas
    comunes. Devuelve una lista de URLs de sitemap (índice o directo)."""
    found = []
    try:
        resp = requests.get(f"https://{domain}/robots.txt", headers=REQUEST_HEADERS, timeout=10)
        if resp.ok:
            found = re.findall(r"(?im)^sitemap:\s*(\S+)", resp.text)
    except requests.RequestException:
        pass

    if found:
        return found

    return [f"https://{domain}{path}" for path in COMMON_SITEMAP_PATHS]


def _check_via_sitemap(domain: str):
    """Paso 2. Devuelve (ok, motivo, sitemap_urls_usados) o (False, motivo, None)."""
    to_visit = _find_sitemap_index_urls(domain)
    visited = set()
    leaf_sitemaps = []  # los .xml/.xml.gz que sí tenían fichas (no más índices)
    property_urls = []

    while to_visit and len(property_urls) < 500:
        sm_url = to_visit.pop(0)
        if sm_url in visited:
            continue
        visited.add(sm_url)
        try:
            locs = _fetch_sitemap_locs(sm_url)
        except requests.RequestException:
            continue
        if not locs:
            continue

        looks_like_index = sum(1 for l in locs if l.endswith((".xml", ".xml.gz"))) > len(locs) * 0.8
        if looks_like_index:
            to_visit.extend(locs)
            continue

        leaf_sitemaps.append(sm_url)
        property_urls.extend(locs)

    if not property_urls:
        return False, "no se encontró sitemap con URLs de ficha (ni en robots.txt ni en rutas comunes)", None

    # Priorizamos URLs que "suenan" a alquiler, si las hay, para no
    # gastar la muestra en fichas de venta.
    rental_like = [u for u in property_urls if re.search(r"alquil|lloguer|rent", u, re.IGNORECASE)]
    sample_pool = rental_like if rental_like else property_urls
    sample = sample_pool[:SITEMAP_SAMPLE_SIZE]

    hits = 0
    example_price = None
    for prop_url in sample:
        ok, _ = _check_one_page(prop_url)
        if ok:
            hits += 1
            if example_price is None:
                example_price = prop_url

    if hits == 0:
        return False, f"tiene sitemap ({len(property_urls)} fichas) pero ninguna de las {len(sample)} muestreadas tiene precio+m2+zona en HTML crudo (puede ser JS también en la ficha)", None

    url_filter_pattern = r"alquil|lloguer|rent" if rental_like else None
    return (
        True,
        f"sitemap con {len(property_urls)} fichas, {hits}/{len(sample)} muestreadas OK (ej. {example_price})",
        {"sitemap_urls": leaf_sitemaps, "url_filter_pattern": url_filter_pattern},
    )


def _check_via_playwright(url: str):
    """Paso 3, último recurso. Importa Playwright adentro de la función:
    si no está instalado (p. ej. corriendo esto fuera del workflow de
    discovery, que es el único que lo instala), este paso se salta solo
    en vez de romper toda la corrida."""
    try:
        from sources.playwright_agency import render_html
    except ImportError:
        return False, "Playwright no está instalado en este entorno, se salta este paso"

    try:
        html = render_html(url)
    except Exception as e:
        return False, f"Playwright no pudo renderizar ({e})"

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    if not M2_RE.search(text):
        return False, "ni renderizando con navegador aparece ningún m² (puede que este sí necesite login, o que el listado esté vacío)"
    zone_hit = match_zone(text)
    if zone_hit is None:
        return False, "renderizado sí trae contenido, pero no menciona ninguna de tus zonas"

    plausible, prices = _extract_plausible_price(text)
    if not plausible:
        if prices:
            return False, f"renderizado: precios altos nomás (mínimo {min(prices):.0f}€), parece lujo o venta"
        return False, "renderizado sí trae m² y zona, pero no se ve ningún precio"

    return True, f"(vía Playwright) tiene precio (ej. {min(plausible):.0f}€) y m² visibles, menciona {zone_hit}"


def quick_quality_check(url: str):
    """Chequeo en cascada: HTML plano -> sitemap -> Playwright. Devuelve
    (ok: bool, motivo: str, method: str|None, extra: dict|None).
    method es "generic", "sitemap" o "playwright" (para que
    main_discovery.py sepa qué scraper_type asignar); extra solo se usa
    para "sitemap" (sitemap_urls + url_filter_pattern)."""
    ok, reason = _check_html_plano(url)
    if ok:
        return True, reason, "generic", None

    domain = _domain_of(url)
    ok_sm, reason_sm, sitemap_info = _check_via_sitemap(domain)
    if ok_sm:
        return True, reason_sm, "sitemap", sitemap_info

    home_url = f"https://{domain}/"
    ok_pw, reason_pw = _check_via_playwright(url if url.rstrip("/") != home_url.rstrip("/") else home_url)
    if ok_pw:
        return True, reason_pw, "playwright", None

    combined = f"{reason} / sitemap: {reason_sm} / Playwright: {reason_pw}"
    return False, combined, None, None
