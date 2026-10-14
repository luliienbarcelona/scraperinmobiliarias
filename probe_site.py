import sys, os, requests, traceback
from playwright.sync_api import sync_playwright

os.makedirs("probe_out", exist_ok=True)

def w(path, text):
    with open("probe_out/" + path, "w", encoding="utf-8") as f:
        f.write(text)

base = "https://www.monapart.com"
for p in ["/robots.txt", "/sitemap.xml"]:
    try:
        r = requests.get(base + p, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        w(p.strip("/") + ".out", f"{r.status_code}\n{r.text[:6000]}")
    except Exception as e:
        w(p.strip("/") + ".out", str(e))

try:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for i, u in enumerate(sys.argv[1:]):
            try:
                pg = b.new_page()
                xhrs = []
                def on_resp(r, xhrs=xhrs):
                    if r.request.resource_type in ("xhr", "fetch") and "monapart" in r.url:
                        xhrs.append(f"{r.status} {r.url}")
                        try:
                            if "thecat" in r.url:
                                w("api_" + str(len(xhrs)) + ".json", r.url + "\n" + r.text()[:60000])
                        except Exception:
                            pass
                pg.on("response", on_resp)
                try:
                    pg.goto(u, wait_until="networkidle", timeout=45000)
                    pg.wait_for_timeout(3000)
                    for _ in range(6):
                        pg.mouse.wheel(0, 4000)
                        pg.wait_for_timeout(1200)
                except Exception as e:
                    xhrs.append("ERR " + str(e))
                w(f"page{i}.html", pg.content()[:400000])
                links = pg.eval_on_selector_all(
                    "a[href]",
                    "els=>els.map(e=>e.href+' | '+e.innerText.replace(/\\s+/g,' ').slice(0,200))")
                w(f"page{i}_links.txt", u + "\n" + "\n".join(links) + "\n\nXHR:\n" + "\n".join(xhrs))
                w(f"page{i}_text.txt", pg.inner_text("body")[:8000])
            except Exception:
                w(f"page{i}_error.txt", traceback.format_exc())
        b.close()
except Exception:
    w("error.txt", traceback.format_exc())
