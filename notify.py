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


def format_listing_message(listing: dict) -> str:
    beds = listing.get("beds")
    beds_txt = f"{beds} hab. · " if beds else ""
    m2 = listing.get("m2")
    m2_txt = f"{m2:.0f}m² · " if m2 else "m² sin confirmar · "
    price = listing.get("price")
    price_txt = f"{price:.0f}€/mes" if price is not None else "precio sin confirmar"
    review_txt = "\n⚠️ Revisar a mano (no se pudo leer precio o m² del snippet)" if listing.get("needs_review") else ""

    return (
        f"🏠 <b>Nuevo piso en {listing['zone']}</b>\n"
        f"{m2_txt}{beds_txt}{price_txt}\n"
        f"Fuente: {listing['source']}\n"
        f"{listing['url']}"
        f"{review_txt}"
    )
