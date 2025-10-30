import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# =====================
# VARIABLES
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DESTINATION_CHANNELS = [int(x) for x in os.getenv("DESTINATION_CHANNELS", "").split(",") if x]
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "pocketoption0o")
EXCLUDE_PART = "🚧 POCKET 1M FREE 🚧 CREATE ACCOUNT ADD ALL BOT https://t.me/addlist/9ze9Nw05g6UyYTVl JOIN MAIN CHANNEL @pocketoptionai"

bot = Bot(token=BOT_TOKEN)

print(f"TOKEN DETECTADO: {BOT_TOKEN[:8]}")
print(f"📡 Canales destino: {DESTINATION_CHANNELS}")
print(f"🌐 Leyendo canal público (vía proxy): {SOURCE_CHANNEL}")

last_message = None

# =====================
# FUNCIÓN PRINCIPAL
# =====================
def get_latest_message():
    """Lee el último mensaje público del canal usando proxy Jina AI"""
    try:
        url = f"https://r.jina.ai/https://t.me/s/{SOURCE_CHANNEL}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        texts = soup.get_text(separator="\n").split("\n")
        texts = [t.strip() for t in texts if t.strip()]
        if not texts:
            return None
        return texts[-1]
    except Exception as e:
        print(f"⚠️ Error leyendo canal: {e}")
        return None

# =====================
# LOOP PRINCIPAL
# =====================
print("🕓 Esperando nuevos mensajes...\n")
while True:
    message = get_latest_message()
    if message and message != last_message:
        if EXCLUDE_PART in message:
            message = message.replace(EXCLUDE_PART, "").strip()
        for dest in DESTINATION_CHANNELS:
            try:
                bot.send_message(chat_id=dest, text=message)
                print(f"✅ Mensaje reenviado a {dest}: {message[:50]}...")
            except Exception as e:
                print(f"⚠️ Error enviando a {dest}: {e}")
        last_message = message
    time.sleep(10)
