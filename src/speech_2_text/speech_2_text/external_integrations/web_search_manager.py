import os
import requests
from dotenv import load_dotenv, find_dotenv

# Buscar .env subiendo directorios desde este archivo, o usar ruta absoluta si está definida
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(
    filename='.env',
    raise_error_if_not_found=False,
    usecwd=False
)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchManager:
    """Gestor de búsquedas web mediante Google Custom Search API"""

    def __init__(self, api_key: str = None, search_engine_id: str = None):
        self.api_key = api_key or GOOGLE_SEARCH_API_KEY
        self.search_engine_id = search_engine_id or GOOGLE_SEARCH_ENGINE_ID

    def search(self, query: str, num_results: int = 5) -> dict:
        """
        Realiza una búsqueda web y retorna los resultados más relevantes.

        Args:
            query: La consulta de búsqueda.
            num_results: Número de resultados a retornar (máximo 10 por petición de la API).

        Returns:
            dict con status y lista de resultados o mensaje de error.
        """
        if not self.api_key or not self.search_engine_id:
            return {
                "status": "error",
                "message": "Google Search API no configurada. Faltan GOOGLE_SEARCH_API_KEY o GOOGLE_SEARCH_ENGINE_ID."
            }

        try:
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10),
            }
            response = requests.get(GOOGLE_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            results = [
                {
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                }
                for item in items
            ]

            return {
                "status": "success",
                "query": query,
                "results": results,
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Error en la petición HTTP: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ── Definición de función para function calling ──────────────────────────────

web_search_function = {
    "name": "web_search",
    "description": (
        "Realiza una búsqueda en internet usando Google Search y retorna los resultados más relevantes. "
        "Úsala cuando el usuario pida información actualizada, noticias, datos que no conoces, "
        "o cualquier consulta que requiera buscar en la web."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "La consulta de búsqueda en lenguaje natural o palabras clave."
            },
            "num_results": {
                "type": "integer",
                "description": "Número de resultados a obtener (entre 1 y 10). Por defecto 5.",
            }
        },
        "required": ["query"]
    }
}

# Exportar funciones disponibles para Web Search
WEB_SEARCH_FUNCTIONS = [web_search_function]
