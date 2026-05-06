"""
Gestor de Google Sheets usando gspread + OAuth 2.0.

Capacidades principales:
  - Listar todos los documentos de Sheets del usuario
  - Leer datos de cualquier hoja (rango o hoja completa)
  - Buscar texto a través de todos los documentos
  - Escribir / actualizar celdas
  - Añadir filas al final de una hoja
  - Crear nuevos documentos y/o nuevas hojas dentro de un documento
  - Eliminar filas por índice

Requiere:
  - credentials.json de Google Cloud Console con scopes de Sheets + Drive
  - Las credenciales deben tener habilitadas las APIs:
      · Google Sheets API
      · Google Drive API
  - Configurar GOOGLE_SHEETS_TOKEN_FILE en .env (opcional; default: token_sheets.json)
    IMPORTANTE: el token de Calendar (token.json) usa scopes distintos;
    por eso Sheets usa su propio archivo de token para evitar conflictos.
"""

import os
import pickle
from pathlib import Path
from typing import Any

import gspread
from dotenv import find_dotenv, load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Configuración ──────────────────────────────────────────────────────────────
_env_file = (
    os.getenv("DOTENV_PATH")
    or find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=False)
)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE",
    os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json"),
)
GOOGLE_SHEETS_TOKEN_FILE = os.getenv("GOOGLE_SHEETS_TOKEN_FILE", "token_sheets.json")

# Scopes necesarios para leer/escribir Sheets y listar archivos en Drive
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",  # para listar / buscar archivos
]

# ── Declaraciones de funciones para function calling ──────────────────────────
SHEETS_FUNCTIONS = [
    {
        "name": "list_spreadsheets",
        "description": (
            "Lista todos los documentos de Google Sheets del usuario. "
            "Devuelve nombre, ID y URL de cada spreadsheet. "
            "Útil antes de leer o editar un documento cuando no se conoce el ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de documentos a listar (default: 20).",
                    "default": 20,
                }
            },
            "required": [],
        },
    },
    {
        "name": "read_spreadsheet",
        "description": (
            "Lee los datos de una hoja de Google Sheets. "
            "Puede leer toda la hoja o un rango específico (p. ej. 'A1:D10'). "
            "Acepta el nombre del documento o su ID. "
            "Si no se especifica sheet_name, lee la primera hoja."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_name_or_id": {
                    "type": "string",
                    "description": "Nombre exacto o ID del documento de Google Sheets.",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Nombre de la pestaña/hoja (default: primera hoja).",
                },
                "cell_range": {
                    "type": "string",
                    "description": (
                        "Rango de celdas en notación A1 (p. ej. 'A1:E20'). "
                        "Si se omite, se lee toda la hoja."
                    ),
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Número máximo de filas a devolver (default: 100).",
                    "default": 100,
                },
            },
            "required": ["spreadsheet_name_or_id"],
        },
    },
    {
        "name": "search_in_spreadsheets",
        "description": (
            "Busca una palabra, frase o valor en todos los documentos de Google Sheets del usuario "
            "(o en un documento específico si se indica). "
            "Devuelve las filas que contienen la coincidencia junto con el nombre del documento y la hoja."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar dentro de las celdas.",
                },
                "spreadsheet_name_or_id": {
                    "type": "string",
                    "description": (
                        "Si se especifica, limita la búsqueda a ese documento. "
                        "Si se omite, busca en todos los documentos."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de filas coincidentes a devolver (default: 20).",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "write_to_spreadsheet",
        "description": (
            "Escribe o sobreescribe valores en un rango de celdas de Google Sheets. "
            "Úsalo para actualizar celdas individuales o bloques de datos. "
            "Los datos deben ser una lista de filas (lista de listas)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_name_or_id": {
                    "type": "string",
                    "description": "Nombre exacto o ID del documento.",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Nombre de la pestaña/hoja (default: primera hoja).",
                },
                "cell_range": {
                    "type": "string",
                    "description": "Celda inicial o rango destino (p. ej. 'A1' o 'B3:D5').",
                },
                "values": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "description": (
                        "Datos a escribir como lista de filas. "
                        "Ejemplo: [['Nombre','Edad'],['Ana','30']]"
                    ),
                },
            },
            "required": ["spreadsheet_name_or_id", "cell_range", "values"],
        },
    },
    {
        "name": "append_rows_to_spreadsheet",
        "description": (
            "Añade filas al final de los datos existentes en una hoja de Google Sheets. "
            "Ideal para registrar entradas nuevas sin sobreescribir datos previos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_name_or_id": {
                    "type": "string",
                    "description": "Nombre exacto o ID del documento.",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Nombre de la pestaña/hoja (default: primera hoja).",
                },
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "description": (
                        "Filas a añadir. Cada elemento es una fila (lista de valores). "
                        "Ejemplo: [['2026-05-04','Gasto','15000']]"
                    ),
                },
            },
            "required": ["spreadsheet_name_or_id", "rows"],
        },
    },
    {
        "name": "create_spreadsheet",
        "description": (
            "Crea un nuevo documento de Google Sheets con el título indicado. "
            "Opcionalmente agrega encabezados en la primera fila y configura el nombre de la hoja inicial."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título del nuevo documento.",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Nombre de la hoja inicial (default: 'Hoja1').",
                    "default": "Hoja1",
                },
                "headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista de encabezados de columna a insertar en la primera fila. "
                        "Ejemplo: ['Fecha','Descripción','Monto']"
                    ),
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "add_sheet_to_spreadsheet",
        "description": (
            "Añade una nueva pestaña/hoja a un documento de Google Sheets existente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_name_or_id": {
                    "type": "string",
                    "description": "Nombre exacto o ID del documento.",
                },
                "new_sheet_name": {
                    "type": "string",
                    "description": "Nombre de la nueva pestaña.",
                },
                "headers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Encabezados opcionales para la primera fila.",
                },
            },
            "required": ["spreadsheet_name_or_id", "new_sheet_name"],
        },
    },
]


# ── Manager ────────────────────────────────────────────────────────────────────
class GoogleSheetsManager:
    """Gestor de Google Sheets con autenticación OAuth 2.0."""

    def __init__(
        self,
        credentials_file: str = None,
        token_file: str = None,
    ):
        self.credentials_file = credentials_file or GOOGLE_SHEETS_CREDENTIALS_FILE
        self.token_file = token_file or GOOGLE_SHEETS_TOKEN_FILE

        self._creds: Credentials | None = None
        self._gc: gspread.Client | None = None
        self._drive_service = None

        self._authenticate()

    # ── Auth ──────────────────────────────────────────────────────────────────
    def _authenticate(self):
        """Autenticación OAuth 2.0 para Sheets + Drive."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        token_path = project_root / self.token_file
        credentials_path = project_root / self.credentials_file

        creds = None
        if token_path.exists():
            with open(token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"No se encontró el archivo de credenciales: {credentials_path}\n"
                        "Descarga credentials.json desde Google Cloud Console y colócalo en la raíz del proyecto."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SHEETS_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        self._creds = creds
        self._gc = gspread.authorize(creds)
        self._drive_service = build("drive", "v3", credentials=creds)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _open_spreadsheet(self, name_or_id: str) -> gspread.Spreadsheet:
        """Abre un spreadsheet por nombre o por ID (intenta ID primero)."""
        try:
            return self._gc.open_by_key(name_or_id)
        except Exception:
            pass
        try:
            return self._gc.open(name_or_id)
        except gspread.SpreadsheetNotFound:
            raise ValueError(
                f"No se encontró el documento '{name_or_id}'. "
                "Verifica el nombre exacto o el ID."
            )

    def _get_worksheet(
        self, spreadsheet: gspread.Spreadsheet, sheet_name: str | None
    ) -> gspread.Worksheet:
        if sheet_name:
            return spreadsheet.worksheet(sheet_name)
        return spreadsheet.sheet1

    # ── Operaciones públicas ──────────────────────────────────────────────────
    def list_spreadsheets(self, max_results: int = 20) -> dict:
        """Lista los Google Sheets del usuario usando Google Drive API."""
        try:
            query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
            response = (
                self._drive_service.files()
                .list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id, name, webViewLink, modifiedTime)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )
            files = response.get("files", [])
            sheets = [
                {
                    "name": f["name"],
                    "id": f["id"],
                    "url": f.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{f['id']}"),
                    "modified": f.get("modifiedTime", ""),
                }
                for f in files
            ]
            return {
                "status": "success",
                "count": len(sheets),
                "spreadsheets": sheets,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def read_spreadsheet(
        self,
        spreadsheet_name_or_id: str,
        sheet_name: str = None,
        cell_range: str = None,
        max_rows: int = 100,
    ) -> dict:
        """Lee datos de una hoja. Devuelve una lista de filas."""
        try:
            sp = self._open_spreadsheet(spreadsheet_name_or_id)
            ws = self._get_worksheet(sp, sheet_name)

            if cell_range:
                values = ws.get(cell_range)
            else:
                values = ws.get_all_values()

            # Limitar filas
            values = values[:max_rows]

            return {
                "status": "success",
                "spreadsheet": sp.title,
                "sheet": ws.title,
                "rows_returned": len(values),
                "data": values,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_in_spreadsheets(
        self,
        query: str,
        spreadsheet_name_or_id: str = None,
        max_results: int = 20,
    ) -> dict:
        """Busca texto en uno o todos los spreadsheets del usuario."""
        try:
            results = []
            query_lower = query.lower()

            if spreadsheet_name_or_id:
                spreadsheets_to_search = [self._open_spreadsheet(spreadsheet_name_or_id)]
            else:
                listed = self.list_spreadsheets(max_results=50)
                if listed["status"] != "success":
                    return listed
                spreadsheets_to_search = []
                for item in listed["spreadsheets"]:
                    try:
                        spreadsheets_to_search.append(
                            self._gc.open_by_key(item["id"])
                        )
                    except Exception:
                        pass

            for sp in spreadsheets_to_search:
                for ws in sp.worksheets():
                    all_values = ws.get_all_values()
                    for row_idx, row in enumerate(all_values, start=1):
                        row_text = " ".join(str(cell) for cell in row).lower()
                        if query_lower in row_text:
                            results.append(
                                {
                                    "spreadsheet": sp.title,
                                    "sheet": ws.title,
                                    "row_number": row_idx,
                                    "data": row,
                                }
                            )
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

            return {
                "status": "success",
                "query": query,
                "matches_found": len(results),
                "results": results,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def write_to_spreadsheet(
        self,
        spreadsheet_name_or_id: str,
        cell_range: str,
        values: list[list[Any]],
        sheet_name: str = None,
    ) -> dict:
        """Escribe datos en un rango de celdas (sobreescribe)."""
        try:
            sp = self._open_spreadsheet(spreadsheet_name_or_id)
            ws = self._get_worksheet(sp, sheet_name)
            ws.update(cell_range, values)
            return {
                "status": "success",
                "spreadsheet": sp.title,
                "sheet": ws.title,
                "range_written": cell_range,
                "rows_written": len(values),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def append_rows(
        self,
        spreadsheet_name_or_id: str,
        rows: list[list[Any]],
        sheet_name: str = None,
    ) -> dict:
        """Añade filas al final de los datos existentes."""
        try:
            sp = self._open_spreadsheet(spreadsheet_name_or_id)
            ws = self._get_worksheet(sp, sheet_name)
            ws.append_rows(rows, value_input_option="USER_ENTERED")
            return {
                "status": "success",
                "spreadsheet": sp.title,
                "sheet": ws.title,
                "rows_appended": len(rows),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_spreadsheet(
        self,
        title: str,
        sheet_name: str = "Hoja1",
        headers: list[str] = None,
    ) -> dict:
        """Crea un nuevo documento de Google Sheets."""
        try:
            sp = self._gc.create(title)
            ws = sp.sheet1
            ws.update_title(sheet_name)
            if headers:
                ws.append_row(headers, value_input_option="USER_ENTERED")
            url = f"https://docs.google.com/spreadsheets/d/{sp.id}"
            return {
                "status": "success",
                "spreadsheet": sp.title,
                "id": sp.id,
                "url": url,
                "sheet": sheet_name,
                "headers_added": bool(headers),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def add_sheet(
        self,
        spreadsheet_name_or_id: str,
        new_sheet_name: str,
        headers: list[str] = None,
    ) -> dict:
        """Añade una nueva pestaña a un documento existente."""
        try:
            sp = self._open_spreadsheet(spreadsheet_name_or_id)
            ws = sp.add_worksheet(title=new_sheet_name, rows=1000, cols=26)
            if headers:
                ws.append_row(headers, value_input_option="USER_ENTERED")
            return {
                "status": "success",
                "spreadsheet": sp.title,
                "new_sheet": new_sheet_name,
                "headers_added": bool(headers),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
