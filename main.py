import logging
from telethon import TelegramClient, events
import re
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

api_id = 12345678  # tu API ID
api_hash = "tu_api_hash"
session_name = "valhalla_copy_bot"

# canales origen y destino
origen = [-1003850180555]
destinos = [-1003201762088]

# frases bloqueadas (se eliminarán, no el mensaje completo)
frases_bloqueadas = [
    "Mention time",
    "trade start time",
    "STEP MART",
    "avoid this for low payout",
    "trade can close",
    "check accuracy",
    "join in",
    "public group",
    "secure"
]

client = TelegramClient(session_name, api_id, api_hash)

def limpiar_texto(texto):
    for frase in frases_bloqueadas:
        texto = re.sub(frase, "", texto, flags=re.IGNORECASE)
    # Elimina espacios o saltos sobrantes
    return re.sub(r"\n{2,}", "\n", texto.strip())

@client.on(events.NewMessage(chats=origen))
async def handler(event):
    texto = event.raw_text
    texto_limpio = limpiar_texto(texto)

    if not texto_limpio.strip():
        logging.info(f"Mensaje vacío tras limpieza, ignorado: {texto}")
        return

    for destino in destinos:
        try:
            await client.send_message(destino, texto_limpio)
            logging.info(f"✅ Enviado a {destino}: {texto_limpio[:40]}")
        except Exception as e:
            logging.error(f"Error enviando a {destino}: {e}")

async def main():
    await client.start()
    logging.info("🤖 Bot iniciado y escuchando...")
    await asyncio.Future()

with client:
    client.loop.run_until_complete(main())
