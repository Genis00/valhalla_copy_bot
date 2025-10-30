# main.py
# Lectura directa desde t.me/s/<channel> (sin proxy) + reenvío a destinos
# Usa asyncio y python-telegram-bot (async send_message). Logs claros y mensajes limpios.

import os
import asyncio
import json
import logging
import re
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError

# ---------------- CONFIG desde ENV (Railway) ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
SOURCE_CHANNELS = [s.strip() for s in os.getenv("SOURCE_CHANNELS", "binollaofficiall,pocketoptionbotm1").split(",") if s.strip()]
DEST_IDS = [int(x.strip()) for x in os.getenv("DEST_IDS", "-1003202176280,-1003058100855").split(",") if x.strip()]
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))  # segundos entre revisiones
STATE_FILE = "last_seen_web.json"
# ----------------------------------------------------------

# Frases prohibidas (se eliminarán las líneas que las contengan)
BAD_PHRASES = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧",
    "@unstoppable_trader VIP BOT",
    "🚧 BINOLLA FREE 1M 🚧",
    "@pocketoptionai",
    "@pocketoption0o",
    "BINOLLA FREE 1M",
    "MAIN CHANNEL",
    "VIP BOT"
]
BAD_RE = [re.compile(re.escape(p), flags=re.IGNORECASE) for p in BAD_PHRASES]

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("web-copier")

if not BOT_TOKEN:
    log.error("❌ BOT_TOKEN no está configurado en variables de entorno.")
    raise SystemExit(1)

bot = Bot(token=BOT_TOKEN)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {ch: 0 for ch in SOURCE_CHANNELS}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("No se pudo guardar estado: %s", e)


def fetch_posts(channel):
    url = f"https://t.me/s/{channel}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, timeout=15, headers=headers)
        r.raise_for_status()
    except Exception as e:
        log.warning("⚠️ Error leyendo canal %s: %s", channel, e)
        return []

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
        text = text_div.get_text("\n", strip=True) if text_div else ""
        if text:
            posts.append({"id": msg_id, "text": text})
    posts.sort(key=lambda x: x["id"])
    return posts


def clean_text_keep_rest(text):
    # Elimina líneas con frases prohibidas y limpia saltos / espacios
    cleaned_lines = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if any(p.search(line_stripped) for p in BAD_RE):
            continue
        cleaned_lines.append(line_stripped)
    # Unir todo en una sola línea limpia y fluida
    return " ".join(cleaned_lines).strip()


async def send_message_async(chat_id: int, text: str, msg_id=None):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        log.info("✅ Enviado a %s: id_msg=%s preview='%s'", chat_id, msg_id, text[:80].replace("\n", " "))
    except TelegramError as e:
        log.error("❌ Error enviando a %s (id_msg=%s): %s", chat_id, msg_id, e)
    except Exception as e:
        log.error("❌ Error inesperado enviando a %s (id_msg=%s): %s", chat_id, msg_id, e)


async def process_channel(channel, state):
    posts = fetch_posts(channel)
    if not posts:
        log.debug("No posts leídos para %s", channel)
        return

    last = int(state.get(channel, 0))
    new_posts = [p for p in posts if p["id"] > last]
    if not new_posts:
        log.debug("No hay posts nuevos en %s (last=%s)", channel, last)
        return

    for p in new_posts:
        raw = p["text"]
        cleaned = clean_text_keep_rest(raw)
        if not cleaned:
            log.info("🚫 Tras limpiar, no queda contenido útil en %s id=%s", channel, p["id"])
        else:
            for dest in DEST_IDS:
                await send_message_async(dest, cleaned, msg_id=p["id"])
                await asyncio.sleep(0.4)
        state[channel] = p["id"]
        save_state(state)


async def main_loop():
    log.info("🚀 Web-copier iniciado (leerán %s). Intervalo %s s", SOURCE_CHANNELS, CHECK_INTERVAL)
    state = load_state()
    for ch in SOURCE_CHANNELS:
        state.setdefault(ch, 0)

    while True:
        try:
            for ch in SOURCE_CHANNELS:
                await process_channel(ch, state)
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            log.exception("❌ Error general en main loop: %s", e)
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(main_loop())
        loop.run_forever()
