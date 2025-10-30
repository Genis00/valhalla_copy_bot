# -*- coding: utf-8 -*-
"""
Telegram Message Copier (sin sesión local)
Autor: ChatGPT para Genis Javier
Descripción:
  Copia mensajes de canales públicos vía web t.me/s y reenvía a canales destino,
  eliminando únicamente las frases/fragmentos prohibidos del texto (sin borrar
  el resto del mensaje).
"""

import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# ------------------- Config desde environment (Railway) -------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SOURCE_CHANNELS_ENV = os.environ.get("SOURCE_CHANNELS", "pocketoptionbotm1")  # comma separated
DEST_IDS_ENV = os.environ.get("DEST_IDS", "")  # comma separated chat ids

SOURCE_CHANNELS = [s.strip() for s in SOURCE_CHANNELS_ENV.split(",") if s.strip()]
try:
    DEST_CHAT_IDS = [int(x.strip()) for x in DEST_IDS_ENV.split(",") if x.strip()]
except:
    DEST_CHAT_IDS = []

STATE_FILE = "last_seen.json"
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))  # segundos entre revisiones
# --------------------------------------------------------------------------

# Frases / fragmentos prohibidos (case-insensitive)
# Añade aquí cualquier otro fragmento que NO quieras que salga en los mensajes reenviados.
BAD_PHRASES = [
    "🚧 main channel",
    "@pocketoptionai",
    "vip bot",
    "@pocketoption0o",
    "register here",
    "@unstoppable_trader",
    "binolla free 1m",
    "🚧 binolla free",
    "create account",
    "join our vip group",
    "add all bot",
]

# compile regex variants for faster replacement (case-insensitive)
BAD_RE_PATTERNS = [re.compile(re.escape(p), flags=re.IGNORECASE) for p in BAD_PHRASES]

# small helper to clean leftover multiple spaces and blank lines
MULTISPACE_RE = re.compile(r"[ \t]{2,}")
MULTIBLANK_RE = re.compile(r"\n{2,}")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        # last_id por canal: { "pocketoptionbotm1": 123, "binollaofficiall": 456 }
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("❌ Error guardando estado:", e)


def fetch_posts_from_web(channel):
    """
    Lee la página pública t.me/s/<channel> y devuelve lista de posts
    como dicts: {"id": int, "text": str}
    """
    url = f"https://t.me/s/{channel}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ Error leyendo canal {channel}: {e}")
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
        if not text_div:
            continue
        # get_text with newlines, keep structure
        text = text_div.get_text("\n").strip()
        if not text:
            continue
        posts.append({"id": msg_id, "text": text})

    return posts


def clean_prohibited_fragments(text):
    """
    Elimina solo las frases / fragmentos prohibidos del texto (sin borrar el resto).
    - Reemplaza ocurrencias de BAD_PHRASES por cadena vacía.
    - Normaliza espacios y líneas vacías.
    """
    original = text

    # Reemplazar cada patrón por vacío
    for pat in BAD_RE_PATTERNS:
        text = pat.sub("", text)

    # Además quitar enlaces obvios si están en la misma línea y están en la lista de frases
    # (no activo por defecto) - dejamos URLs intactas por petición del usuario.

    # Limpiar espacios repetidos
    text = MULTISPACE_RE.sub(" ", text)
    # Quitar espacios al inicio / final de cada línea
    lines = [ln.strip() for ln in text.splitlines()]
    # Eliminar líneas vacías
    lines = [ln for ln in lines if ln != ""]
    text = "\n".join(lines).strip()
    # Colapsar múltiples saltos de línea
    text = MULTIBLANK_RE.sub("\n", text)

    return text


def send_to_destinations(text, src_channel, msg_id=None):
    if not bot:
        print("❌ Bot no configurado (BOT_TOKEN vacío).")
        return

    for chat_id in DEST_CHAT_IDS:
        try:
            bot.send_message(chat_id=chat_id, text=text)
            print(f"✅ Enviado a {chat_id}: id_msg={msg_id} preview='{text[:50]}...'")
        except Exception as e:
            # Mostrar solo error y no abortar
            print(f"❌ Error enviando a {chat_id}: {e}")


def process_new_posts(channel, posts, last_id_map):
    """
    Para cada nuevo post mayor que last_id_map[channel], limpialo y reenviar.
    Devuelve el nuevo last_id para el canal.
    """
    if not posts:
        return last_id_map.get(channel, 0)

    posts_sorted = sorted(posts, key=lambda x: x["id"])
    last_id = last_id_map.get(channel, 0)

    for p in posts_sorted:
        if p["id"] <= last_id:
            continue

        raw_text = p["text"]
        cleaned_text = clean_prohibited_fragments(raw_text)

        if not cleaned_text:
            # Si tras limpiar solo quedan fragmentos prohibidos -> no reenviamos
            print(f"🚫 Después de limpiar, no queda contenido útil en {channel} (msg {p['id']})")
        else:
            # Reenvía el mensaje limpio
            send_to_destinations(cleaned_text, channel, msg_id=p["id"])
            print(f"✅ Copiado desde {channel}: {cleaned_text[:80]}")

        last_id = max(last_id, p["id"])
        last_id_map[channel] = last_id
        save_state(last_id_map)

    return last_id


def main_loop():
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN no está configurado en las variables de entorno.")
        return

    if not SOURCE_CHANNELS:
        print("❌ ERROR: SOURCE_CHANNELS no configurado.")
        return

    if not DEST_CHAT_IDS:
        print("❌ ERROR: DEST_IDS no configurado o vacío.")
        return

    print("🚀 Iniciando bot de copia directa (sin proxy)...")
    print("📡 Canales origen:", SOURCE_CHANNELS)
    print("🎯 Canales destino:", DEST_CHAT_IDS)

    state = load_state()

    # Asegurar la clave para cada canal
    for ch in SOURCE_CHANNELS:
        if ch not in state:
            state[ch] = 0

    while True:
        try:
            for ch in SOURCE_CHANNELS:
                posts = fetch_posts_from_web(ch)
                if not posts:
                    # No posts o error al leer
                    # (no mostramos "filtrado" aquí porque puede haber simplemente no posts)
                    print(f"⚠️ No se pudieron obtener mensajes (canal inaccesible o sin contenido): {ch}")
                    continue

                # Procesar solo los nuevos
                process_new_posts(ch, posts, state)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("🛑 Interrumpido por teclado, guardando estado...")
            save_state(state)
            break
        except Exception as e:
            print("❌ Error general en loop:", e)
            time.sleep(10)


if __name__ == "__main__":
    main_loop()
