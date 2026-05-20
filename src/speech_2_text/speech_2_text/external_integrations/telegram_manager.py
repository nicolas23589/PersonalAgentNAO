import os
import threading
import time
import requests
from dotenv import load_dotenv, find_dotenv

# Buscar .env subiendo directorios desde este archivo, o usar ruta absoluta si está definida
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(
    filename='.env',
    raise_error_if_not_found=False,
    usecwd=False
)
if _env_file:
    load_dotenv(dotenv_path=_env_file)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


class TelegramSender:
    """Gestor de mensajes de Telegram"""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._last_chat_id: str = None
        self._last_update_id: int = None
        self._polling_active: bool = False
        self._polling_thread: threading.Thread = None

    @property
    def last_chat_id(self) -> str:
        """Retorna el chat_id de la última persona que escribió al bot."""
        return self._last_chat_id

    def start_polling(self, poll_interval: float = 2.0):
        """
        Inicia un hilo background que hace polling de getUpdates.
        Hace un fetch sincrono inicial para recuperar el ultimo chat_id de inmediato.
        Estrategia: 1) cache en disco, 2) offset=-1 para forzar ultimo update.
        """
        if self._polling_active:
            return

        # 1) Intentar cargar chat_id desde cache en disco
        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".telegram_last_chat_id")
        if os.path.exists(cache_file):
            try:
                cached = open(cache_file).read().strip()
                if cached:
                    self._last_chat_id = cached
                    print(f"[Telegram] chat_id cargado desde cache: {self._last_chat_id}")
            except Exception:
                pass

        # 2) Fetch sincrono con offset=-1 para forzar el ultimo update (aunque ya haya sido leido)
        if not self._last_chat_id:
            try:
                resp = requests.get(
                    f"{self.base_url}/getUpdates",
                    params={"timeout": 0, "limit": 1, "offset": -1},
                    timeout=5
                )
                data = resp.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        self._last_update_id = update["update_id"]
                        msg = (
                            update.get("message")
                            or update.get("edited_message")
                            or update.get("channel_post")
                        )
                        if msg and "chat" in msg:
                            self._last_chat_id = str(msg["chat"]["id"])
                    if self._last_chat_id:
                        print(f"[Telegram] Ultimo chat recuperado via offset=-1: {self._last_chat_id}")
                    else:
                        print("[Telegram] Sin historial de chats — escribe al bot para activarlo.")
                else:
                    print("[Telegram] Sin updates disponibles — escribe al bot para activarlo.")
            except Exception as e:
                print(f"[Telegram] No se pudo hacer fetch inicial: {e}")

        # Guardar chat_id en cache si ya lo tenemos
        if self._last_chat_id:
            try:
                open(cache_file, "w").write(self._last_chat_id)
            except Exception:
                pass

        self._polling_active = True
        self._polling_thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True
        )
        self._polling_thread.start()
        print("[Telegram] Polling iniciado — el bot detectara el ultimo chat activo.")

    def stop_polling(self):
        """Detiene el polling de Telegram."""
        self._polling_active = False

    def _poll_loop(self, interval: float):
        """Loop interno de polling de getUpdates."""
        while self._polling_active:
            try:
                params = {"timeout": 0, "limit": 10}
                if self._last_update_id is not None:
                    params["offset"] = self._last_update_id + 1

                resp = requests.get(
                    f"{self.base_url}/getUpdates",
                    params=params,
                    timeout=5
                )
                data = resp.json()
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        self._last_update_id = update["update_id"]
                        msg = (
                            update.get("message")
                            or update.get("edited_message")
                            or update.get("channel_post")
                        )
                        if msg and "chat" in msg:
                            chat_id = str(msg["chat"]["id"])
                            if chat_id != self._last_chat_id:
                                print(f"[Telegram] Nuevo chat_id activo: {chat_id}")
                            self._last_chat_id = chat_id
            except Exception as e:
                print(f"[Telegram] Error en polling: {e}")
            time.sleep(interval)

    def send_message(self, chat_id: str, text: str, parse_mode: str = "Markdown"):
        """Envía un mensaje de texto por Telegram"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        response = requests.post(url, json=data)
        return response.json()
    
    def send_link(self, chat_id: str, url: str, description: str = ""):
        """Envía un link por Telegram"""
        if description:
            text = f"[{description}]({url})"
        else:
            text = url
        return self.send_message(chat_id, text)

    def send_photo_url(self, chat_id: str, photo_url: str, caption: str = ""):
        """Envía una imagen por URL a Telegram (Static Maps, Street View, etc.)"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=data)
        return response.json()


# Definición de funciones para Telegram (function calling)
telegram_send_link_function = {
    "name": "send_telegram_link",
    "description": "Envía un link u otro contenido no apropiado para text-to-speech por Telegram. "
                   "Usa esta función cuando el usuario pida links, URLs, direcciones web, o cualquier "
                   "información que no sea adecuada para comunicar verbalmente.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "La URL o link que se debe enviar"
            },
            "description": {
                "type": "string",
                "description": "Una breve descripción del link"
            }
        },
        "required": ["url"]
    }
}

telegram_send_text_function = {
    "name": "send_telegram_text",
    "description": "Envía información estructurada o texto complementario por Telegram que no es apropiado "
                   "para text-to-speech (tablas, listas largas, códigos, etc.)",
    "parameters": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "El contenido a enviar por Telegram"
            },
            "format": {
                "type": "string",
                "description": "El formato del contenido (Markdown, HTML, plain)",
                "enum": ["Markdown", "HTML", "plain"]
            }
        },
        "required": ["content"]
    }
}

# Exportar funciones disponibles para Telegram
TELEGRAM_FUNCTIONS = [
    telegram_send_link_function,
    telegram_send_text_function
]
