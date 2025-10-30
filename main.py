import os
import time
import logging
import requests
from telegram import Bot
from telegram.error import TelegramError

# -----------------------------------------
# CONFIGURACIÓN INICIAL
# -----------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE = os.getenv("SOURCE")  # ejemplo: pocketoption0o
DESTINATIONS = os.getenv("DESTINATIONS", "").split(",")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

if not BOT_TOKEN or not SOURCE or not DESTINATIONS:
    logging.error("❌ Faltan variables de entorno BOT_TOKEN / SOURCE / DESTINATIONS.")
    exit(1)

bot = Bot(token=BOT_TOKEN)

# -----------------------------------------
# BLOQUES DE TEXTO QUE SE ELIMINAN
# -----------------------------------------
TEXTS_TO_REMOVE = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧",
    "🚧 POCKET 1M FREE 🚧",
    "CREATE ACCOUNT",
    "ADD ALL BOT https://t.me/addlist/9ze9Nw05g6UyYTVl",
    "JOIN MAIN CHANNEL @pocketoptionai"
]

# -----------------------------------------
# FUNCIONES DE UTILIDAD
# -----------------------------------------

def clean_text(text):
    """Elimina cualquier línea que contenga una de las frases prohibidas."""
    lines = text.splitlines()
    clean_lines = [
        line for line in lines
        if not any(bad.lower() in line.lower() for bad in TEXTS_TO_REMOVE)
    ]
    return "\n".join(clean_lines).strip()


def get_latest_post(source):
    """Lee el último mensaje público de un canal Telegram a través de t.me/s/..."""
    try:
        url = f"https://t.me/s/{source}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logging.warning(f"⚠️ No se pudo acceder al canal: {source}")
            return None, None

        # Buscar el último mensaje visible (identificador del mensaje y texto)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        messages = soup.select(".tgme_widget_message_text")
        ids = soup.select(".tgme_widget_message")
        if not messages or not ids:
            return None, None

        last_id = ids[-1]["data-post"].split("/")[-1]
        text = messages[-1].get_text("\n")
        return last_id, text
    except Exception as e:
        logging.error(f"❌ Error al obtener mensaje de {source}: {e}")
        return None, None


def send_to_destinations(text, msg_id):
    """Envía el texto a todos los canales destino."""
    for chat_id in DESTINATIONS:
        chat_id = chat_id.strip()
        if not chat_id:
            continue
        try:
            bot.send_message(chat_id=chat_id, text=text)
            preview = text.replace("\n", " ")[:50]
            logging.info(f"✅ Enviado a {chat_id}: id_msg={msg_id} preview='{preview}...'")
        except TelegramError as e:
            logging.error(f"⚠️ Error enviando a {chat_id}: {e}")


# -----------------------------------------
# LOOP PRINCIPAL
# -----------------------------------------
def main():
    logging.info(f"🚀 Iniciado. SOURCE = {SOURCE} | Destinos: {DESTINATIONS} | Intervalo: {CHECK_INTERVAL}")

    last_msg_id = None

    while True:
        msg_id, text = get_latest_post(SOURCE)
        if not msg_id or not text:
            time.sleep(CHECK_INTERVAL)
            continue

        if msg_id != last_msg_id:
            clean_msg = clean_text(text)
            if clean_msg:
                send_to_destinations(clean_msg, msg_id)
                last_msg_id = msg_id
            else:
                logging.info(f"ℹ️ Mensaje {msg_id} limpiado completamente (solo texto bloqueado).")
        else:
            logging.debug("⏳ Sin nuevos mensajes.")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
