"""
Gestor de Gmail usando Gmail API + OAuth 2.0.

Capacidades principales:
  - Enviar correos a nombre del usuario (aparece como enviado desde su cuenta)
  - Responder a un hilo de correo existente
  - Buscar correos con lenguaje natural (traduce a query de Gmail)
  - Leer el contenido completo de un correo
  - Listar correos recientes de la bandeja de entrada

Requiere:
  - credentials.json de Google Cloud Console
  - Gmail API habilitada en el proyecto de las credenciales (uniandes-452002)
  - Variable GOOGLE_GMAIL_TOKEN_FILE en .env (default: token_gmail.json)
"""

import base64
import email as email_lib
import os
import pickle
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── Configuración ──────────────────────────────────────────────────────────────
_env_file = (
    os.getenv("DOTENV_PATH")
    or find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=False)
)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GMAIL_CREDENTIALS_FILE = os.getenv(
    "GMAIL_CREDENTIALS_FILE",
    os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json"),
)
GMAIL_TOKEN_FILE = os.getenv("GOOGLE_GMAIL_TOKEN_FILE", "token_gmail.json")

# Scopes: send + readonly (modificar labels, leer, buscar — no eliminar)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# ── Declaraciones de funciones para function calling ──────────────────────────
GMAIL_FUNCTIONS = [
    {
        "name": "send_email",
        "description": (
            "Envía un correo electrónico a nombre del usuario desde su cuenta de Gmail. "
            "El correo aparecerá en la bandeja de enviados del usuario. "
            "Úsalo cuando el usuario quiera enviar un email, escribir un correo, "
            "o contactar a alguien por correo electrónico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": (
                        "Dirección de correo del destinatario. "
                        "Puede incluir nombre y email: 'Nombre <email@ejemplo.com>' "
                        "o solo el email."
                    ),
                },
                "subject": {
                    "type": "string",
                    "description": "Asunto del correo.",
                },
                "body": {
                    "type": "string",
                    "description": (
                        "Cuerpo del correo en texto plano. "
                        "Redáctalo de forma natural y profesional según el contexto."
                    ),
                },
                "cc": {
                    "type": "string",
                    "description": "Dirección(es) en copia, separadas por coma (opcional).",
                },
                "reply_to_message_id": {
                    "type": "string",
                    "description": (
                        "ID del mensaje al que se responde (opcional). "
                        "Úsalo para que el correo quede en el mismo hilo."
                    ),
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "search_emails",
        "description": (
            "Busca correos en Gmail del usuario usando lenguaje natural. "
            "Úsalo cuando el usuario pregunte por correos recibidos, "
            "quiera saber si llegó algo de alguien, busque información en sus emails, "
            "o pida resumir correos sobre un tema. "
            "Devuelve asunto, remitente, fecha y un extracto del cuerpo de cada correo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Descripción en lenguaje natural de lo que buscar. "
                        "Ejemplos: 'correos de mi jefe esta semana', "
                        "'facturas de marzo', 'confirmación de vuelo', "
                        "'correos no leídos de hoy'."
                    ),
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de correos a devolver (default: 10, máx: 30).",
                    "default": 10,
                },
                "include_body": {
                    "type": "boolean",
                    "description": (
                        "Si es true, incluye el cuerpo completo (truncado a 500 chars) "
                        "de cada correo. Úsalo cuando el usuario necesite el contenido. "
                        "Default: true."
                    ),
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_email",
        "description": (
            "Lee el contenido completo de un correo específico por su ID. "
            "Úsalo cuando el usuario quiera leer un correo en detalle "
            "después de haberlo encontrado con search_emails."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "ID del mensaje de Gmail (obtenido de search_emails).",
                },
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "list_inbox",
        "description": (
            "Lista los correos más recientes de la bandeja de entrada del usuario. "
            "Úsalo cuando el usuario pregunte '¿qué correos tengo?', "
            "'¿llegó algo nuevo?' o quiera ver sus últimos emails."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Número de correos a listar (default: 10).",
                    "default": 10,
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "Si es true, lista solo los no leídos (default: false).",
                    "default": False,
                },
            },
            "required": [],
        },
    },
]


# ── Helpers internos ───────────────────────────────────────────────────────────
def _natural_query_to_gmail(query: str) -> str:
    """
    Convierte lenguaje natural a sintaxis de búsqueda de Gmail.
    Aplica heurísticas comunes; el resto lo pasa tal cual (Gmail entiende keywords).
    """
    q = query.lower()
    parts = []

    # No leídos
    if any(w in q for w in ["no leído", "no leidos", "sin leer", "unread"]):
        parts.append("is:unread")

    # Periodos de tiempo
    time_map = {
        "hoy": "newer_than:1d",
        "ayer": "newer_than:2d older_than:1d",
        "esta semana": "newer_than:7d",
        "este mes": "newer_than:30d",
        "último mes": "newer_than:30d",
        "esta semana": "newer_than:7d",
    }
    for keyword, gmail_filter in time_map.items():
        if keyword in q:
            parts.append(gmail_filter)
            break

    # Adjuntos
    if any(w in q for w in ["adjunto", "archivo adjunto", "attachment", "con archivo"]):
        parts.append("has:attachment")

    # Construir el query final: añadir el texto original como keywords de búsqueda libre
    # Eliminar palabras de filtro ya procesadas para no ensuciar el query
    clean = re.sub(
        r"\b(correos?|emails?|mails?|de|con|en|del?|los|las|mis|que|sobre|acerca de|"
        r"no leídos?|no leidos?|sin leer|hoy|ayer|esta semana|este mes|último mes|"
        r"adjunto|archivo adjunto|con archivo|tengo|llegó|llegaron|busca|buscar|muestra|"
        r"dame|dime|hay|algún|alguna)\b",
        " ",
        q,
        flags=re.IGNORECASE,
    ).strip()

    # Limpiar espacios extra
    clean = re.sub(r"\s+", " ", clean).strip()
    if clean:
        parts.append(clean)

    return " ".join(parts) if parts else query


def _decode_body(payload: dict) -> str:
    """Extrae el texto plano del payload del mensaje de Gmail."""
    body = ""

    def _extract(part):
        nonlocal body
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                body += base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        elif mime_type == "text/html" and not body:
            data = part.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                # Quitar tags HTML básico
                body += re.sub(r"<[^>]+>", " ", html)
                body = re.sub(r"\s+", " ", body).strip()
        elif "parts" in part:
            for sub in part["parts"]:
                _extract(sub)

    if "parts" in payload:
        for p in payload["parts"]:
            _extract(p)
    else:
        _extract(payload)

    return body.strip()


def _header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ── Manager ────────────────────────────────────────────────────────────────────
class GmailManager:
    """Gestor de Gmail con OAuth 2.0: envío y búsqueda de correos."""

    def __init__(self, credentials_file: str = None, token_file: str = None):
        self.credentials_file = credentials_file or GMAIL_CREDENTIALS_FILE
        self.token_file = token_file or GMAIL_TOKEN_FILE
        self._service = None
        self._user_email: Optional[str] = None
        self._authenticate()

    # ── Auth ──────────────────────────────────────────────────────────────────
    def _authenticate(self):
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
                        "Descarga credentials.json desde Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(token_path, "wb") as f:
                pickle.dump(creds, f)

        self._service = build("gmail", "v1", credentials=creds)

        # Cachear el email del usuario autenticado
        try:
            profile = self._service.users().getProfile(userId="me").execute()
            self._user_email = profile.get("emailAddress", "me")
        except Exception:
            self._user_email = "me"

    # ── Envío ─────────────────────────────────────────────────────────────────
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = None,
        reply_to_message_id: str = None,
    ) -> dict:
        """Envía un correo desde la cuenta del usuario autenticado."""
        try:
            msg = MIMEMultipart("alternative")
            msg["To"] = to
            msg["Subject"] = subject
            msg["From"] = self._user_email
            if cc:
                msg["Cc"] = cc

            # Adjuntar hilo si es respuesta
            if reply_to_message_id:
                try:
                    original = (
                        self._service.users()
                        .messages()
                        .get(userId="me", id=reply_to_message_id, format="metadata",
                             metadataHeaders=["Message-ID", "References", "Subject", "Thread-Id"])
                        .execute()
                    )
                    headers = original.get("payload", {}).get("headers", [])
                    orig_msg_id = _header(headers, "Message-ID")
                    orig_refs = _header(headers, "References")
                    if orig_msg_id:
                        msg["In-Reply-To"] = orig_msg_id
                        msg["References"] = (
                            f"{orig_refs} {orig_msg_id}".strip()
                            if orig_refs
                            else orig_msg_id
                        )
                    if not subject.lower().startswith("re:"):
                        msg["Subject"] = "Re: " + subject
                except Exception:
                    pass  # Si falla el hilo, igual envía el correo

            msg.attach(MIMEText(body, "plain", "utf-8"))

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            send_body: dict = {"raw": raw}
            if reply_to_message_id:
                try:
                    thread_id = original.get("threadId")
                    if thread_id:
                        send_body["threadId"] = thread_id
                except Exception:
                    pass

            result = self._service.users().messages().send(
                userId="me", body=send_body
            ).execute()

            return {
                "status": "success",
                "message_id": result.get("id"),
                "from": self._user_email,
                "to": to,
                "subject": subject,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Búsqueda ──────────────────────────────────────────────────────────────
    def search_emails(
        self,
        query: str,
        max_results: int = 10,
        include_body: bool = True,
    ) -> dict:
        """Busca correos por lenguaje natural; devuelve metadata + extracto."""
        try:
            max_results = min(max_results, 30)
            gmail_query = _natural_query_to_gmail(query)

            response = (
                self._service.users()
                .messages()
                .list(userId="me", q=gmail_query, maxResults=max_results)
                .execute()
            )
            messages_meta = response.get("messages", [])

            emails = []
            for meta in messages_meta:
                msg = (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=meta["id"], format="full")
                    .execute()
                )
                payload = msg.get("payload", {})
                headers = payload.get("headers", [])

                body_text = ""
                if include_body:
                    body_text = _decode_body(payload)[:600]  # extracto

                emails.append(
                    {
                        "id": msg["id"],
                        "thread_id": msg.get("threadId"),
                        "from": _header(headers, "From"),
                        "to": _header(headers, "To"),
                        "subject": _header(headers, "Subject"),
                        "date": _header(headers, "Date"),
                        "snippet": msg.get("snippet", ""),
                        "body_excerpt": body_text,
                        "unread": "UNREAD" in msg.get("labelIds", []),
                    }
                )

            return {
                "status": "success",
                "query_used": gmail_query,
                "original_query": query,
                "count": len(emails),
                "emails": emails,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_email(self, message_id: str) -> dict:
        """Lee el contenido completo de un correo por ID."""
        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            body = _decode_body(payload)

            return {
                "status": "success",
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": _header(headers, "From"),
                "to": _header(headers, "To"),
                "cc": _header(headers, "Cc"),
                "subject": _header(headers, "Subject"),
                "date": _header(headers, "Date"),
                "body": body,
                "unread": "UNREAD" in msg.get("labelIds", []),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_inbox(self, max_results: int = 10, unread_only: bool = False) -> dict:
        """Lista los correos más recientes de la bandeja de entrada."""
        q = "in:inbox" + (" is:unread" if unread_only else "")
        return self.search_emails(
            query=q,
            max_results=max_results,
            include_body=False,
        )
