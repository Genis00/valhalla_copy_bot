import os
import time
import requests
from bs4 import BeautifulSoup

# Variables de entorno de Railway (no necesitas cambiarlas)
SOURCE = os.getenv("SOURCE", "pocketoption0o")

def obtener_mensajes_web(source_username):
    """Lee los últimos mensajes del canal público vía web"""
    url = f"https://t.me/s/{source_username}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Telegram usa <div class="tgme_widget_message_text"> para el texto
        mensajes_html = soup.find_all("div", class_="tgme_widget_message_text")
        mensajes = [m.get_text("\n", strip=True) for m in mensajes_html]

        return mensajes[-5:]  # devolvemos los últimos 5 mensajes
    except Exception as e:
        print(f"⚠️ Error al leer desde la web: {e}")
        return []

if __name__ == "__main__":
    print(f"🌐 Leyendo canal público: {SOURCE}")
    print("📡 Esperando y mostrando los últimos mensajes...\n")

    mensajes_previos = []

    while True:
        nuevos = obtener_mensajes_web(SOURCE)

        if nuevos:
            # Compara con los mensajes anteriores
            nuevos_detectados = [m for m in nuevos if m not in mensajes_previos]
            if nuevos_detectados:
                print("📩 Nuevos mensajes detectados:")
                for msg in nuevos_detectados:
                    print("────────────────────────────")
                    print(msg)
                print("────────────────────────────\n")

                mensajes_previos = nuevos
        else:
            print("⚠️ No se pudieron obtener mensajes (canal inaccesible o vacío)")

        time.sleep(20)  # cada 20 segundos
