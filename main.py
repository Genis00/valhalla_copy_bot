import os
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import aiohttp
import html
import re

# ======================
# CONFIGURACIÓN
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNELS = os.getenv("SOURCE_CHANNELS", "binollaofficiall,pocketoptionbotm1").split(",")
DEST_IDS = [int(x.strip()) for x in os.getenv("DEST_IDS", "").split(",") if x.strip()]

# Textos prohibidos
BLOCKED_PATTERNS = [
    "🚧 MAIN CHANNEL @pocketoptionai",
    "VIP BOT @pocketoption0o",
    "Register here 🚧",
    "@unstoppable_trader VIP BOT",
    "🚧 BINOLLA FREE 1M 🚧"
]

# ======================
# FUNCIONES
# ======================

async def fetch_latest_messages(channel_username):
    """Obtiene los últimos mensajes de un canal público desde la web de Telegram"""
    url = f"https://t.me/s/{channel_username}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"⚠️ Error al leer {channel_username}: {resp.status}")
                return []

            html_content = await resp.text()
            # Extraer mensajes simples (texto plano) de la web pública
            pattern = re.compile(r'<div class="tgme_widget_message_text js-message_text" dir="auto">(.*?)</div>', re.S)
            messages = pattern.findall(html_content)
            clean_messages = [html.unescape(re.sub(r"<.*?>", "", msg)).strip() for msg in messages]
            return clean_messages[-5:]  # Últimos 5 mensajes


async def send_to_destinations(bot, text):
    """Envía un mensaje a todos los canales destino"""
    for dest in DEST_IDS:
        try:
            await bot.send_message(chat_id=dest, text=text)
            await asyncio.sleep(0.8)
        except TelegramError as e:
            print(f"❌ Error enviando a {dest}: {e}")


async def main():
    print("🚀 Iniciando bot de copia directa (sin proxy)...")
    print(f"📡 Canales origen: {SOURCE_CHANNELS}")
    print(f"🎯 Canales destino: {DEST_IDS}")

    bot = Bot(token=BOT_TOKEN)
    last_messages = {ch: [] for ch in SOURCE_CHANNELS}

    while True:
        for channel in SOURCE_CHANNELS:
            try:
                messages = await fetch_latest_messages(channel)
                if not messages:
                    print(f"⚠️ Sin mensajes en {channel}")
                    continue

                new_msgs = [m for m in messages if m not in last_messages[channel]]
                if new_msgs:
                    for msg in new_msgs:
                        if not any(blocked in msg for blocked in BLOCKED_PATTERNS):
                            await send_to_destinations(bot, msg)
                            print(f"✅ Copiado desde {channel}: {msg[:50]}...")
                        else:
                            print(f"🚫 Filtrado mensaje de {channel}")
                    last_messages[channel] = messages
            except Exception as e:
                print(f"❗ Error procesando {channel}: {e}")

        await asyncio.sleep(30)  # espera entre ciclos

if __name__ == "__main__":
    asyncio.run(main())
