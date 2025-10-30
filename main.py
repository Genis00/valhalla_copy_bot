import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

# ==========================
# VARIABLES DE ENTORNO (desde Railway)
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE = os.getenv("SOURCE")
DEST_IDS = os.getenv("DEST_IDS")

# ==========================
# CONFIGURACIÓN DEL BOT
# ==========================
bot = Bot(token=BOT_TOKEN)

print(f"TOKEN DETECTADO: {BOT_TOKEN[:8]}")
print(f"🌐 Leyendo canal público (vía proxy): {SOURCE}")
print(f"📡 Canales destino: {DEST_IDS}")
print("🕓 Esperando nuevos mensajes...\n")

# Convertir lista de destino en enteros
DEST_IDS = [int(x.strip()) for x in DEST_IDS.split(",") if x.strip()]

# ==========================
# FUNCIÓN PARA LEER MENSAJES CON PROXY
# ==========================
PROXY = "https://api.allorigins.win/raw?url="  # proxy gratuito

def obtener_mensajes_proxy(source_username):
    url = f"{PROXY}https://t.me/s/{source_username}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        mensajes = [
            m.get_text("\n", strip=True)
            for m in soup.find_all("div", class_="tgme_widget_message_text")
        ]
        return mensajes[-5:]  # últimos 5 mensajes
    except Exception as e:
        print(f"⚠️ Error leyendo canal: {e}")
        return []

# ==========================
# BUCLE PRINCIPAL
# ==========================
prev = []

while True:
    nuevos = obtener_mensajes_proxy(SOURCE)
    if nuevos:
        nuevos_detectados = [m for m in nuevos if m not in prev]
        if nuevos_detectados:
            for mensaje in nuevos_detectados:
                print(f"🆕 Nuevo mensaje detectado:\n{mensaje}\n────────────────────────────\n")
                for dest in DEST_IDS:
                    try:
                        bot.send_message(chat_id=dest, text=mensaje)
                    except TelegramError as e:
                        print(f"⚠️ Error enviando a {dest}: {e}")
            prev = nuevos
    else:
        print("⚠️ No se pudieron obtener mensajes (canal inaccesible o sin contenido)")
    time.sleep(30)
