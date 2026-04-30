import os
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
