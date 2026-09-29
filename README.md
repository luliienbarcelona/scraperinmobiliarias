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
`"tier": 2` y `"active": true`, usando un scraper genérico
(`sources/generic_agency.py`) en vez de un archivo por sitio. Así se puede
ir sumando inmobiliarias sin escribir código nuevo cada vez.

**Discovery (`main_discovery.py`, 2 veces por día)**
Busca inmobiliarias nuevas con Brave Search (zona por zona, por ejemplo
"inmobiliaria Poblenou Barcelona alquiler"), no pisos sueltos. A cada
dominio nuevo le hace un chequeo automático (¿tiene precio+m2 en el HTML,
menciona alguna de tus zonas?) y si pasa lo suma a Tier 2 directo, sin
esperar aprobación manual. Te avisa por Telegram qué sumó y qué descartó,
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

`seen_listings.json`, `seen_tier2.json`, `seen_broad.json` y
`agencies.json` los actualiza el bot solo en cada corrida (con
last_scrape, precios ya vistos, etc). Si subís una versión vieja desde tu
compu vas a perder ese historial y capaz te llegan notificaciones
repetidas.

## Secrets necesarios (Settings → Secrets → Actions)

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `BRAVE_API_KEY` (solo lo usa discovery)
