# -*- coding: utf-8 -*-
"""Sondeo temporal: baja una pagina, robots.txt y sitemap desde la red de GitHub
y los guarda en probe_out/ para poder leerlos. Se borra despues de usarlo."""
import os, sys, requests
from urllib.parse import urlparse
from config import REQUEST_HEADERS

url = sys.argv[1]
p = urlparse(url)
origin = f"{p.scheme}://{p.netloc}"
os.makedirs("probe_out", exist_ok=True)

def grab(name, u):
    try:
        r = requests.get(u, headers=REQUEST_HEADERS, timeout=25, allow_redirects=True)
        chain = " -> ".join([h.url for h in r.history] + [r.url])
        with open(f"probe_out/{name}", "w", encoding="utf-8") as f:
            f.write(f"<!-- status={r.status_code} chain={chain} len={len(r.text)} -->\n{r.text}")
        print(name, r.status_code, len(r.text))
    except Exception as e:
        with open(f"probe_out/{name}", "w", encoding="utf-8") as f:
            f.write(f"ERROR {e}")
        print(name, "ERROR", e)

grab("page.html", url)
grab("robots.txt", origin + "/robots.txt")
grab("sitemap.xml", origin + "/sitemap.xml")
