import os
import pickle
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Buscar .env subiendo directorios, o usar ruta absoluta si está definida en DOTENV_PATH
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)
GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_CALENDAR_TOKEN_FILE = os.getenv('GOOGLE_CALENDAR_TOKEN_FILE', 'token.json')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

# Scopes para Google Calendar
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']


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
        # Raíz del proyecto: src/speech_2_text/speech_2_text/external_integrations/ -> 4 niveles arriba en src/, luego 1 más al workspace
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        token_path = project_root / self.token_file
        credentials_path = project_root / self.credentials_file
        
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


# Definición de función para Google Calendar (function calling)
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

# Exportar funciones disponibles para Calendar
CALENDAR_FUNCTIONS = [
    create_calendar_event_function
]
