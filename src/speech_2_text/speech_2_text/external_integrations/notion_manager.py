"""
Gestor de notas y páginas usando Notion (API oficial).
Reemplaza la integración con Google Keep (no oficial).

Requiere:
    - Crear una integración en https://www.notion.so/my-integrations
    - Compartir una base de datos de Notion con esa integración
    - Configurar NOTION_TOKEN y NOTION_DATABASE_ID en .env
"""
import os
from dotenv import load_dotenv, find_dotenv
from notion_client import Client
from typing import Dict, Any, List

# Buscar .env subiendo directorios
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')


# Definición de funciones para function calling (equivalentes a Keep)
NOTION_FUNCTIONS = [
    {
        "name": "create_notion_page",
        "description": (
            "Crea una página (nota) en Notion con título y contenido. "
            "Útil para guardar información, ideas, recordatorios o cualquier texto que el usuario quiera conservar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la página"
                },
                "content": {
                    "type": "string",
                    "description": "Contenido o cuerpo de la página"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Etiquetas/categorías opcionales para organizar la nota"
                }
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "create_notion_list",
        "description": (
            "Crea una página en Notion con una lista de ítems tipo checklist. "
            "Ideal para listas de compras, tareas pendientes o cualquier lista de ítems."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la lista"
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de ítems a agregar como elementos de la checklist"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Etiquetas/categorías opcionales"
                }
            },
            "required": ["title", "items"]
        }
    },
    {
        "name": "search_notion_pages",
        "description": "Busca páginas (notas) en Notion por palabra clave o frase.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Palabra o frase a buscar en las páginas de Notion"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de resultados a retornar (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


class NotionManager:
    """Gestor de páginas y notas de Notion usando la API oficial."""

    def __init__(self, token: str = None, database_id: str = None):
        self.token = token or NOTION_TOKEN
        self.database_id = database_id or NOTION_DATABASE_ID

        if not self.token:
            raise ValueError(
                "Se requiere NOTION_TOKEN en .env\n"
                "Crea una integración en: https://www.notion.so/my-integrations"
            )
        if not self.database_id:
            raise ValueError(
                "Se requiere NOTION_DATABASE_ID en .env\n"
                "Comparte una base de datos de Notion con tu integración y copia su ID."
            )

        self.client = Client(auth=self.token)
        # Verificar conexión
        self.client.users.me()
        print("[NotionManager] ✅ Conectado a Notion exitosamente")

    def create_page(
        self,
        title: str,
        content: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una página en la base de datos de Notion.

        Args:
            title: Título de la página
            content: Contenido de texto
            tags: Lista de etiquetas (multi-select)

        Returns:
            Dict con status y detalles de la página creada
        """
        try:
            properties = {
                "Name": {
                    "title": [{"text": {"content": title}}]
                }
            }

            # Agregar tags si los hay y si la DB los soporta (multi_select)
            if tags:
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }

            # Bloques de contenido
            children = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]

            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )

            return {
                "status": "success",
                "page_id": page["id"],
                "url": page.get("url", ""),
                "title": title,
                "message": f"Página '{title}' creada exitosamente en Notion"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al crear página en Notion: {str(e)}"
            }

    def create_list(
        self,
        title: str,
        items: List[str],
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una página en Notion con una checklist.

        Args:
            title: Título de la lista
            items: Ítems de la checklist
            tags: Lista de etiquetas opcionales

        Returns:
            Dict con status y detalles de la página creada
        """
        try:
            properties = {
                "Name": {
                    "title": [{"text": {"content": title}}]
                }
            }

            if tags:
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }

            # Convertir ítems a bloques to_do (checklist)
            children = [
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": item}}],
                        "checked": False
                    }
                }
                for item in items
            ]

            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=children
            )

            return {
                "status": "success",
                "page_id": page["id"],
                "url": page.get("url", ""),
                "title": title,
                "items_count": len(items),
                "message": f"Lista '{title}' creada exitosamente con {len(items)} ítems en Notion"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al crear lista en Notion: {str(e)}"
            }

    def search_pages(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Busca páginas en Notion por texto.

        Args:
            query: Texto a buscar
            max_results: Máximo de resultados

        Returns:
            Dict con status y lista de páginas encontradas
        """
        try:
            response = self.client.search(
                query=query,
                filter={"value": "page", "property": "object"},
                page_size=max_results
            )

            results = []
            for page in response.get("results", []):
                # Obtener título
                title_prop = page.get("properties", {}).get("Name", {})
                title_parts = title_prop.get("title", [])
                title = "".join(t.get("plain_text", "") for t in title_parts) if title_parts else "(sin título)"

                results.append({
                    "id": page["id"],
                    "title": title,
                    "url": page.get("url", ""),
                    "created_time": page.get("created_time", ""),
                    "last_edited_time": page.get("last_edited_time", "")
                })

            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results,
                "message": f"Se encontraron {len(results)} páginas en Notion"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al buscar en Notion: {str(e)}"
            }


def main():
    """Función de prueba"""
    print("=" * 60)
    print("Notion Manager - Prueba")
    print("=" * 60)

    try:
        manager = NotionManager()

        print("\n1. Creando página de prueba...")
        result = manager.create_page(
            title="Nota de prueba - NAO Agent",
            content="Esta es una nota de prueba creada por el agente NAO.",
            tags=["prueba", "nao"]
        )
        print(f"Resultado: {result}")

        print("\n2. Creando lista de prueba...")
        result = manager.create_list(
            title="Lista de prueba - NAO Agent",
            items=["Item 1", "Item 2", "Item 3"]
        )
        print(f"Resultado: {result}")

        print("\n3. Buscando páginas...")
        result = manager.search_pages(query="NAO", max_results=5)
        print(f"Resultado: {result}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
