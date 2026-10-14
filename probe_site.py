import sys, re, os, requests
from playwright.sync_api import sync_playwright
os.makedirs("probe_out", exist_ok=True)
base = "https://www.monapart.com"
for p in ["/robots.txt", "/sitemap.xml"]:
    try:
        r = requests.get(base + p, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        open("probe_out/" + p.strip("/").replace("/", "_") + ".txt", "w").write(f"{r.status_code}\n{r.text[:6000]}")
    except Exception as e:
        open("probe_out/" + p.strip("/") + ".txt", "w").write(str(e))
urls = sys.argv[1:]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for i, u in enumerate(urls):
        pg = b.new_page()
        xhrs = []
        pg.on("response", lambda r: xhrs.append(f"{r.status} {r.request.resource_type} {r.url}") if r.request.resource_type in ("xhr", "fetch") else None)
        try:
            pg.goto(u, wait_until="networkidle", timeout=45000)
            pg.wait_for_timeout(3000)
        except Exception as e:
            xhrs.append("ERR " + str(e))
        open(f"probe_out/page{i}.html", "w").write(pg.content()[:400000])
        links = pg.eval_on_selector_all("a[href]", "els=>els.map(e=>e.href+' | '+e.innerText.replace(/\\s+/g,' ').slice(0,200))")
        open(f"probe_out/page{i}_links.txt", "w").write(u + "\n" + "\n".join(links) + "\n\nXHR:\n" + "\n".join(xhrs))
        open(f"probe_out/page{i}_text.txt", "w").write(pg.inner_text("body")[:8000])
    b.close()
