import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# =============================
# 🔧 VARIABLES DE CONFIGURACIÓN
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL = "pocketoption0o"  # sin @
TARGET_CHANNELS = [-1003202176280, -1003058100855]  # lista de IDs destino

# =============================
# 🚀 INICIALIZACIÓN DEL BOT
# =============================
bot = Bot(token=BOT_TOKEN)
print(f"TOKEN DETECTADO: {BOT_TOKEN[:8]}")
print(f"🚀 Bot iniciado — copiando desde: {SOURCE_CHANNEL}")
print(f"📡 Canales destino: {TARGET_CHANNELS}")

# =============================
# ⚙️ FUNCIONES
# =============================
last_message_text = ""

def get_latest_message():
    """Lee el mensaje más reciente del canal público usando t.me/s/<canal>"""
    url = f"https://t.me/s/{SOURCE_CHANNEL}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    all_msgs = soup.find_all("div", {"class": "tgme_widget_message_text"})

    if not all_msgs:
        return None

    # Tomar el texto del último mensaje
    last_msg = all_msgs[-1].get_text("\n", strip=True)
    return last_msg


def send_to_targets(text):
    """Envía un texto a todos los canales destino"""
    for chat_id in TARGET_CHANNELS:
        try:
            bot.send_message(chat_id=chat_id, text=text)
            print(f"✅ Enviado a {chat_id}")
        except Exception as e:
            print(f"⚠️ Error enviando a {chat_id}: {e}")


# =============================
# 🔁 LOOP PRINCIPAL
# =============================
print("🕓 Esperando mensajes nuevos...")
while True:
    try:
        message = get_latest_message()
        if message and message != last_message_text:
            print(f"📩 Nuevo mensaje detectado:\n{message}\n")
            send_to_targets(message)
            last_message_text = message
        time.sleep(10)
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(15)
