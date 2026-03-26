"""
Gestor de búsquedas web usando Serper API (Google Search)
"""
import os
import requests
from dotenv import load_dotenv, find_dotenv

# Buscar .env subiendo directorios, o usar ruta absoluta si está definida en DOTENV_PATH
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

SERPER_API_KEY = os.getenv('SERPER_API_KEY')


class WebSearchManager:
    """Gestor de búsquedas web usando Serper API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or SERPER_API_KEY
        
        if not self.api_key:
            raise ValueError(
                "Se requiere SERPER_API_KEY en el archivo .env. "
                "Obtén tu API Key gratis en https://serper.dev (2500 búsquedas gratis)"
            )
    
    def search(self, query: str, num_results: int = 5):
        """
        Realiza una búsqueda web usando Serper y retorna los resultados
        
        Args:
            query: El término de búsqueda
            num_results: Número de resultados a devolver (máximo 10)
        
        Returns:
            dict con status y results (lista de diccionarios con title, link, snippet)
        """
        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": min(num_results, 10)
            }
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_msg = response.json().get("message", "Error desconocido") if response.text else f"HTTP {response.status_code}"
                return {
                    "status": "error",
                    "message": f"Error en búsqueda: {error_msg}"
                }
            
            data = response.json()
            
            # Extraer resultados orgánicos
            results = []
            if "organic" in data:
                for item in data["organic"][:num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
            
            return {
                "status": "success",
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al realizar búsqueda: {str(e)}"
            }


# Definición de funciones para búsqueda web (function calling)
web_search_function = {
    "name": "web_search",
    "description": (
        "Realiza una búsqueda en internet usando Google Search. "
        "Usa esta función cuando el usuario pida información actualizada, "
        "noticias, datos específicos que no conoces, o cuando necesites "
        "buscar contenido en la web. Retorna títulos, links y descripciones "
        "de los resultados más relevantes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "El término o pregunta a buscar en internet"
            },
            "num_results": {
                "type": "integer",
                "description": "Número de resultados a devolver (1-10, por defecto 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}

# Exportar la lista de funciones
SEARCH_FUNCTIONS = [web_search_function]
