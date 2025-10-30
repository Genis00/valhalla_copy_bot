# main.py
# Telegram Message Copier — lectura directa desde t.me/s (sin proxy)
# Autor: ChatGPT para Genis Javier
# Versión: 2025-10-30

import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------ CONFIG desde ENV ------------------
# En Railway: BOT_TOKEN, DEST_IDS (coma-separated), SOURCE_CHANNELS (coma-separated)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DEST_IDS_RAW = os.environ.get("DEST_IDS", "-1003202176280,-1003058100855")
SOURCE_CHANNELS_RAW = os.environ.get("SOURCE_CHANNELS", "binollaofficiall,pocketoptionbotm1")
STATE_FILE = os.environ.get("STATE_FILE", "last_seen.json")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "6"))  # segundos entre comprobaciones (usa 6-60 según prefieras)
# ------------------------------------------------------

DEST_CHAT_IDS = [int(x.strip()) for x in DEST_IDS_RAW.split(",") if x.strip()]
SOURCE_CHANNELS = [s.strip() for s in SOURCE_CHANNELS_RAW.split(",") if s.strip()]

# Frases / bloques totalmente prohibidos (se eliminarán si aparecen dentro del mensaje)
TEXTS_TO_REMOVE = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧",
    "@unstoppable_trader VIP BOT",
    "🚧 BINOLLA FREE 1M 🚧",
]

# Compila patrón para eliminar todas las ocurrencias (case sensitive para emojis/handles, pero haremos tolerant)
REMOVE_PATTERNS = [re.escape(t) for t in TEXTS_TO_REMOVE]
combined_re = re.compile("|".join(REMOVE_PATTERNS))

# Token check
if not BOT_TOKEN:
    logging.error("ERROR: BOT_TOKEN no está configurado. Ponlo en las variables de Railway (BOT_TOKEN).")
    raise SystemExit(1)

bot = Bot(token=BOT_TOKEN)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.warning("No pude leer state file: %s", e)
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logging.warning("Error guardando state: %s", e)


def fetch_posts_from_channel(channel):
    """Lee los últimos posts públicos de https://t.me/s/<channel> y devuelve lista de dict {id,text}"""
    url = f"https://t.me/s/{channel}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logging.warning("⚠️ Error leyendo canal %s: %s", channel, e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    posts = []

    # búsqueda de mensajes en la vista pública
    for div in soup.find_all("div", class_="tgme_widget_message"):
        # fecha/href con id
        a = div.find("a", class_="tgme_widget_message_date")
        if not a:
            continue
        href = a.get("href", "")
        try:
            msg_id = int(href.strip("/").split("/")[-1])
        except:
            continue

        # texto
        text_div = div.find("div", class_="tgme_widget_message_text")
        if not text_div:
            continue

        # Obtén texto respetando saltos de línea
        text = text_div.get_text("\n").strip()
        if not text:
            continue

        posts.append({"id": msg_id, "text": text})

    return posts


def clean_text_keep_rest(text):
    """
    Elimina SOLO las frases definidas en TEXTS_TO_REMOVE (pueden aparecer en cualquier parte).
    - Si una línea queda vacía tras eliminar, la borra.
    - Colapsa múltiples saltos de línea en uno.
    """
    # Reemplaza todas las ocurrencias exactas definidas
    new = combined_re.sub("", text)

    # Algunas variantes: si aparecen las frases en mayúsc/minúsc (handles suelen case-sensitive),
    # podemos también eliminar versiones sin emojis si existieran:
    # (Añado una pasada 'suave' por substrings sin emojis)
    extra_to_remove = [
        "@unstoppable_trader VIP BOT",
        "BINOLLA FREE 1M",
        "VIP BOT @pocketoption0o",
        "MAIN CHANNEL @pocketoptionai",
    ]
    for sub in extra_to_remove:
        new = re.sub(re.escape(sub), "", new, flags=re.IGNORECASE)

    # Limpia líneas que queden vacías y colapsa saltos de línea
    lines = [ln.rstrip() for ln in new.splitlines()]
    lines = [ln for ln in lines if ln.strip() != ""]
    cleaned = "\n".join(lines).strip()

    # Elimina espacios dobles
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

    return cleaned


def send_to_destinations(text, src_channel, msg_id):
    for chat_id in DEST_CHAT_IDS:
        try:
            bot.send_message(chat_id=chat_id, text=text)
            logging.info("✅ Enviado a %s: id_msg=%s preview=%s", chat_id, msg_id, text[:60].replace("\n", " "))
        except Exception as e:
            logging.warning("❌ Error enviando a %s: %s", chat_id, e)


def main_loop():
    state = load_state()
    # estado por canal: last_id stored as str(key=channel)
    last_ids = state.get("last_ids", {})

    logging.info("🚀 Iniciando bot de copia directa (sin proxy)...")
    logging.info("📡 Canales origen: %s", SOURCE_CHANNELS)
    logging.info("🎯 Canales destino: %s", DEST_CHAT_IDS)
    logging.info("⏱ Intervalo: %s segundos", CHECK_INTERVAL)

    while True:
        try:
            for ch in SOURCE_CHANNELS:
                try:
                    posts = fetch_posts_from_channel(ch)
                except Exception as e:
                    logging.warning("Error fetch posts %s: %s", ch, e)
                    posts = []

                if not posts:
                    logging.debug("⚠️ No se encontraron posts para %s (puede estar vacío o inaccesible)", ch)
                    continue

                last_id = int(last_ids.get(ch, 0))
                # Filtrar nuevos
                new_posts = [p for p in posts if p["id"] > last_id]
                new_posts.sort(key=lambda x: x["id"])

                if not new_posts:
                    logging.debug("No hay posts nuevos en %s (last_id=%s)", ch, last_id)
                    continue

                for p in new_posts:
                    cleaned = clean_text_keep_rest(p["text"])
                    if not cleaned:
                        logging.debug("🚫 Mensaje filtrado completamente de %s id=%s (quedó vacío tras limpiar)", ch, p["id"])
                        last_id = max(last_id, p["id"])
                        last_ids[ch] = last_id
                        continue

                    # Enviar
                    send_to_destinations(cleaned, ch, p["id"])

                    last_id = max(last_id, p["id"])
                    last_ids[ch] = last_id

                # guarda estado tras procesar cada canal
                state["last_ids"] = last_ids
                save_state(state)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Saliendo por KeyboardInterrupt")
            break
        except Exception as e:
            logging.exception("❌ Error general en main loop: %s", e)
            time.sleep(10)


if __name__ == "__main__":
    main_loop()
