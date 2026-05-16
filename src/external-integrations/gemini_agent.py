import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Importar los gestores externos
from telegram_manager import TelegramSender, TELEGRAM_FUNCTIONS
from calendar_manager import GoogleCalendarManager, CALENDAR_FUNCTIONS

# Cargar variables del env
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Alistar Gemini
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)

# Arreglo de funciones (tools) para function calling
AVAILABLE_TOOLS = TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS

class GeminiAgent:
    """Agente de Gemini con function calling"""
    
    def __init__(self, telegram_chat_id: str = None, enable_calendar: bool = True):
        self.model_name = 'gemini-2.5-pro'
        self.tools = [types.Tool(function_declarations=AVAILABLE_TOOLS), types.Tool(
        google_search=types.GoogleSearch()
    )]
        self.telegram_sender = TelegramSender(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None
        self.telegram_chat_id = telegram_chat_id
        self.chat_history = []
        
        # Inicializar Google Calendar Manager
        self.calendar_manager = None
        if enable_calendar:
            try:
                self.calendar_manager = GoogleCalendarManager()
            except Exception as e:
                print(f"-") #TODO reemplazar por advertencia de calendar
        
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


def main():
    TELEGRAM_CHAT_ID = "1242472265"
    
    # Crear agente
    agent = GeminiAgent(telegram_chat_id=TELEGRAM_CHAT_ID)
    
    # Ejemplos de conversación
    print("Iniciando Gemini Agent...")
    print("=" * 60)
    
    response = agent.process_message("Hola")

    print(f"Respuesta para TTS: {response['natural_response']}")
    print("-" * 60)
    print(f"Funciones ejecutadas: {len(response['function_calls'])}")
    for fc in response['function_calls']:
        print(f"  - {fc['name']}: {fc['result']['status']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    main()
