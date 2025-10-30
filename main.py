# ================================================================
# Telegram Message Copier (v2) — Lectura desde web pública (sin BotFather en el canal origen)
# Autor: ChatGPT para Genis Javier
# Descripción:
#   Copia automáticamente mensajes desde un canal público (vía t.me/s)
#   y los reenvía a varios canales privados configurados.
# ================================================================

import requests
from bs4 import BeautifulSoup
import time
import json
import os
from telegram import Bot

# ---------------- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE = os.getenv("SOURCE", "pocketoption0o")  # Canal de origen SIN @
DEST_IDS = os.getenv("DEST_IDS", "-1003202176280,-1003058100855")  # IDs separados por coma
STATE_FILE = "last_seen.json"
CHECK_INTERVAL = 60  # segundos entre revisiones
# ---------------------------------------------------------------------------

# Mensajes o bloques que deben eliminarse del texto original
TEXTS_TO_REMOVE = [
    "🚧 POCKET 1M FREE 🚧",
    "CREATE ACCOUNT",
    "ADD ALL BOT https://t.me/addlist/9ze9Nw05g6UyYTVl",
    "JOIN MAIN CHANNEL @pocketoptionai"
]

# Línea de diagnóstico (para Railway)
print("TOKEN DETECTADO:", BOT_TOKEN[:10] if BOT_TOKEN else "NO DETECTADO")

# Validación del token
if not BOT_TOKEN:
    raise ValueError("❌ No se encontró la variable BOT_TOKEN. Verifica en Railway → Variables.")

# Inicialización del bot
bot = Bot(token=BOT_TOKEN)


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"last_id": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fetch_posts(channel):
    """Obtiene los mensajes del canal público desde t.me/s/<channel>"""
    url = f"https://t.me/s/{channel}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    posts = []
    for div in soup.find_all("div", class_="tgme_widget_message"):
        a = div.find("a", class_="tgme_widget_message_date")
        if not a:
            continue
        href = a.get("href", "")
        try:
            msg_id = int(href.strip("/").split("/")[-1])
        except:
            continue

        text_div = div.find("div", class_="tgme_widget_message_text")
        if not text_div:
            continue
        text = text_div.get_text("\n").strip()
        if not text:
            continue

        posts.append({"id": msg_id, "text": text})

    return posts


def clean_text(text):
    """Elimina las líneas o fragmentos no deseados"""
    for bad in TEXTS_TO_REMOVE:
        text = text.replace(bad, "")
    return text.strip()


def main_loop():
    state = load_state()
    last_id = state.get("last_id", 0)

    dest_list = [int(x) for x in DEST_IDS.split(",") if x.strip()]

    print(f"🚀 Bot iniciado — copiando desde: {SOURCE}")
    print(f"📡 Canales destino: {dest_list}")

    while True:
        try:
            posts = fetch_posts(SOURCE)
            new_posts = [p for p in posts if p["id"] > last_id]
            new_posts.sort(key=lambda x: x["id"])

            for p in new_posts:
                clean_msg = clean_text(p["text"])
                if not clean_msg:
                    continue

                for chat_id in dest_list:
                    try:
                        bot.send_message(chat_id=chat_id, text=clean_msg)
                        print(f"✅ Enviado a {chat_id}: {clean_msg[:40]}...")
                    except Exception as e:
                        print(f"⚠️ Error enviando a {chat_id}: {e}")

                last_id = max(last_id, p["id"])
                state["last_id"] = last_id
                save_state(state)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("❌ Error general:", e)
            time.sleep(15)


if __name__ == "__main__":
    main_loop()
