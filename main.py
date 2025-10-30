# ================================================================
# Telegram Message Copier (sin sesión local)
# Autor: ChatGPT para Genis Javier
# Descripción:
#   Copia automáticamente mensajes de texto desde un canal público
#   y los reenvía a varios canales privados cada 60 segundos.
# ================================================================

import requests
from bs4 import BeautifulSoup
import time
import json
from telegram import Bot

# ---------------- CONFIGURACIÓN ----------------
BOT_TOKEN = "TU_TOKEN_AQUI"  # ⚠️ Reemplázalo por el token del BotFather
SOURCE = "pocketoption0o"  # canal de origen (sin @)
DEST_CHAT_IDS = [-1003202176280, -1003058100855]  # canales privados de salida
STATE_FILE = "last_seen.json"
CHECK_INTERVAL = 60  # segundos entre revisiones
# ------------------------------------------------


# Palabras o bloques de texto que deben eliminarse
TEXTS_TO_REMOVE = [
    "🚧 POCKET 1M FREE 🚧\nCREATE ACCOUNT\nADD ALL BOT https://t.me/addlist/9ze9Nw05g6UyYTVl\nJOIN MAIN CHANNEL @pocketoptionai"
]

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
    """Obtiene los mensajes del canal público desde la web t.me/s"""
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
    """Elimina las líneas no deseadas"""
    for bad in TEXTS_TO_REMOVE:
        text = text.replace(bad, "")
    return text.strip()


def main_loop():
    state = load_state()
    last_id = state.get("last_id", 0)

    while True:
        try:
            posts = fetch_posts(SOURCE)
            new_posts = [p for p in posts if p["id"] > last_id]
            new_posts.sort(key=lambda x: x["id"])

            for p in new_posts:
                clean_msg = clean_text(p["text"])
                if not clean_msg:
                    continue  # ignorar vacíos

                # Enviar a todos los canales de salida
                for chat_id in DEST_CHAT_IDS:
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
    print("🚀 Bot iniciado — copiando desde:", SOURCE)
    main_loop()
