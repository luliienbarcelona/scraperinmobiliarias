# -*- coding: utf-8 -*-
"""
Guardas compartidas por generic_agency y playwright_agency para no confundir
links de navegacion/footer con fichas de pisos.

Caso real (fincasfinurba.com, 2026-10-05): sin href_pattern el scraper
aceptaba cualquier link, y para links de footer (cookies.php, Twitter,
Facebook, Instagram, WhatsApp) subia por los ancestros hasta un contenedor
que abarcaba toda la pagina, tomaba el primer precio/m2 que encontraba
adentro y lo asignaba a ese link como si fuera una ficha.

Filosofia UNKNOWN != REJECT: estas guardas solo descartan en base a una
senal explicita de que NO es una ficha (link a otro dominio, o contenedor
demasiado grande para ser una sola tarjeta), nunca por un dato faltante.
"""
from urllib.parse import urlparse

# Una tarjeta de piso real tiene decenas o pocos cientos de caracteres. Un
# contenedor de mas de esto casi seguro agrupa varias tarjetas o toda la pagina.
MAX_CARD_TEXT_CHARS = 2000


def _base_host(host: str) -> str:
    host = (host or "").lower().strip()
    return host[4:] if host.startswith("www.") else host


def is_same_site(href: str, domain: str) -> bool:
    """True si el href es relativo o apunta al dominio de la inmobiliaria
    (o a un subdominio). False para links a redes sociales, WhatsApp,
    blogspot, etc."""
    if not href:
        return False
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if not parsed.netloc:
        return True  # relativo
    host = _base_host(parsed.netloc)
    dom = _base_host(domain)
    return host == dom or host.endswith("." + dom)


def card_text_ok(text: str) -> bool:
    return len(text) <= MAX_CARD_TEXT_CHARS
