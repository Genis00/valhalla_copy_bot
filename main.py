import asyncio
import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ---------------- CONFIGURACIÓN ----------------
TOKEN = "TU_TOKEN_AQUI"

# Canales de origen (nombres sin @)
CHANNELS_ORIGEN = ["binollaofficiall", "pocketoptionbotm1"]

# Canales destino (IDs numéricos)
CHANNELS_DESTINO = [-1003202176280, -1003058100855]

# Frases que deben eliminarse del mensaje
FRASES_PROHIBIDAS = [
    "VIP", "Binolla Premium", "Suscríbete", "canal privado",
    "https://", "t.me/"
]

# ------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------------------------
def limpiar_texto(texto: str) -> str:
    """Elimina solo las frases prohibidas del texto."""
    for frase in FRASES_PROHIBIDAS:
        texto = re.sub(re.escape(frase), "", texto, flags=re.IGNORECASE)
    return texto.strip()

# ------------------------------------------------
async def reenviar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        canal_origen = update.effective_chat.username
        if canal_origen not in CHANNELS_ORIGEN:
            return

        if not update.message or not update.message.text:
            return

        texto_original = update.message.text
        texto_filtrado = limpiar_texto(texto_original)

        if not texto_filtrado:
            logger.info("🚫 Mensaje vacío tras limpiar. No se reenvía.")
            return

        for destino in CHANNELS_DESTINO:
            try:
                await context.bot.send_message(chat_id=destino, text=texto_filtrado)
                logger.info(f"✅ Enviado a {destino}: {texto_filtrado[:60]!r}")
            except Exception as e:
                logger.error(f"❌ Error enviando a {destino}: {e}")

        logger.info(f"📤 Copiado desde {canal_origen}: {texto_filtrado[:80]!r}")

    except Exception as e:
        logger.error(f"⚠️ Error general en reenviar_mensaje: {e}")

# ------------------------------------------------
async def main():
    logger.info("🚀 Iniciando bot de copia directa (sin proxy)...")
    logger.info(f"📡 Canales origen: {CHANNELS_ORIGEN}")
    logger.info(f"🎯 Canales destino: {CHANNELS_DESTINO}")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, reenviar_mensaje))
    await app.run_polling()

# ------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
