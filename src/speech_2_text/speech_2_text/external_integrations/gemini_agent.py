import os
from datetime import datetime
import pytz
from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types

# Importar los gestores externos
from .telegram_manager import TelegramSender, TELEGRAM_FUNCTIONS
from .calendar_manager import GoogleCalendarManager, CALENDAR_FUNCTIONS
from .search_manager import WebSearchManager, SEARCH_FUNCTIONS
from .tasks_manager import GoogleTasksManager, TASKS_FUNCTIONS

# Buscar .env subiendo directorios, o usar ruta absoluta si está definida en DOTENV_PATH
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Alistar Gemini
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)

# Arreglo de funciones (tools) para function calling
AVAILABLE_TOOLS = TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS + SEARCH_FUNCTIONS + TASKS_FUNCTIONS

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
    "con hora específica. Si el usuario dice 'recuérdame comprar leche', crea una tarea, no un evento."
)


class GeminiAgent:
    """Agente de Gemini con function calling"""

    def __init__(self, telegram_chat_id: str = None, enable_calendar: bool = True, use_native_search: bool = False):
        self.model_name = 'gemini-3.1-flash-lite-preview'
        
        # Configurar herramientas (tools)
        # Si use_native_search=True, usa Google Search nativo (grounding)
        # Si use_native_search=False, usa Custom Search API con function calling
        self.tools = []
        
        if use_native_search:
            # Google Search nativo (grounding) - no requiere API Key adicional
            # NO se puede combinar con function calling, así que solo usamos grounding
            self.tools.append(
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            )
            # Con native search, agregamos function calling por separado (sin SEARCH_FUNCTIONS)
            self.tools.append(
                types.Tool(
                    function_declarations=TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS
                )
            )
        else:
            # Custom Search API con function calling manual (incluye todas las funciones)
            self.tools.append(
                types.Tool(
                    function_declarations=AVAILABLE_TOOLS
                )
            )
        
        self.use_native_search = use_native_search
        self.telegram_sender = TelegramSender(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.telegram_chat_id = telegram_chat_id

        # Chat persistente igual que en el script de prueba:
        # la system_instruction va en config, no embebida en el mensaje
        self.chat = client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=self.tools,
                temperature=0.7,
            )
        )

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

        # Enviar mensaje usando el chat (igual que el script de prueba)
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
            function_args = dict(function_call.args)

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

            # Devolver el resultado al modelo dentro del mismo chat
            print(f"[GeminiAgent] Reintentando con function result — función: {function_name}")
            response = self.chat.send_message(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=function_name,
                        response=function_result
                    )
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
