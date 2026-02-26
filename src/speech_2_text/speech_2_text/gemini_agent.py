import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# Cargar variables del env
env_path = Path(__file__).parent.parent.parent / '.env'

load_dotenv(dotenv_path=env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_CALENDAR_TOKEN_FILE = os.getenv('GOOGLE_CALENDAR_TOKEN_FILE', 'token.json')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

# Scopes para Google Calendar
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

# Alistar Gemini
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)


class GoogleCalendarManager:
    """Gestor de eventos de Google Calendar"""
    
    def __init__(self, credentials_file: str = None, token_file: str = None, calendar_id: str = 'primary'):
        self.credentials_file = credentials_file or GOOGLE_CALENDAR_CREDENTIALS_FILE
        self.token_file = token_file or GOOGLE_CALENDAR_TOKEN_FILE
        self.calendar_id = calendar_id or GOOGLE_CALENDAR_ID
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentica con Google Calendar usando OAuth 2.0"""
        creds = None
        
        # El archivo token.json almacena los tokens de acceso y refresh del usuario
        token_path = Path(__file__).parent.parent.parent / self.token_file
        credentials_path = Path(__file__).parent.parent.parent / self.credentials_file
        
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Si no hay credenciales válidas disponibles, solicita al usuario que inicie sesión
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"No se encontró el archivo de credenciales: {credentials_path}\n"
                        "Por favor, descarga el archivo credentials.json desde Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), CALENDAR_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Guardar las credenciales para la próxima ejecución
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def create_event(self, summary: str, start_time: str, end_time: str = None, 
                    description: str = None, location: str = None, timezone: str = 'America/Bogota'):
        """Crea un evento en Google Calendar
        
        Args:
            summary: Título del evento
            start_time: Fecha y hora de inicio (formato ISO o natural)
            end_time: Fecha y hora de fin (opcional, por defecto 1 hora después)
            description: Descripción del evento
            location: Ubicación del evento
            timezone: Zona horaria (por defecto America/Bogota)
        """
        try:
            # Parsear la fecha de inicio
            start_dt = self._parse_datetime(start_time, timezone)
            
            # Si no hay hora de fin, agregar 1 hora por defecto
            if end_time:
                end_dt = self._parse_datetime(end_time, timezone)
            else:
                end_dt = start_dt + timedelta(hours=1)
            
            # Crear el evento
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': timezone,
                },
            }
            
            if description:
                event['description'] = description
            
            if location:
                event['location'] = location
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            return {
                "status": "success",
                "event_id": created_event.get('id'),
                "event_link": created_event.get('htmlLink'),
                "summary": summary,
                "start": start_dt.strftime('%Y-%m-%d %H:%M'),
                "end": end_dt.strftime('%Y-%m-%d %H:%M')
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _parse_datetime(self, datetime_str: str, timezone: str):
        """Parsea una cadena de fecha/hora a objeto datetime"""
        tz = pytz.timezone(timezone)
        
        # Intentar parsear como ISO
        try:
            dt = datetime.fromisoformat(datetime_str)
            if dt.tzinfo is None:
                dt = tz.localize(dt)
            return dt
        except:
            pass
        
        # Formatos comunes
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                return tz.localize(dt)
            except:
                continue
        
        raise ValueError(f"No se pudo parsear la fecha: {datetime_str}")


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

create_calendar_event_function = {
    "name": "create_calendar_event",
    "description": "Crea un evento en Google Calendar basándose en la información proporcionada por el usuario en lenguaje natural. "
                   "Usa esta función cuando el usuario quiera agendar, programar o recordar algo en su calendario.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Título o resumen del evento (ej: 'Reunión con el equipo', 'Cita médica', 'Cumpleaños de María')"
            },
            "start_time": {
                "type": "string",
                "description": "Fecha y hora de inicio en formato ISO o formato legible (ej: '2026-03-15 14:30', '15/03/2026 14:30', '2026-03-15')"
            },
            "end_time": {
                "type": "string",
                "description": "Fecha y hora de fin (opcional, si no se proporciona se asume 1 hora de duración)"
            },
            "description": {
                "type": "string",
                "description": "Descripción detallada del evento"
            },
            "location": {
                "type": "string",
                "description": "Ubicación del evento (dirección física, link de videollamada, etc.)"
            }
        },
        "required": ["summary", "start_time"]
    }
}

# Lista de tools disponibles
AVAILABLE_TOOLS = [
    telegram_send_link_function,
    telegram_send_text_function,
    create_calendar_event_function
]

class GeminiAgent:
    """Agente de Gemini con function calling"""
    
    def __init__(self, telegram_chat_id: str = None, enable_calendar: bool = True):
        self.model_name = 'gemini-3-flash-preview'
        self.tools = [types.Tool(function_declarations=AVAILABLE_TOOLS)]
        self.telegram_sender = TelegramSender(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.telegram_chat_id = telegram_chat_id
        self.chat_history = []
        
        # Inicializar Google Calendar Manager
        self.calendar_manager = None
        if enable_calendar:
            try:
                self.calendar_manager = GoogleCalendarManager()
            except Exception as e:
                print(f"Advertencia: No se pudo inicializar Google Calendar: {e}")
                print("La funcionalidad de calendario no estará disponible.")
        
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
        
        elif function_name == "create_calendar_event":
            if self.calendar_manager:
                result = self.calendar_manager.create_event(
                    summary=function_args.get("summary"),
                    start_time=function_args.get("start_time"),
                    end_time=function_args.get("end_time"),
                    description=function_args.get("description"),
                    location=function_args.get("location")
                )
                return result
            else:
                return {"status": "error", "message": "Google Calendar not configured"}
        
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
                "Cuando el usuario quiera agendar, programar o recordar algo, usa la función de calendario "
                "para crear el evento. Interpreta fechas relativas como 'mañana', 'la próxima semana', etc. "
                "y conviértelas al formato correcto. Si falta información (como la hora), pregunta o sugiere "
                "valores razonables. Luego, en tu respuesta verbal, confirma la creación del evento de forma natural "
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

    response = agent.process_message("Pon en mi calendario una reunión con el equipo colivri el 28 de febrero de 2026 a la 1pm")

    print(f"Respuesta para TTS: {response['natural_response']}")
    print ("---------------------------------------------------------")

    return 0
