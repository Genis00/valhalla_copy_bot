# main.py
# Telegram Message Copier (env vars - listo para Railway)
import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# ---------- CONFIG desde VARIABLES de ENTORNO ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # obligatorio
SOURCE = os.getenv("SOURCE", "pocketoptionbotm1")  # canal origen público (sin @)
DEST_IDS_RAW = os.getenv("DEST_IDS", "")  # ej: -1003202176280,-1003058100855
STATE_FILE = os.getenv("STATE_FILE", "last_seen.json")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # segundos
# ------------------------------------------------------

if not BOT_TOKEN:
    raise SystemExit("ERROR: No BOT_TOKEN set in environment variables.")

# parsear lista de ids
DEST_CHAT_IDS = []
for part in DEST_IDS_RAW.split(","):
    part = part.strip()
    if not part:
        continue
    try:
        DEST_CHAT_IDS.append(int(part))
    except ValueError:
        print("Advertencia: DEST_IDS contiene un valor inválido:", part)

if not DEST_CHAT_IDS:
    raise SystemExit("ERROR: DEST_IDS vacío. Pon los chat_id como variable de entorno.")

bot = Bot(token=BOT_TOKEN)

# Bloques de texto (substrings) a eliminar completamente
TEXTS_TO_REMOVE = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧"
]

# Compilamos un patrón que elimina cualquier línea que contenga esas frases
REMOVE_PATTERNS = [re.compile(re.escape(s), re.IGNORECASE) for s in TEXTS_TO_REMOVE]


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_id": 0}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        print("Warning: no se pudo guardar estado:", e)


def fetch_posts(channel):
    """Obtiene los posts desde la vista pública de telegram t.me/s/channel"""
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
        except Exception:
            continue

        text_div = div.find("div", class_="tgme_widget_message_text")
        if not text_div:
            continue
        # extraemos texto con saltos de línea
        text = text_div.get_text("\n").strip()
        if not text:
            continue
        posts.append({"id": msg_id, "text": text})

    return posts


def clean_text(text):
    """Eliminar líneas que contienen cualquiera de los bloques prohibidos"""
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        skip = False
        for pat in REMOVE_PATTERNS:
            if pat.search(line):
                skip = True
                break
        if not skip:
            cleaned_lines.append(line)
    result = "\n".join([ln.rstrip() for ln in cleaned_lines]).strip()
    return result


def send_to_destinations(message_text):
    """Envía message_text a todos los DEST_CHAT_IDS (maneja errores)."""
    for chat_id in DEST_CHAT_IDS:
        try:
            msg = bot.send_message(chat_id=chat_id, text=message_text)
            print(f"✅ Enviado a {chat_id}: id_msg={getattr(msg, 'message_id', 'n/a')} preview='{message_text[:40]}...'")
        except Exception as e:
            print(f"⚠️ Error enviando a {chat_id}: {e}")


def main_loop():
    state = load_state()
    last_id = state.get("last_id", 0)
    print("🚀 Iniciado. SOURCE =", SOURCE, "| Destinos:", DEST_CHAT_IDS, "| Intervalo:", CHECK_INTERVAL)

    while True:
        try:
            posts = fetch_posts(SOURCE)
            # filtramos solo id > last_id
            new_posts = [p for p in posts if p["id"] > last_id]
            new_posts.sort(key=lambda x: x["id"])
            if not new_posts:
                # print(".", end="", flush=True)
                pass

            for p in new_posts:
                clean_msg = clean_text(p["text"])
                if not clean_msg:
                    print(f"ℹ️ Mensaje {p['id']} limpiado completamente, se ignora.")
                else:
                    send_to_destinations(clean_msg)

                last_id = max(last_id, p["id"])
                state["last_id"] = last_id
                save_state(state)

            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print("❌ Error general en loop:", e)
            time.sleep(15)


if __name__ == "__main__":
    main_loop()
