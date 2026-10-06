# Scraper de departamentos en Barcelona

Busca pisos en alquiler de larga estancia en Barcelona y avisa por
Telegram apenas aparece uno nuevo que pueda servir. Corre solo en GitHub
Actions (gratis, repo público). Tiene tres capas:

## Las tres capas

**Tier 1 — rápida (`main.py` vía `run_tier1_loop.py`, cada ~2,5 min)**
Scrapea directo las inmobiliarias que ya verificamos a mano: hoy son Loca
Barcelona, Finques March, Finques Bou, aProperties, Finques Grau, Selekta
Properties, ShBarcelona y Finques Teixidor, más Fotocasa como portal. Cada
una tiene su propio archivo en `sources/`.

El cron de GitHub Actions no respeta intervalos cortos (el "cada 5 min"
corría en realidad cada ~19 min), así que el Tier 1 corre como un loop: un
solo job dura ~55 min y repite el scraping cada ~2,5 min adentro
(`run_tier1_loop.py`). El cron (cada 30 min) solo relanza el job y
`concurrency` encola los lanzamientos para que no haya huecos ni solapes.
Cada sitio se consulta una vez por iteración; Fotocasa, que es un portal
grande con protección anti-bots, solo 1 de cada 4 iteraciones (~cada 10
min). `seen_listings.json` se commitea apenas aparece algo nuevo, así que
si el job se corta no se reenvían avisos.

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

Las búsquedas en Brave rotan: hay un pool de ~60 combinaciones de zona +
frase de búsqueda (7 zonas + 5 sub-barrios específicos, x 5 frases
distintas), y cada corrida prueba solo una tanda de 24, no todo el pool.
La próxima corrida sigue donde dejó la anterior (el puntero se guarda en
`discovery_state.json`). Así, en vez de repetir siempre las mismas 21
búsquedas de antes, en ~2-3 corridas ya recorrió todo el pool una vez y
arranca de nuevo, sin pasarse del límite gratis de Brave (2000
consultas/mes: con 24 x 2 corridas/día quedan ~1440/mes, con margen).

## El registro: `agencies.json`

Es la fuente de verdad de qué inmobiliarias conocemos, cuáles están
activas, en qué tier, y notas de por qué se descartó cada una que no pasó
el audit. Discovery y Tier 2 lo leen y lo actualizan solos (se commitea de
vuelta al repo en cada corrida). Las fuentes de Tier 1 también están
anotadas ahí, aunque tienen su propio archivo en `sources/` en vez de usar
el scraper genérico.

## Salud de las fuentes (Tier 1)

Con el mercado flojo, "no llega nada por Telegram" es lo normal, y eso
tapa a las fuentes rotas: antes, si el sitio de una inmobiliaria cambiaba
su HTML y el scraper pasaba a devolver 0, el workflow seguía en verde y
nadie se enteraba. Ahora `health.py` anota por fuente (en `health.json`)
cuántos anuncios en tus zonas trajo cada corrida o si falló, y manda UN
aviso por Telegram cuando una fuente:
- da error en todas las corridas durante ~2h,
- lleva ~12h en cero habiendo traído cosas antes (24h si nunca trajo nada),

y otro aviso cuando se recupera. Los umbrales son por tiempo, no por
cantidad de corridas. Si falla algo en el chequeo de salud, la corrida
principal sigue igual.

## Guardas contra falsos positivos (Tier 2 genérico y JS)

`sources/card_guard.py`: en `generic_agency` y `playwright_agency` se
ignoran links que van a otro dominio (redes sociales, WhatsApp, blogs) y
se corta la búsqueda de precio/m² cuando el contenedor es demasiado grande
para ser una sola tarjeta (>2000 caracteres). Caso que lo motivó:
fincasfinurba.com, donde links de footer heredaban el precio de toda la
página.

## Filtros

- Máximo 1600€/mes, mínimo 50m² (`config.py`)
- Zonas: Eixample (+ Dreta, Esquerra, Fort Pienc, Sant Antoni), Sagrada
  Família, Poblenou (+ Parc i la Llacuna), El Clot (+ Camp de l'Arpa),
  Gràcia, Barceloneta, Vila Olímpica
- Solo alquiler de larga estancia (se descarta lo que dice "temporada",
  "turístico", etc.)
- Se rechaza solo si dice explícitamente "no se admiten mascotas"
- Se rechazan oficinas, despachos, locales, garajes, parkings, trasteros,
  naves y coworkings (`filters.py`): por frases en el texto, por el tipo en
  la URL (directorio, primer o último tramo del slug, ej.
  `.../diputacio-despacho.htm`) y por el título cuando arranca con el tipo
  ("Oficina en..."). Un piso que solo menciona "con garaje" o "con despacho"
  NO se rechaza.

**Filosofía importante** (`filters.py`): un dato que falta (precio, m²,
tipo de alquiler, mascotas) nunca es motivo de descarte por sí solo. Solo
se rechaza cuando hay una señal explícita de que no sirve. Todo lo demás
se manda a Telegram marcado como "desconocido" en vez de perderse.

## Archivos que NO hay que pisar

`seen_listings.json`, `seen_tier2.json`, `seen_broad.json`,
`sitemap_seen.json`, `discovery_state.json`, `health.json` y `agencies.json` los
actualiza el bot solo en cada corrida (con last_scrape, precios ya
vistos, fichas de sitemap ya evaluadas, qué tanda de búsquedas sigue,
etc). Si subís una versión vieja desde tu compu vas a perder ese
historial y capaz te llegan notificaciones repetidas.

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
