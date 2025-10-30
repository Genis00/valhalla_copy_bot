# ================================================================
# Telegram multi-source copier (sin proxy, directo desde t.me/s/)
# Lee canales públicos y reenvía los mensajes filtrados a tus grupos/canales destino
# ================================================================

import os
import time
import json
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

# ---------------------------
# CONFIGURACIÓN PRINCIPAL
# ---------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNELS = os.getenv("SOURCE_CHANNELS", "binollaofficiall,pocketoptionbotm1")
DEST_IDS = os.getenv("DEST_IDS", "-1003202176280,-1003058100855")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "25"))
STATE_FILE = "last_seen.json"

# ---------------------------
# Textos prohibidos que deben eliminarse del mensaje
# ---------------------------
TEXTS_TO_REMOVE = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧",
    "@unstoppable_trader VIP BOT",
    "🚧 BINOLLA FREE 1M 🚧"
]

# ---------------------------
# Inicialización
# ---------------------------
if not BOT_TOKEN:
    raise ValueError("❌ Falta el BOT_TOKEN en las variables de entorno.")

SOURCE_CHANNELS = [s.strip() for s in SOURCE_CHANNELS.split(",") if s.strip()]
DEST_IDS = [int(x.strip()) for x in DEST_IDS.split(",") if x.strip()]
bot = Bot(token=BOT_TOKEN)

print("✅ BOT iniciado")
print("📥 Canales origen:", SOURCE_CHANNELS)
print("📤 Canales destino:", DEST_IDS)
print("⏱ Intervalo de lectura:", CHECK_INTERVAL, "segundos\n")


# ---------------------------
# Funciones de utilidad
# ---------------------------
def load_state():
    """Carga el último ID enviado por canal."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def clean_text(text):
    """Elimina las líneas prohibidas del mensaje."""
    for bad in TEXTS_TO_REMOVE:
        text = text.replace(bad, "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def fetch_posts(channel):
    """Lee directamente desde https://t.me/s/<canal>"""
    url = f"https://t.me/s/{channel}"
    try:
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Error leyendo {channel}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    posts = []

    for div in soup.find_all("div", class_="tgme_widget_message"):
        # obtener id
        a = div.find("a", class_="tgme_widget_message_date")
        if not a:
            continue
        href = a.get("href", "")
        try:
            msg_id = int(href.strip("/").split("/")[-1])
        except:
            continue

        # obtener texto del mensaje
        text_div = div.find("div", class_="tgme_widget_message_text")
        text = text_div.get_text("\n", strip=True) if text_div else ""

        if text:
            posts.append({"id": msg_id, "text": text})

    posts.sort(key=lambda x: x["id"])
    return posts


def send_to_destinations(text):
    """Envía el texto limpio a todos los destinos configurados."""
    for chat_id in DEST_IDS:
        try:
            bot.send_message(chat_id=chat_id, text=text)
            print(f"✅ Enviado a {chat_id}: {text[:60]}...")
        except TelegramError as e:
            print(f"⚠️ Error enviando a {chat_id}: {e}")


# ---------------------------
# Loop principal
# ---------------------------
def main_loop():
    state = load_state()
    for ch in SOURCE_CHANNELS:
        if ch not in state:
            state[ch] = 0

    while True:
        for ch in SOURCE_CHANNELS:
            posts = fetch_posts(ch)
            if not posts:
                continue

            new_posts = [p for p in posts if p["id"] > state.get(ch, 0)]
            if not new_posts:
                continue

            for p in new_posts:
                cleaned = clean_text(p["text"])
                if cleaned:
                    send_to_destinations(cleaned)
                    state[ch] = p["id"]
                    save_state(state)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()
