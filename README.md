# Scraper de departamentos en Barcelona

Busca pisos en alquiler de larga estancia en Barcelona y te avisa por
Telegram cuando aparece uno nuevo que matchea tus filtros (≤1600€, ≥50m²,
en tus zonas). Corre solo en GitHub Actions (gratis). Tiene dos capas:

## Las dos capas

**Capa 1 — rápida (`main.py`, cada 5 min)**
Scrapea directo Loca Barcelona y Housfy, dos inmobiliarias reales que ya
identificamos como confiables y fáciles de leer. Te avisa casi al instante.

**Capa 2 — amplia (`main_broad.py`, cada 1 hora)**
No se limita a sitios que conocemos: le pregunta a Google, zona por zona,
qué inmobiliarias tienen indexado ("alquiler piso Poblenou Barcelona larga
estancia", etc.) y revisa los resultados nuevos. Así agarra inmobiliarias
chicas o que nunca vimos antes, como la de la Vila Olímpica que contactaste
por mail. Corre cada 1 hora en vez de cada 5 min porque el tier gratis de
Google permite 100 consultas/día.

Cuando Google no muestra el precio o los m² en el resultado (pasa seguido),
el piso se notifica igual, marcado como "revisar a mano", en vez de
descartarlo silenciosamente.

## El límite real que sigue existiendo

Ninguna de las dos capas puede encontrar un piso que **nunca se publicó en
ninguna página web** (por ejemplo, se ofreció solo boca a boca o por mail
directo sin subirlo a ningún sitio). Tampoco aparece hasta que Google indexe
esa página, lo cual a veces tarda días. Eso no tiene solución técnica, es un
límite de la fuente, no del scraper.

## Paso 1: Crear el bot de Telegram

1. Abrí Telegram y buscá **@BotFather**.
2. Mandale `/newbot`, elegí un nombre y un usuario (tiene que terminar en `bot`).
3. Te va a dar un **token** tipo `123456789:ABCdefGhIJKlmNoPQRstuVwXYZ`. Guardalo.
4. Buscá tu bot recién creado por su usuario y mandale cualquier mensaje.
5. Andá a `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` en el navegador.
6. Ahí vas a ver un JSON con `"chat":{"id":123456789,...}`. Ese número es tu
   **chat_id**.

## Paso 2: Crear el repositorio en GitHub

1. Entrá a github.com, creá una cuenta si no tenés.
2. "New repository", ponele un nombre (ej. `apartment-scraper`).
3. **Dejalo público** (así los Actions son gratis e ilimitados).
4. Subí todos los archivos de esta carpeta: "Add file" → "Upload files",
   arrastrando toda la carpeta (incluida la carpeta oculta `.github`).

## Paso 3: Cargar las secrets básicas (necesarias para la Capa 1)

En tu repo: **Settings → Secrets and variables → Actions → New repository secret**.
- `TELEGRAM_BOT_TOKEN`: el token del Paso 1.
- `TELEGRAM_CHAT_ID`: tu chat_id del Paso 1.

Con esto ya podés activar la Capa 1 (ver Paso 6).

## Paso 4: Crear la API de Google Custom Search (para la Capa 2)

Esto habilita la búsqueda amplia. Son dos partes:

**Parte A — la API key:**
1. Andá a [console.cloud.google.com](https://console.cloud.google.com/), creá
   un proyecto (o usá uno existente).
2. Buscá "Custom Search API" en el buscador de servicios y activala.
3. Andá a "Credenciales" → "Crear credenciales" → "Clave de API". Copiala.

**Parte B — el motor de búsqueda:**
1. Andá a [programmablesearchengine.google.com](https://programmablesearchengine.google.com/).
2. "Agregar", elegí "Buscar en toda la web".
3. Creá el motor y copiá su **ID de motor de búsqueda** (Search engine ID / `cx`).

## Paso 5: Cargar las secrets de Google

Mismo lugar que el Paso 3:
- `GOOGLE_API_KEY`: la clave de la Parte A.
- `GOOGLE_CSE_ID`: el ID de la Parte B.

Si no cargás esto, la Capa 1 funciona igual; simplemente la Capa 2 se salta
sola (lo vas a ver en los logs) hasta que la configures.

## Paso 6: Activar los scrapers

1. Pestaña **Actions** de tu repo. Si pregunta si habilitar workflows, sí.
2. Vas a ver dos workflows en la lista: "Scraper rapido" y "Scraper amplio".
3. Entrá a cada uno y click "Run workflow" para probarlo a mano una vez.
4. Revisá los logs de cada corrida para confirmar que encontró anuncios y
   que no hubo errores.

Si todo salió bien, de ahí en más corren solos.

## Cómo ajustar filtros

Todo lo que probablemente quieras cambiar está en `config.py`:
- `MAX_PRICE` y `MIN_M2`.
- `ZONES`: la lista de barrios (alimenta la Capa 2 automáticamente).
- `LOCA_BARCELONA_ZONES` / `HOUSFY_ZONES`: URLs de la Capa 1 por barrio.

## Si querés sumar una inmobiliaria puntual

Si conocés una agencia en particular (como la de la Vila Olímpica) y su sitio
tiene una página de listado propia, pasame la URL y le armo un scraper
dedicado para la Capa 1, así la tenés cubierta cada 5 minutos en vez de
esperar a que la agarre la búsqueda amplia.

## Si algo se rompe

Los sitios cambian de estructura de vez en cuando. Estos scrapers están
armados según cómo se veían los sitios el 26/09/2026. Si en algún momento
dejan de traer resultados que sabés que existen, pasame el link de la zona
que no anda y el log de error, y lo reviso.
