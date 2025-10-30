import asyncio
import logging
import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode

# Configuración del registro de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
DESTINATION_CHAT_IDS = os.getenv("DESTINATION_CHAT_IDS", "").split(",")

bot = Bot(token=BOT_TOKEN)

# Palabras o frases bloqueadas
BLOCKED_PHRASES = [
    "canal exclusivo", "únete", "unete", "haz clic", "click aquí",
    "suscríbete", "subscribe", "join", "promo", "oferta", "haz parte"
]

# Función para limpiar mensajes
def clean_message(text):
    """Elimina solo las frases bloqueadas, dejando el resto del mensaje intacto."""
    for phrase in BLOCKED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)
    return text.strip()

# Función para copiar mensajes de texto
async def forward_text_message(message):
    text = message.text or message.caption or ""
    if not text.strip():
        return

    cleaned_text = clean_message(text)

    # Saltar si el mensaje quedó vacío
    if not cleaned_text:
        logger.info("Mensaje bloqueado completamente por filtros.")
        return

    for dest_id in DESTINATION_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=dest_id.strip(),
                text=cleaned_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Mensaje reenviado a {dest_id}")
        except TelegramError as e:
            logger.error(f"Error al reenviar mensaje a {dest_id}: {e}")

# Función principal
async def main():
    from telegram.ext import Application, MessageHandler, filters

    app = Application.builder().token(BOT_TOKEN).build()

    async def handle_message(update, context):
        message = update.effective_message
        if message.chat_id == int(SOURCE_CHAT_ID):
            await forward_text_message(message)

    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_message))

    logger.info("Bot iniciado y escuchando mensajes...")
    await app.run_polling()

# Bloque final corregido para Railway / Replit
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
