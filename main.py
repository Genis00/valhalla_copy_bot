import asyncio
import logging
import os
import re
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, MessageHandler, filters

# ===== CONFIGURACIÓN =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
DESTINATION_CHAT_IDS = [x.strip() for x in os.getenv("DESTINATION_CHAT_IDS", "").split(",") if x.strip()]

bot = Bot(token=BOT_TOKEN)

BLOCKED_PHRASES = [
    "canal exclusivo", "únete", "unete", "haz clic", "click aquí",
    "suscríbete", "subscribe", "join", "promo", "oferta", "haz parte"
]


def clean_message(text: str) -> str:
    for phrase in BLOCKED_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)
    return text.strip()


async def forward_text_message(message):
    text = message.text or message.caption or ""
    if not text.strip():
        return

    cleaned_text = clean_message(text)
    if not cleaned_text:
        logger.info("Mensaje filtrado completamente.")
        return

    for dest_id in DESTINATION_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=dest_id,
                text=cleaned_text,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Enviado a {dest_id}")
        except TelegramError as e:
            logger.error(f"Error al reenviar mensaje a {dest_id}: {e}")


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    async def handle_message(update, context):
        message = update.effective_message
        if str(message.chat_id) == str(SOURCE_CHAT_ID):
            await forward_text_message(message)

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("🚀 Bot activo y escuchando mensajes...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # mantiene vivo el bot sin cerrar loop


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Si Railway o Replit ya tienen loop activo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(main())
        loop.run_forever()
