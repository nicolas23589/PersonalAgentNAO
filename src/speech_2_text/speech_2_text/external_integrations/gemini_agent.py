import os
from datetime import datetime
import pytz
from dotenv import load_dotenv, find_dotenv
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    GenerationConfig,
    Content,
    Part
)

# Importar los gestores externos
from .telegram_manager import TelegramSender, TELEGRAM_FUNCTIONS
from .calendar_manager import GoogleCalendarManager, CALENDAR_FUNCTIONS
from .search_manager import WebSearchManager, SEARCH_FUNCTIONS
from .tasks_manager import GoogleTasksManager, TASKS_FUNCTIONS
from .keep_manager import GoogleKeepManager, KEEP_FUNCTIONS

# Buscar .env subiendo directorios, o usar ruta absoluta si está definida en DOTENV_PATH
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

# Configuración de Vertex AI
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'us-central1')  # Región por defecto
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Inicializar Vertex AI
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)

# Arreglo de funciones (tools) para function calling
AVAILABLE_TOOLS = TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS + SEARCH_FUNCTIONS + TASKS_FUNCTIONS + KEEP_FUNCTIONS

SYSTEM_INSTRUCTION = (
    "Eres un asistente personal NAO, un robot humanoide. Tu respuesta será convertida a voz (text-to-speech), "
    "por lo que debes responder de manera natural y conversacional, manteniendo tus respuestas cortas. "
    "Sin embargo, cuando el usuario pida links, URLs, o información que no es apropiada "
    "para comunicar verbalmente (como tablas, listas largas, código, etc.), usa las funciones "
    "disponibles para enviar esa información por Telegram. "
    "Cuando el usuario quiera agendar, programar o recordar algo, usa la función de calendario "
    "para crear el evento. Interpreta fechas relativas como 'mañana', 'la próxima semana', etc. "
    "y conviértelas al formato correcto. Si falta información (como la hora), pregunta o sugiere "
    "valores razonables. Luego, en tu respuesta verbal, confirma la creación del evento de forma natural "
    "sin leer los detalles completos. "
    "Cuando el usuario pida información actualizada, noticias, datos que no conoces, o cualquier cosa "
    "que requiera búsqueda en internet, busca la información en la web. Resume los resultados de forma "
    "breve y natural para comunicar verbalmente, y envía los links completos por Telegram si es apropiado. "
    "Cuando el usuario quiera crear una tarea, recordatorio o pendiente, usa Google Tasks. Las tareas "
    "son para cosas por hacer (to-do), mientras que los eventos de calendario son para citas o reuniones "
    "con hora específica. Si el usuario dice 'recuérdame comprar leche', crea una tarea, no un evento. "
    "Cuando el usuario quiera guardar notas, ideas, información general o crear listas, usa Google Keep. "
    "Keep es ideal para notas rápidas, listas de compras, ideas y cualquier información que no sea una tarea "
    "específica ni un evento con fecha. Por ejemplo: 'guarda esta receta', 'anota esta idea', 'crea una lista de compras'."
)


class GeminiAgent:
    """Agente de Gemini con function calling usando Vertex AI"""

    def __init__(self, telegram_chat_id: str = None, enable_calendar: bool = True, use_native_search: bool = False):
        self.model_name = 'gemini-1.5-pro-002'  # Modelo estable de Vertex AI
        
        # Configurar herramientas (tools) para Vertex AI
        self.tools = []
        
        if use_native_search:
            # Google Search con grounding en Vertex AI
            # Nota: Grounding with Google Search en Vertex AI requiere configuración especial
            print("[Advertencia] Google Search grounding no está completamente implementado en esta versión")
            # Por ahora, usar solo las funciones disponibles
            vertex_functions = self._convert_to_vertex_functions(TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS + TASKS_FUNCTIONS)
            if vertex_functions:
                self.tools.append(Tool(function_declarations=vertex_functions))
        else:
            # Custom Search API con function calling manual
            vertex_functions = self._convert_to_vertex_functions(AVAILABLE_TOOLS)
            if vertex_functions:
                self.tools.append(Tool(function_declarations=vertex_functions))
        
        self.use_native_search = use_native_search
        self.telegram_sender = TelegramSender(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.telegram_chat_id = telegram_chat_id

        # Crear modelo con system instruction
        self.model = GenerativeModel(
            model_name=self.model_name,
            system_instruction=[SYSTEM_INSTRUCTION],
            tools=self.tools if self.tools else None,
            generation_config=GenerationConfig(
                temperature=0.7,
            )
        )
        
        # Iniciar chat persistente
        self.chat = self.model.start_chat()

        # Inicializar Google Calendar Manager
        self.calendar_manager = None
        if enable_calendar:
            try:
                self.calendar_manager = GoogleCalendarManager()
            except Exception as e:
                print(f"Advertencia: No se pudo inicializar Google Calendar: {e}")
                print("La funcionalidad de calendario no estará disponible.")
        
        # Inicializar Web Search Manager
        self.search_manager = None
        try:
            self.search_manager = WebSearchManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Web Search: {e}")
            print("La funcionalidad de búsqueda web no estará disponible.")
        
        # Inicializar Google Tasks Manager
        self.tasks_manager = None
        try:
            self.tasks_manager = GoogleTasksManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Google Tasks: {e}")
            print("La funcionalidad de tareas no estará disponible.")
        
        # Inicializar Google Keep Manager
        self.keep_manager = None
        try:
            self.keep_manager = GoogleKeepManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Google Keep: {e}")
            print("La funcionalidad de Keep no estará disponible.")
            print("Para usar Keep, configura GOOGLE_KEEP_EMAIL y GOOGLE_KEEP_APP_PASSWORD en .env")
    
    def _convert_to_vertex_functions(self, function_declarations):
        """Convierte las declaraciones de función al formato de Vertex AI"""
        vertex_functions = []
        for func_dict in function_declarations:
            try:
                vertex_func = FunctionDeclaration(
                    name=func_dict.get('name'),
                    description=func_dict.get('description'),
                    parameters=func_dict.get('parameters', {})
                )
                vertex_functions.append(vertex_func)
            except Exception as e:
                print(f"[Advertencia] No se pudo convertir función {func_dict.get('name', 'unknown')}: {e}")
        return vertex_functions

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
        
        elif function_name == "web_search":
            if self.search_manager:
                result = self.search_manager.search(
                    query=function_args.get("query"),
                    num_results=function_args.get("num_results", 5)
                )
                return result
            else:
                return {"status": "error", "message": "Web Search not configured"}
        
        elif function_name == "create_task":
            if self.tasks_manager:
                result = self.tasks_manager.create_task(
                    title=function_args.get("title"),
                    notes=function_args.get("notes"),
                    due=function_args.get("due")
                )
                return result
            else:
                return {"status": "error", "message": "Google Tasks not configured"}
        
        elif function_name == "list_tasks":
            if self.tasks_manager:
                result = self.tasks_manager.list_tasks(
                    max_results=function_args.get("max_results", 10),
                    show_completed=function_args.get("show_completed", False)
                )
                return result
            else:
                return {"status": "error", "message": "Google Tasks not configured"}
        
        elif function_name == "complete_task":
            if self.tasks_manager:
                result = self.tasks_manager.complete_task(
                    task_id=function_args.get("task_id")
                )
                return result
            else:
                return {"status": "error", "message": "Google Tasks not configured"}
        
        elif function_name == "create_keep_note":
            if self.keep_manager:
                result = self.keep_manager.create_note(
                    title=function_args.get("title"),
                    content=function_args.get("content"),
                    color=function_args.get("color", "DEFAULT"),
                    pinned=function_args.get("pinned", False)
                )
                return result
            else:
                return {"status": "error", "message": "Google Keep not configured"}
        
        elif function_name == "create_keep_list":
            if self.keep_manager:
                result = self.keep_manager.create_list(
                    title=function_args.get("title"),
                    items=function_args.get("items"),
                    color=function_args.get("color", "DEFAULT"),
                    pinned=function_args.get("pinned", False)
                )
                return result
            else:
                return {"status": "error", "message": "Google Keep not configured"}
        
        elif function_name == "search_keep_notes":
            if self.keep_manager:
                result = self.keep_manager.search_notes(
                    query=function_args.get("query"),
                    max_results=function_args.get("max_results", 5)
                )
                return result
            else:
                return {"status": "error", "message": "Google Keep not configured"}

        # Aquí se pueden agregar más funciones fácilmente
        else:
            return {"status": "error", "message": f"Unknown function: {function_name}"}

    def process_message(self, user_message: str) -> dict:
        """
        Procesa un mensaje del usuario y retorna la respuesta natural y las acciones ejecutadas.

        Returns:
            dict con:
                - 'natural_response': str - Respuesta en lenguaje natural (para TTS)
                - 'function_calls': list - Lista de funciones ejecutadas
                - 'full_response': str - Respuesta completa del modelo
        """
        # Adjuntar fecha y hora actual para que el modelo interprete fechas relativas correctamente
        now = datetime.now(pytz.timezone('America/Bogota'))
        date_context = f"[Fecha y hora actual: {now.strftime('%A %d de %B de %Y, %H:%M')}] "
        full_message = date_context + user_message

        # Log de caracteres enviados
        print(f"[GeminiAgent] Enviando al modelo — caracteres del mensaje: {len(full_message)}")

        # Enviar mensaje usando Vertex AI
        response = self.chat.send_message(full_message)

        function_calls_executed = []

        # Procesar function calls si existen
        # Verificar todas las partes del response
        if response.candidates and len(response.candidates) > 0 and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    print(f"[DEBUG] Function call detectado: {part.function_call.name}")
        
        # Loop para procesar function calls múltiples
        while (response.candidates and 
               len(response.candidates) > 0 and
               response.candidates[0].content and
               response.candidates[0].content.parts and
               len(response.candidates[0].content.parts) > 0 and
               hasattr(response.candidates[0].content.parts[0], 'function_call') and
               response.candidates[0].content.parts[0].function_call):

            function_call = response.candidates[0].content.parts[0].function_call
            function_name = function_call.name
            # Convertir MapComposite a dict
            function_args = dict(function_call.args) if function_call.args else {}

            print(f"[GeminiAgent] Ejecutando función: {function_name}")
            print(f"[GeminiAgent] Argumentos: {function_args}")

            # Ejecutar la función
            function_result = self._execute_function(function_name, function_args)
            function_calls_executed.append({
                "name": function_name,
                "args": function_args,
                "result": function_result
            })

            print(f"[GeminiAgent] Resultado: {function_result.get('status', 'unknown')}")
            if function_result.get('status') == 'error':
                print(f"[GeminiAgent] ❌ Error: {function_result.get('message', 'Sin mensaje')}")

            # Devolver el resultado al modelo dentro del mismo chat usando Vertex AI format
            print(f"[GeminiAgent] Reintentando con function result — función: {function_name}")
            response = self.chat.send_message(
                Part.from_function_response(
                    name=function_name,
                    response=function_result
                )
            )
        
        # Obtener respuesta final (verificar que existe)
        natural_response = ""
        if (response and response.candidates and len(response.candidates) > 0 and 
            response.candidates[0].content and response.text):
            natural_response = response.text
        else:
            natural_response = "Lo siento, no pude generar una respuesta."

        return {
            "natural_response": natural_response,
            "function_calls": function_calls_executed,
            "full_response": natural_response
        }

    def set_telegram_chat_id(self, chat_id: str):
        # TODO el chat debe dejar de ser fijo y pasar a ser una variable con reglas de negocio pre definidas
        self.telegram_chat_id = chat_id


def main():
    TELEGRAM_CHAT_ID = "1242472265"

    # Crear agente
    agent = GeminiAgent(telegram_chat_id=TELEGRAM_CHAT_ID)

    # Ejemplos de conversación
    print("Iniciando Gemini Agent...")
    print("=" * 60)

    response = agent.process_message(
        "Hola"
    )

    print(f"Respuesta para TTS: {response['natural_response']}")
    print("-" * 60)
    print(f"Funciones ejecutadas: {len(response['function_calls'])}")
    for fc in response['function_calls']:
        print(f"  - {fc['name']}: {fc['result']['status']}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    main()
