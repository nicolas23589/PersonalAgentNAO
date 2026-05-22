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
from .notion_manager import NotionManager, NOTION_FUNCTIONS
from .maps_manager import MapsManager, MAPS_FUNCTIONS
from .sheets_manager import GoogleSheetsManager, SHEETS_FUNCTIONS
from .gmail_manager import GmailManager, GMAIL_FUNCTIONS

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
AVAILABLE_TOOLS = TELEGRAM_FUNCTIONS + CALENDAR_FUNCTIONS + SEARCH_FUNCTIONS + TASKS_FUNCTIONS + NOTION_FUNCTIONS + MAPS_FUNCTIONS + SHEETS_FUNCTIONS + GMAIL_FUNCTIONS

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
    "Cuando el usuario pregunte qué tiene agendado, qué hay esta semana, si tiene algo pendiente en el "
    "calendario, o busque un evento específico, usa list_calendar_events o search_calendar_events según "
    "corresponda. Resume verbalmente los eventos más relevantes (máximo 3-4) de forma natural y envía "
    "la lista completa por Telegram cuando haya más de uno. "
    "Cuando el usuario pida información actualizada, noticias, datos que no conoces, o cualquier cosa "
    "que requiera búsqueda en internet, busca la información en la web. Resume los resultados de forma "
    "breve y natural para comunicar verbalmente, y envía los links completos por Telegram si es apropiado. "
    "Cuando el usuario quiera crear una tarea, recordatorio o pendiente, usa Google Tasks. Las tareas "
    "son para cosas por hacer (to-do), mientras que los eventos de calendario son para citas o reuniones "
    "con hora específica. Si el usuario dice 'recuérdame comprar leche', crea una tarea, no un evento. "
    "Cuando el usuario quiera guardar notas, ideas, información general o crear listas, usa Notion. "
    "Notion es ideal para notas rápidas, listas de compras, ideas y cualquier información que no sea una tarea "
    "específica ni un evento con fecha. Por ejemplo: 'guarda esta receta', 'anota esta idea', 'crea una lista de compras'. "
    "Cuando el usuario pregunte sobre mapas, tráfico, rutas, lugares, distancias, 'cómo llegar', 'qué hay cerca', "
    "o quiera ver un lugar visualmente, usa las funciones de Google Maps. "
    "Para respuestas verbales resume el resultado (tiempo de viaje, nombre del lugar, estado del tráfico). "
    "Siempre envía por Telegram los mapas estáticos, Street Views, y links de rutas para que el usuario los abra. "
    "Si la ubicación del usuario está disponible en el contexto, úsala como origen o referencia por defecto. "
    "Cuando el usuario pregunte por datos en sus hojas de cálculo, presupuestos, registros, listas en Google Sheets, "
    "o quiera crear/editar un documento de Sheets, usa las funciones de Google Sheets. "
    "Si el usuario menciona el nombre de una hoja de forma parcial o aproximada (por ejemplo: 'la hoja de notas', "
    "'el presupuesto del semestre', 'mis gastos'), usa find_spreadsheet primero para encontrar el documento exacto, "
    "luego usa su nombre o ID en las demás funciones (read_spreadsheet, write_to_spreadsheet, etc.). "
    "Para respuestas verbales resume brevemente lo que encontraste o lo que hiciste (p.ej. 'Encontré 3 filas con ese dato'). "
    "Envía tablas completas o links del documento por Telegram para que el usuario los consulte. "
    "Cuando el usuario quiera enviar un correo electrónico, redactar un email o contactar a alguien por correo, "
    "usa send_email para enviarlo desde la cuenta del usuario. Redacta el cuerpo de forma natural y profesional. "
    "Confirma verbalmente el envío de forma breve (p. ej. 'Listo, te envié el correo a Ana'). "
    "Cuando el usuario pregunte por correos recibidos, busque información en sus emails, o quiera saber si llegó "
    "algo de alguien o sobre un tema, usa search_emails o list_inbox según corresponda. "
    "Resume los resultados verbalmente de forma concisa y envía el detalle completo por Telegram cuando haya mucho texto."
)


class GeminiAgent:
    """Agente de Gemini con function calling usando Vertex AI"""

    def __init__(self, telegram_chat_id: str = None, enable_calendar: bool = True, use_native_search: bool = False):
        self.model_name = 'gemini-2.5-pro'  # Modelo estable de Vertex AI
        
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
        
        # Inicializar Notion Manager
        self.notion_manager = None
        try:
            self.notion_manager = NotionManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Notion: {e}")
            print("La funcionalidad de Notion no estará disponible.")
            print("Para usar Notion, configura NOTION_TOKEN y NOTION_DATABASE_ID en .env")

        # Inicializar Google Sheets Manager
        self.sheets_manager = None
        try:
            self.sheets_manager = GoogleSheetsManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Google Sheets: {e}")
            print("La funcionalidad de Sheets no estará disponible.")
            print("Para usar Sheets, habilita las APIs Google Sheets y Drive en Cloud Console.")

        # Inicializar Gmail Manager
        self.gmail_manager = None
        try:
            self.gmail_manager = GmailManager()
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar Gmail: {e}")
            print("La funcionalidad de Gmail no estará disponible.")
            print("Para usar Gmail, habilita la Gmail API en Google Cloud Console (proyecto uniandes-452002).")

        # Inicializar Google Maps Manager
        self.maps_manager = None
        try:
            self.maps_manager = MapsManager()
            # Detectar ubicación del dispositivo al iniciar
            self._device_location = self.maps_manager.refresh_location()
        except Exception as e:
            self._device_location = None
            print(f"Advertencia: No se pudo inicializar Google Maps: {e}")
            print("La funcionalidad de mapas no estará disponible.")
            print("Para usar Maps, configura GOOGLE_MAPS_API_KEY en .env")
    
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

        elif function_name == "list_calendar_events":
            if self.calendar_manager:
                result = self.calendar_manager.list_events(
                    time_min=function_args.get("time_min"),
                    time_max=function_args.get("time_max"),
                    max_results=function_args.get("max_results", 10),
                )
                if result.get("status") == "success" and result.get("count", 0) > 0 and self.telegram_sender and self.telegram_chat_id:
                    lines = [f"📅 *Eventos en tu calendario ({result['count']}):*"]
                    for ev in result["events"]:
                        lines.append(
                            f"\n• *{ev['summary']}*\n"
                            f"  🕒 {ev['start']}"
                            + (f" → {ev['end']}" if ev.get('end') else "")
                            + (f"\n  📍 {ev['location']}" if ev.get('location') else "")
                            + (f"\n  [Ver evento]({ev['event_link']})" if ev.get('event_link') else "")
                        )
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text="\n".join(lines),
                    )
                return result
            else:
                return {"status": "error", "message": "Google Calendar not configured"}

        elif function_name == "search_calendar_events":
            if self.calendar_manager:
                result = self.calendar_manager.search_events(
                    query=function_args.get("query"),
                    time_min=function_args.get("time_min"),
                    time_max=function_args.get("time_max"),
                    max_results=function_args.get("max_results", 10),
                )
                if result.get("status") == "success" and result.get("count", 0) > 0 and self.telegram_sender and self.telegram_chat_id:
                    lines = [f"🔍 *Resultados para '{function_args.get('query')}' ({result['count']}):*"]
                    for ev in result["events"]:
                        lines.append(
                            f"\n• *{ev['summary']}*\n"
                            f"  🕒 {ev['start']}"
                            + (f" → {ev['end']}" if ev.get('end') else "")
                            + (f"\n  📍 {ev['location']}" if ev.get('location') else "")
                            + (f"\n  [Ver evento]({ev['event_link']})" if ev.get('event_link') else "")
                        )
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text="\n".join(lines),
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
        
        elif function_name == "create_notion_page":
            if self.notion_manager:
                result = self.notion_manager.create_page(
                    title=function_args.get("title"),
                    content=function_args.get("content"),
                    tags=function_args.get("tags")
                )
                return result
            else:
                return {"status": "error", "message": "Notion not configured"}

        elif function_name == "create_notion_list":
            if self.notion_manager:
                result = self.notion_manager.create_list(
                    title=function_args.get("title"),
                    items=function_args.get("items"),
                    tags=function_args.get("tags")
                )
                return result
            else:
                return {"status": "error", "message": "Notion not configured"}

        elif function_name == "search_notion_pages":
            if self.notion_manager:
                result = self.notion_manager.search_pages(
                    query=function_args.get("query"),
                    max_results=function_args.get("max_results", 5)
                )
                return result
            else:
                return {"status": "error", "message": "Notion not configured"}

        # Aquí se pueden agregar más funciones fácilmente
        elif function_name == "search_places":
            if self.maps_manager:
                return self.maps_manager.search_places(
                    query=function_args.get("query"),
                    location=function_args.get("location"),
                    radius_km=function_args.get("radius_km", 5),
                    max_results=function_args.get("max_results", 5)
                )
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "get_directions":
            if self.maps_manager:
                result = self.maps_manager.get_directions(
                    destination=function_args.get("destination"),
                    origin=function_args.get("origin"),
                    mode=function_args.get("mode", "driving"),
                    send_telegram_link=function_args.get("send_telegram_link", True)
                )
                if result.get("status") == "success" and result.get("send_to_telegram", True) and self.telegram_sender and self.telegram_chat_id:
                    mode_emoji = {"driving": "🚗", "walking": "🚶", "bicycling": "🚴", "transit": "🚌"}.get(result.get("mode", "driving"), "🚗")
                    text = (
                        f"{mode_emoji} *Ruta a {result['destination']}*\n"
                        f"📍 Desde: {result['origin']}\n"
                        f"🛣️ Distancia: {result['distance']}\n"
                        f"⏱️ Sin tráfico: {result['duration_no_traffic']}\n"
                        f"🚦 Con tráfico: {result['duration_with_traffic']}\n"
                        f"[Abrir en Google Maps]({result['directions_url']})"
                    )
                    self.telegram_sender.send_message(chat_id=self.telegram_chat_id, text=text)
                return result
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "get_traffic_info":
            if self.maps_manager:
                result = self.maps_manager.get_traffic_info(
                    destination=function_args.get("destination"),
                    origin=function_args.get("origin")
                )
                if result.get("status") == "success" and self.telegram_sender and self.telegram_chat_id:
                    traffic_emoji = {
                        "fluido": "🟢", "moderado": "🟡",
                        "con demoras": "🟠", "muy congestionado": "🔴"
                    }.get(result.get("traffic_status", ""), "🚦")
                    text = (
                        f"{traffic_emoji} *Tráfico hacia {result['destination']}*\n"
                        f"🛣️ Distancia: {result['distance']}\n"
                        f"⏱️ Sin tráfico: {result['duration_no_traffic']}\n"
                        f"🚦 Ahora: {result['duration_with_traffic']} ({result['traffic_status']})"
                        + (f" (+{result['delay_minutes']} min)" if result.get('delay_minutes', 0) > 0 else "") +
                        f"\n[Ver ruta]({result['directions_url']})"
                    )
                    self.telegram_sender.send_message(chat_id=self.telegram_chat_id, text=text)
                return result
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "get_place_details":
            if self.maps_manager:
                result = self.maps_manager.get_place_details(
                    place_name=function_args.get("place_name"),
                    location_hint=function_args.get("location_hint"),
                    send_telegram_link=function_args.get("send_telegram_link", True)
                )
                if result.get("status") == "success" and result.get("send_to_telegram", True) and self.telegram_sender and self.telegram_chat_id:
                    open_str = "🟢 Abierto ahora" if result.get("open_now") else ("🔴 Cerrado ahora" if result.get("open_now") is False else "")
                    text = (
                        f"📍 *{result['name']}*\n"
                        f"{result.get('address', '')}\n"
                        + (f"⭐ {result['rating']}/5 ({result.get('total_ratings', '?')} reseñas)\n" if result.get('rating') else "")
                        + (f"{open_str}\n" if open_str else "")
                        + (f"📞 {result['phone']}\n" if result.get('phone') else "")
                        + (f"🌐 {result['website']}\n" if result.get('website') else "")
                        + (f"[Ver en Google Maps]({result['maps_url']})" if result.get('maps_url') else "")
                    )
                    self.telegram_sender.send_message(chat_id=self.telegram_chat_id, text=text)
                return result
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "send_static_map":
            if self.maps_manager:
                result = self.maps_manager.get_static_map_url(
                    center=function_args.get("center"),
                    zoom=function_args.get("zoom", 14),
                    markers=function_args.get("markers"),
                    map_type=function_args.get("map_type", "roadmap"),
                    caption=function_args.get("caption")
                )
                # Enviar imagen por Telegram si está configurado
                if result["status"] == "success" and self.telegram_sender and self.telegram_chat_id:
                    try:
                        self.telegram_sender.send_photo_url(
                            chat_id=self.telegram_chat_id,
                            photo_url=result["static_map_url"],
                            caption=result.get("caption", "")
                        )
                    except Exception as e:
                        # Fallback: enviar como link si no soporta foto directa
                        self.telegram_sender.send_message(
                            chat_id=self.telegram_chat_id,
                            text=f"🗺️ *{result.get('caption', 'Mapa')}*\n{result['static_map_url']}"
                        )
                return result
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "send_street_view":
            if self.maps_manager:
                result = self.maps_manager.get_street_view(
                    location=function_args.get("location"),
                    heading=function_args.get("heading"),
                    caption=function_args.get("caption")
                )
                if result["status"] == "success" and self.telegram_sender and self.telegram_chat_id:
                    try:
                        self.telegram_sender.send_photo_url(
                            chat_id=self.telegram_chat_id,
                            photo_url=result["street_view_image_url"],
                            caption=result.get("caption", "")
                        )
                    except Exception as e:
                        self.telegram_sender.send_message(
                            chat_id=self.telegram_chat_id,
                            text=(
                                f"📸 *{result.get('caption', 'Street View')}*\n"
                                f"[Ver en Street View]({result['street_view_explore_url']})"
                            )
                        )
                return result
            return {"status": "error", "message": "Google Maps not configured"}

        elif function_name == "find_spreadsheet":
            if self.sheets_manager:
                result = self.sheets_manager.find_spreadsheet(
                    query=function_args.get("query"),
                    max_results=function_args.get("max_results", 5),
                )
                if result.get("status") == "success" and result.get("count", 0) > 0 and self.telegram_sender and self.telegram_chat_id:
                    lines = [f"🔍 *Documentos encontrados para '{function_args.get('query')}' ({result['count']}):*"]
                    for s in result["spreadsheets"]:
                        lines.append(f"• *{s['name']}*\n  [Abrir]({s['url']})")
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text="\n\n".join(lines),
                    )
                return result
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "list_spreadsheets":
            if self.sheets_manager:
                return self.sheets_manager.list_spreadsheets(
                    max_results=function_args.get("max_results", 20)
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "read_spreadsheet":
            if self.sheets_manager:
                return self.sheets_manager.read_spreadsheet(
                    spreadsheet_name_or_id=function_args.get("spreadsheet_name_or_id"),
                    sheet_name=function_args.get("sheet_name"),
                    cell_range=function_args.get("cell_range"),
                    max_rows=function_args.get("max_rows", 100),
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "search_in_spreadsheets":
            if self.sheets_manager:
                return self.sheets_manager.search_in_spreadsheets(
                    query=function_args.get("query"),
                    spreadsheet_name_or_id=function_args.get("spreadsheet_name_or_id"),
                    max_results=function_args.get("max_results", 20),
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "write_to_spreadsheet":
            if self.sheets_manager:
                return self.sheets_manager.write_to_spreadsheet(
                    spreadsheet_name_or_id=function_args.get("spreadsheet_name_or_id"),
                    cell_range=function_args.get("cell_range"),
                    values=function_args.get("values"),
                    sheet_name=function_args.get("sheet_name"),
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "append_rows_to_spreadsheet":
            if self.sheets_manager:
                return self.sheets_manager.append_rows(
                    spreadsheet_name_or_id=function_args.get("spreadsheet_name_or_id"),
                    rows=function_args.get("rows"),
                    sheet_name=function_args.get("sheet_name"),
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "create_spreadsheet":
            if self.sheets_manager:
                result = self.sheets_manager.create_spreadsheet(
                    title=function_args.get("title"),
                    sheet_name=function_args.get("sheet_name", "Hoja1"),
                    headers=function_args.get("headers"),
                )
                if result.get("status") == "success" and self.telegram_sender and self.telegram_chat_id:
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text=(
                            f"📊 *Nuevo documento creado: {result['spreadsheet']}*\n"
                            f"[Abrir en Google Sheets]({result['url']})"
                        ),
                    )
                return result
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "add_sheet_to_spreadsheet":
            if self.sheets_manager:
                return self.sheets_manager.add_sheet(
                    spreadsheet_name_or_id=function_args.get("spreadsheet_name_or_id"),
                    new_sheet_name=function_args.get("new_sheet_name"),
                    headers=function_args.get("headers"),
                )
            return {"status": "error", "message": "Google Sheets not configured"}

        elif function_name == "send_email":
            if self.gmail_manager:
                result = self.gmail_manager.send_email(
                    to=function_args.get("to"),
                    subject=function_args.get("subject"),
                    body=function_args.get("body"),
                    cc=function_args.get("cc"),
                    reply_to_message_id=function_args.get("reply_to_message_id"),
                )
                return result
            return {"status": "error", "message": "Gmail not configured"}

        elif function_name == "search_emails":
            if self.gmail_manager:
                result = self.gmail_manager.search_emails(
                    query=function_args.get("query"),
                    max_results=function_args.get("max_results", 10),
                    include_body=function_args.get("include_body", True),
                )
                # Si hay correos, enviar resumen detallado por Telegram
                if (
                    result.get("status") == "success"
                    and result.get("count", 0) > 0
                    and self.telegram_sender
                    and self.telegram_chat_id
                ):
                    lines = [f"📧 *Correos encontrados ({result['count']}):*"]
                    for i, em in enumerate(result["emails"], 1):
                        lines.append(
                            f"\n*{i}. {em.get('subject','(sin asunto)')}*\n"
                            f"De: {em.get('from','')}\n"
                            f"Fecha: {em.get('date','')}\n"
                            + (f"_{em.get('body_excerpt','')[:300]}_" if em.get('body_excerpt') else "")
                        )
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text="\n".join(lines),
                    )
                return result
            return {"status": "error", "message": "Gmail not configured"}

        elif function_name == "get_email":
            if self.gmail_manager:
                result = self.gmail_manager.get_email(
                    message_id=function_args.get("message_id"),
                )
                if result.get("status") == "success" and self.telegram_sender and self.telegram_chat_id:
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text=(
                            f"📧 *{result.get('subject','(sin asunto)')}*\n"
                            f"De: {result.get('from','')}\n"
                            f"Para: {result.get('to','')}\n"
                            f"Fecha: {result.get('date','')}\n\n"
                            f"{result.get('body','')[:2000]}"
                        ),
                    )
                return result
            return {"status": "error", "message": "Gmail not configured"}

        elif function_name == "list_inbox":
            if self.gmail_manager:
                result = self.gmail_manager.list_inbox(
                    max_results=function_args.get("max_results", 10),
                    unread_only=function_args.get("unread_only", False),
                )
                if (
                    result.get("status") == "success"
                    and result.get("count", 0) > 0
                    and self.telegram_sender
                    and self.telegram_chat_id
                ):
                    lines = [f"📬 *Bandeja de entrada ({result['count']} correos):*"]
                    for i, em in enumerate(result["emails"], 1):
                        unread_mark = "🔵 " if em.get("unread") else ""
                        lines.append(
                            f"{unread_mark}*{i}. {em.get('subject','(sin asunto)')}*\n"
                            f"De: {em.get('from','')} — {em.get('date','')}"
                        )
                    self.telegram_sender.send_message(
                        chat_id=self.telegram_chat_id,
                        text="\n\n".join(lines),
                    )
                return result
            return {"status": "error", "message": "Gmail not configured"}

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

        # Adjuntar ubicación del dispositivo si está disponible
        location_context = ""
        if self._device_location:
            lat, lng = self._device_location
            location_context = f"[Ubicación actual del usuario: {lat:.5f},{lng:.5f}] "

        full_message = date_context + location_context + user_message

        # Log de caracteres enviados
        print(f"[GeminiAgent] Enviando al modelo — caracteres del mensaje: {len(full_message)}")

        # Enviar mensaje usando Vertex AI
        response = self.chat.send_message(full_message)

        function_calls_executed = []

        # Loop para procesar function calls (Gemini puede devolver múltiples a la vez)
        while response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            # Recolectar TODOS los function calls de esta respuesta
            pending_calls = [
                part.function_call
                for part in response.candidates[0].content.parts
                if hasattr(part, 'function_call') and part.function_call and part.function_call.name
            ]

            if not pending_calls:
                break

            # Ejecutar todos y recolectar respuestas
            function_response_parts = []
            for function_call in pending_calls:
                function_name = function_call.name
                function_args = dict(function_call.args) if function_call.args else {}

                print(f"[GeminiAgent] Ejecutando función: {function_name}")
                print(f"[GeminiAgent] Argumentos: {function_args}")

                function_result = self._execute_function(function_name, function_args)
                function_calls_executed.append({
                    "name": function_name,
                    "args": function_args,
                    "result": function_result
                })

                print(f"[GeminiAgent] Resultado: {function_result.get('status', 'unknown')}")
                if function_result.get('status') == 'error':
                    print(f"[GeminiAgent] ❌ Error: {function_result.get('message', 'Sin mensaje')}")

                function_response_parts.append(
                    Part.from_function_response(
                        name=function_name,
                        response=function_result
                    )
                )

            # Enviar TODAS las respuestas juntas en un solo mensaje
            print(f"[GeminiAgent] Enviando {len(function_response_parts)} respuestas de función al modelo")
            response = self.chat.send_message(function_response_parts)
        
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
