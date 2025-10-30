import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup

# Configura logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# 🧩 CONFIGURACIÓN
BOT_TOKEN = "8374240235:AAHPdqfC-lbgyQIJ34CDx1fjdttTGnwU8JU"
CANAL_ORIGENES = ["binollaofficiall", "pocketoptionbotm1"]
CANAL_DESTINOS = [-1003202176280, -1003058100855]

# 📦 Almacenamiento temporal de IDs para evitar duplicados
mensajes_enviados = set()

# 🧹 Limpia texto con BeautifulSoup (quita HTML basura)
def limpiar_texto(texto: str) -> str:
    return BeautifulSoup(texto, "html.parser").get_text(separator="\n").strip()

# 📤 Función para reenviar mensaje limpio
async def reenviar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message

    # Evitar duplicados o mensajes vacíos
    if mensaje.message_id in mensajes_enviados or not mensaje.text:
        return
    mensajes_enviados.add(mensaje.message_id)

    # Evitar mensajes de sistema o fijados
    if mensaje.is_automatic_forward or mensaje.pinned_message:
        return
    if mensaje.text.startswith("pinned") or "joined" in mensaje.text.lower():
        return

    texto_limpio = limpiar_texto(mensaje.text)

    # Evita reenviar si no hay texto significativo
    if not texto_limpio or len(texto_limpio) < 3:
        return

    # Envía a todos los canales destino
    for destino in CANAL_DESTINOS:
        try:
            await context.bot.send_message(chat_id=destino, text=texto_limpio)
            logging.info(f"✅ Enviado a {destino}: id_msg={mensaje.message_id} preview={texto_limpio[:80]}")
        except Exception as e:
            logging.error(f"❌ Error enviando a {destino}: {e}")

# 🚀 Inicializa la app
async def main():
    logging.info("🚀 Iniciando bot de copia filtrada...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reenviar))

    await app.start()
    logging.info("📡 Escuchando mensajes...")
    await app.updater.start_polling()
    await asyncio.Event().wait()  # Mantiene el bot activo

if __name__ == "__main__":
    asyncio.run(main())
