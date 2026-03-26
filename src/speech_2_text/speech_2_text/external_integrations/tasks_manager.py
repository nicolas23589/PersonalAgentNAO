"""
Gestor de tareas usando Google Tasks API
"""
import os
import pickle
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Buscar .env subiendo directorios, o usar ruta absoluta si está definida en DOTENV_PATH
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GOOGLE_TASKS_CREDENTIALS_FILE = os.getenv('GOOGLE_TASKS_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_TASKS_TOKEN_FILE = os.getenv('GOOGLE_TASKS_TOKEN_FILE', 'token_tasks.json')
GOOGLE_TASKS_LIST_ID = os.getenv('GOOGLE_TASKS_LIST_ID', '@default')

# Scopes para Google Tasks (se puede combinar con Calendar)
TASKS_SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar'  # Incluir ambos para usar un solo token
]


class GoogleTasksManager:
    """Gestor de tareas de Google Tasks"""
    
    def __init__(self, credentials_file: str = None, token_file: str = None, tasklist_id: str = '@default'):
        self.credentials_file = credentials_file or GOOGLE_TASKS_CREDENTIALS_FILE
        # Usar el mismo token que Calendar para simplificar
        self.token_file = token_file or os.getenv('GOOGLE_CALENDAR_TOKEN_FILE', 'token.json')
        self.tasklist_id = tasklist_id or GOOGLE_TASKS_LIST_ID
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentica con Google Tasks usando OAuth 2.0"""
        creds = None
        
        # Raíz del proyecto: src/speech_2_text/speech_2_text/external_integrations/ -> subir hasta workspace
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
                    str(credentials_path), TASKS_SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Guardar las credenciales para la próxima ejecución
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('tasks', 'v1', credentials=creds)
    
    def create_task(self, title: str, notes: str = None, due: str = None):
        """
        Crea una tarea en Google Tasks
        
        Args:
            title: Título de la tarea
            notes: Notas o descripción adicional
            due: Fecha de vencimiento en formato ISO (YYYY-MM-DD o ISO 8601 completo)
        
        Returns:
            dict con status y detalles de la tarea creada
        """
        try:
            task = {
                "title": title
            }
            
            if notes:
                task["notes"] = notes
            
            if due:
                # Google Tasks solo acepta fechas (no hora), formato RFC 3339
                # Debe ser: YYYY-MM-DDTHH:MM:SS.000Z
                # O simplificado: YYYY-MM-DD (se interpreta como medianoche UTC)
                try:
                    # Normalizar formato
                    if 'T' in due:
                        # Tiene hora, parsear y convertir a RFC 3339
                        if due.endswith('Z'):
                            # Ya está en formato correcto
                            task["due"] = due
                        else:
                            # Añadir Z si no tiene timezone
                            task["due"] = due + 'Z'
                    else:
                        # Solo fecha YYYY-MM-DD, convertir a RFC 3339
                        due_dt = datetime.strptime(due, "%Y-%m-%d")
                        task["due"] = due_dt.isoformat() + 'Z'
                except Exception as e:
                    print(f"Advertencia: formato de fecha inválido ({due}): {e}")
            
            result = self.service.tasks().insert(
                tasklist=self.tasklist_id,
                body=task
            ).execute()
            
            return {
                "status": "success",
                "task_id": result.get("id"),
                "title": result.get("title"),
                "message": f"Tarea '{title}' creada exitosamente"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al crear tarea: {str(e)}"
            }
    
    def list_tasks(self, max_results: int = 10, show_completed: bool = False):
        """
        Lista las tareas pendientes
        
        Args:
            max_results: Número máximo de tareas a devolver
            show_completed: Si incluir tareas completadas
        
        Returns:
            dict con status y lista de tareas
        """
        try:
            results = self.service.tasks().list(
                tasklist=self.tasklist_id,
                maxResults=max_results,
                showCompleted=show_completed
            ).execute()
            
            tasks = results.get('items', [])
            
            task_list = []
            for task in tasks:
                task_list.append({
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "notes": task.get("notes", ""),
                    "due": task.get("due", ""),
                    "status": task.get("status")
                })
            
            return {
                "status": "success",
                "tasks": task_list,
                "total": len(task_list)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al listar tareas: {str(e)}"
            }
    
    def complete_task(self, task_id: str):
        """
        Marca una tarea como completada
        
        Args:
            task_id: ID de la tarea a completar
        
        Returns:
            dict con status
        """
        try:
            task = self.service.tasks().get(
                tasklist=self.tasklist_id,
                task=task_id
            ).execute()
            
            task['status'] = 'completed'
            
            result = self.service.tasks().update(
                tasklist=self.tasklist_id,
                task=task_id,
                body=task
            ).execute()
            
            return {
                "status": "success",
                "message": f"Tarea '{result.get('title')}' marcada como completada"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al completar tarea: {str(e)}"
            }


# Definición de funciones para Google Tasks (function calling)
tasks_create_function = {
    "name": "create_task",
    "description": (
        "Crea una nueva tarea en Google Tasks. "
        "Usa esta función cuando el usuario quiera recordar algo, crear una tarea pendiente, "
        "o anotar algo que debe hacer. Las tareas pueden tener fecha de vencimiento opcional."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Título o descripción breve de la tarea"
            },
            "notes": {
                "type": "string",
                "description": "Notas adicionales o descripción detallada de la tarea"
            },
            "due": {
                "type": "string",
                "description": "Fecha de vencimiento en formato ISO YYYY-MM-DD o ISO 8601 completo (opcional)"
            }
        },
        "required": ["title"]
    }
}

tasks_list_function = {
    "name": "list_tasks",
    "description": (
        "Lista las tareas pendientes del usuario en Google Tasks. "
        "Usa esta función cuando el usuario pregunte qué tareas tiene, "
        "qué debe hacer, o quiera revisar sus pendientes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Número máximo de tareas a mostrar (por defecto 10)",
                "default": 10
            },
            "show_completed": {
                "type": "boolean",
                "description": "Si incluir tareas completadas (por defecto false)",
                "default": False
            }
        }
    }
}

tasks_complete_function = {
    "name": "complete_task",
    "description": (
        "Marca una tarea como completada en Google Tasks. "
        "Usa esta función cuando el usuario indique que terminó una tarea. "
        "Requiere el ID de la tarea, que puedes obtener primero usando list_tasks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "El ID de la tarea a completar"
            }
        },
        "required": ["task_id"]
    }
}

# Exportar funciones disponibles para Google Tasks
TASKS_FUNCTIONS = [
    tasks_create_function,
    tasks_list_function,
    tasks_complete_function
]
