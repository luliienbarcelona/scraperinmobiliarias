# Scraper de departamentos en Barcelona

Busca pisos en alquiler de larga estancia en Barcelona y avisa por
Telegram apenas aparece uno nuevo que pueda servir. Corre solo en GitHub
Actions (gratis, repo público). Tiene tres capas:

## Las tres capas

**Tier 1 — rápida (`main.py`, cada 5 min)**
Scrapea directo las inmobiliarias que ya verificamos a mano: hoy son Loca
Barcelona, Finques March, Finques Bou, aProperties, Finques Grau, Selekta
Properties, ShBarcelona y Finques Teixidor, más Fotocasa como portal. Cada
una tiene su propio archivo en `sources/`.

**Tier 2 — más cobertura, menos frecuente (`main_tier2.py`, cada 15 min)**
Recorre las inmobiliarias del registro (`agencies.json`) marcadas como
`"tier": 2` y `"active": true`, usando uno de dos scrapers según
`"scraper_type"` (no hace falta un archivo por sitio):
- `"generic"` (`sources/generic_agency.py`): lee el listado directo con
  requests + BeautifulSoup, matcheando un patrón de link a cada ficha.
- `"sitemap"` (`sources/sitemap_agency.py`): para sitios cuyo LISTADO
  carga con JavaScript pero publican un sitemap.xml con la URL de cada
  ficha individual, y esa ficha sí es HTML server-side (caso: Tecnocasa).
  Guarda en `sitemap_seen.json` qué fichas ya evaluó, para no tener que
  volver a pedir cientos de páginas en cada corrida.

**Discovery (`main_discovery.py`, 2 veces por día)**
Busca inmobiliarias nuevas con Brave Search (zona por zona, por ejemplo
"inmobiliaria Poblenou Barcelona alquiler"), no pisos sueltos. A cada
dominio nuevo le hace un chequeo automático EN CASCADA (ver
`sources/discover_agencies.py`), de más liviano a más pesado, antes de
descartarlo:

1. HTML plano (requests) - la mayoría de los sitios normales.
2. Sitemap - si el listado carga por JS pero el sitio publica un
   sitemap.xml con la URL de cada ficha, y la ficha sí es HTML
   server-side (caso: Tecnocasa).
3. Playwright (navegador headless) - último recurso, para sitios que de
   verdad necesitan ejecutar JS para mostrar algo.

Si pasa por 2 o 3 queda marcada con ese `scraper_type` en el registro, y
según cuál sea la procesa `main_tier2.py` (generic/sitemap, cada 15 min) o
`main_tier2_js.py` (playwright, cada 30 min, más caro por eso menos
seguido). No espera aprobación manual para activar una fuente nueva, pero
SIEMPRE avisa por Telegram qué sumó (y por cuál método) y qué descartó,
para que quede auditable.

## El registro: `agencies.json`

Es la fuente de verdad de qué inmobiliarias conocemos, cuáles están
activas, en qué tier, y notas de por qué se descartó cada una que no pasó
el audit. Discovery y Tier 2 lo leen y lo actualizan solos (se commitea de
vuelta al repo en cada corrida). Las fuentes de Tier 1 también están
anotadas ahí, aunque tienen su propio archivo en `sources/` en vez de usar
el scraper genérico.

## Filtros

- Máximo 1600€/mes, mínimo 50m² (`config.py`)
- Zonas: Eixample (+ Dreta, Esquerra, Fort Pienc, Sant Antoni), Sagrada
  Família, Poblenou (+ Parc i la Llacuna), El Clot (+ Camp de l'Arpa),
  Gràcia, Barceloneta, Vila Olímpica
- Solo alquiler de larga estancia (se descarta lo que dice "temporada",
  "turístico", etc.)
- Se rechaza solo si dice explícitamente "no se admiten mascotas"

**Filosofía importante** (`filters.py`): un dato que falta (precio, m²,
tipo de alquiler, mascotas) nunca es motivo de descarte por sí solo. Solo
se rechaza cuando hay una señal explícita de que no sirve. Todo lo demás
se manda a Telegram marcado como "desconocido" en vez de perderse.

## Archivos que NO hay que pisar

`seen_listings.json`, `seen_tier2.json`, `seen_broad.json`,
`sitemap_seen.json` y `agencies.json` los actualiza el bot solo en cada
corrida (con last_scrape, precios ya vistos, fichas de sitemap ya
evaluadas, etc). Si subís una versión vieja desde tu compu vas a perder
ese historial y capaz te llegan notificaciones repetidas.

## Secrets necesarios (Settings → Secrets → Actions)

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `BRAVE_API_KEY` (solo lo usa discovery)

## Bug corregido (2026-09-30): precios de 4+ dígitos sin separador

El regex que lee el precio en todos los scrapers leía mal un precio como
"1200€" (sin punto ni coma) y lo interpretaba como "200€" -se quedaba con
los últimos 3 dígitos en vez del número completo-. Si el sitio SÍ ponía
separador de miles ("1.200€") funcionaba bien, el problema era solo sin
separador. Ya está corregido en los 13 archivos que tenían su propia
copia del regex (`sources/*.py`). Si veías algún piso con un precio que
no tenía sentido, puede haber sido por esto.
