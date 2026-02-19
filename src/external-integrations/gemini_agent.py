import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Cargar variables del env
env_path = Path(__file__).parent.parent.parent / '.env'

load_dotenv(dotenv_path=env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

# Alistar Gemini
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)


class TelegramSender:
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
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
        #TODO enviar más info, imágenes, docs, etc.


# Arreglo de de funciones (tools) para function calling
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

# Lista de tools disponibles
AVAILABLE_TOOLS = [
    telegram_send_link_function,
    telegram_send_text_function
]

class GeminiAgent:
    """Agente de Gemini con function calling"""
    
    def __init__(self, telegram_chat_id: str = None):
        self.model_name = 'gemini-3-flash-preview'
        self.tools = [types.Tool(function_declarations=AVAILABLE_TOOLS)]
        self.telegram_sender = TelegramSender(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.telegram_chat_id = telegram_chat_id
        self.chat_history = []
        
    def _execute_function(self, function_name: str, function_args: dict):
        """Ejecuta las funciones llamadas por el modelo"""
        
        if function_name == "send_telegram_link":
            if self.telegram_sender and self.telegram_chat_id:
                result = self.telegram_sender.send_link(
                    chat_id=self.telegram_chat_id,
                    url=function_args.get("url"),
                    description=function_args.get("description", "")
                )
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "message": "Telegram not configured"}
        
        elif function_name == "send_telegram_text":
            if self.telegram_sender and self.telegram_chat_id:
                result = self.telegram_sender.send_message(
                    chat_id=self.telegram_chat_id,
                    text=function_args.get("content"),
                    parse_mode=function_args.get("format", "Markdown")
                )
                return {"status": "success", "result": result}
            else:
                return {"status": "error", "message": "Telegram not configured"}
        
        # Aquí se pueden agregar más funciones fácilmente
        else:
            return {"status": "error", "message": f"Unknown function: {function_name}"}
    
    def process_message(self, user_message: str, system_instruction: str = None) -> dict:
        """
        Procesa un mensaje del usuario y retorna la respuesta natural y las acciones ejecutadas
        
        Returns:
            dict con:
                - 'natural_response': str - Respuesta en lenguaje natural (para TTS)
                - 'function_calls': list - Lista de funciones ejecutadas
                - 'full_response': str - Respuesta completa del modelo
        """
        
        if system_instruction is None:
            system_instruction = (
                "Eres un asistente personal NAO, un robot humanoide. Tu respuesta será convertida a voz (text-to-speech), "
                "por lo que debes responder de manera natural y conversacional, manteniendo tus respuestas cortas. "
                "Sin embargo, cuando el usuario pida links, URLs, o información que no es apropiada "
                "para comunicar verbalmente (como tablas, listas largas, código, etc.), usa las funciones "
                "disponibles para enviar esa información por Telegram. "
                "Luego, en tu respuesta verbal, simplemente menciona que has enviado la información "
                "sin leer los detalles completos."
            )
        
        # Construir el contenido del mensaje
        if not self.chat_history:
            # Primer mensaje incluye instrucciones del sistema
            full_message = f"{system_instruction}\n\nUsuario: {user_message}"
        else:
            full_message = user_message
        
        # Agregar mensaje del usuario al historial
        self.chat_history.append(types.Content(
            role="user",
            parts=[types.Part(text=full_message)]
        ))
        
        # Enviar mensaje
        response = client.models.generate_content(
            model=self.model_name,
            contents=self.chat_history,
            config=types.GenerateContentConfig(
                tools=self.tools,
                temperature=0.7
            )
        )
        
        function_calls_executed = []
        
        # Procesar function calls si existen
        while response.candidates[0].content.parts and \
              hasattr(response.candidates[0].content.parts[0], 'function_call') and \
              response.candidates[0].content.parts[0].function_call:
            
            function_call = response.candidates[0].content.parts[0].function_call
            function_name = function_call.name
            function_args = dict(function_call.args)
                        
            # Ejecutar la función
            function_result = self._execute_function(function_name, function_args)
            function_calls_executed.append({
                "name": function_name,
                "args": function_args,
                "result": function_result
            })
            
            # Agregar la llamada a función al historial
            self.chat_history.append(response.candidates[0].content)
            
            # Enviar el resultado de vuelta al modelo
            self.chat_history.append(types.Content(
                role="user",
                parts=[types.Part(
                    function_response=types.FunctionResponse(
                        name=function_name,
                        response=function_result
                    )
                )]
            ))
            
            response = client.models.generate_content(
                model=self.model_name,
                contents=self.chat_history,
                config=types.GenerateContentConfig(
                    tools=self.tools,
                    temperature=0.7
                )
            )
        
        # Agregar respuesta del modelo al historial
        self.chat_history.append(response.candidates[0].content)
        natural_response = response.text
        
        return {
            "natural_response": natural_response,
            "function_calls": function_calls_executed,
            "full_response": natural_response
        }
    
    def set_telegram_chat_id(self, chat_id: str):
        #TODO el chat debe dejar de ser fijo y pasar a ser una variable con reglas de negocio pre definidas
        self.telegram_chat_id = chat_id


def main(message):
    TELEGRAM_CHAT_ID = "1242472265"
    
    # Crear agente
    agent = GeminiAgent(telegram_chat_id=TELEGRAM_CHAT_ID)
    
    # Ejemplos de conversación
    response = agent.process_message(message)
    print ("---------------------------------------------------------")
    print(f"Respuesta para TTS: {response['natural_response']}")
    print ("---------------------------------------------------------")

    return 0
