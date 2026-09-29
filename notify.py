# -*- coding: utf-8 -*-
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify] Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID, no se puede notificar.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[notify] Error enviando a Telegram: {e}")


_RENTAL_TYPE_TXT = {
    "long_term": "Larga estancia",
    "short_term": "Corto plazo",
    "unknown": "⚠️ Desconocido",
}

_PETS_TXT = {
    "allowed": "Sí se aceptan",
    "unspecified": "No especificado",
    "rejected": "No se aceptan",
}


def format_listing_message(listing: dict, status: str = "new") -> str:
    """status: "new" (piso nuevo) o "price_drop" (ya lo conocíamos, bajó de precio)."""
    zone = listing.get("zone", "?")
    price = listing.get("price")
    price_txt = f"{price:.0f}€/mes" if price is not None else "⚠️ Desconocido"
    m2 = listing.get("m2")
    m2_txt = f"{m2:.0f}m²" if m2 is not None else "⚠️ Desconocido"
    beds = listing.get("beds")
    rental_type = _RENTAL_TYPE_TXT.get(listing.get("rental_type", "unknown"), "⚠️ Desconocido")
    source = listing.get("source", "?")
    url = listing.get("url", "")

    header = "🚨 <b>NUEVO PISO</b>" if status == "new" else "💸 <b>BAJÓ DE PRECIO</b>"

    lines = [
        header,
        "",
        f"📍 {zone}",
        f"💰 {price_txt}",
        f"📐 {m2_txt}",
    ]
    if beds:
        lines.append(f"🛏 {beds} hab.")
    lines.append(f"🏠 {rental_type}")
    pets_txt = _PETS_TXT.get(listing.get("pets_status", "unspecified"), "No especificado")
    lines.append(f"🐶 Mascotas: {pets_txt}")
    lines.append(f"🏢 {source}")
    lines.append("")
    lines.append(f"🔗 {url}")

    if listing.get("needs_review"):
        lines.append("\n⚠️ Revisar a mano (no se pudo confirmar precio o m² del snippet)")

    return "\n".join(lines)
