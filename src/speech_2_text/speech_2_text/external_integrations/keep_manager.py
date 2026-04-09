"""
Gestor de notas usando Google Keep (no oficial)
IMPORTANTE: Google Keep no tiene una API oficial. Esta integración usa gkeepapi,
una biblioteca no oficial que puede dejar de funcionar si Google cambia su sistema.
"""
import os
from dotenv import load_dotenv, find_dotenv
import gkeepapi
from typing import Optional, Dict, Any, List

# Buscar .env subiendo directorios
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)

GOOGLE_KEEP_EMAIL = os.getenv('GOOGLE_KEEP_EMAIL')
GOOGLE_KEEP_APP_PASSWORD = os.getenv('GOOGLE_KEEP_APP_PASSWORD')


# Definición de funciones para function calling
KEEP_FUNCTIONS = [
    {
        "name": "create_keep_note",
        "description": "Crea una nota en Google Keep con título y contenido. Útil para guardar información, ideas, recordatorios o cualquier texto que el usuario quiera conservar.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la nota"
                },
                "content": {
                    "type": "string",
                    "description": "Contenido o cuerpo de la nota"
                },
                "color": {
                    "type": "string",
                    "enum": ["DEFAULT", "RED", "ORANGE", "YELLOW", "GREEN", "TEAL", "BLUE", "DARKBLUE", "PURPLE", "PINK", "BROWN", "GRAY"],
                    "description": "Color de la nota (opcional)"
                },
                "pinned": {
                    "type": "boolean",
                    "description": "Si la nota debe estar fijada al inicio (opcional)"
                }
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "create_keep_list",
        "description": "Crea una lista de verificación (checklist) en Google Keep. Ideal para listas de compras, tareas o cualquier lista de ítems.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la lista"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Lista de ítems a agregar como elementos de la checklist"
                },
                "color": {
                    "type": "string",
                    "enum": ["DEFAULT", "RED", "ORANGE", "YELLOW", "GREEN", "TEAL", "BLUE", "DARKBLUE", "PURPLE", "PINK", "BROWN", "GRAY"],
                    "description": "Color de la lista (opcional)"
                },
                "pinned": {
                    "type": "boolean",
                    "description": "Si la lista debe estar fijada al inicio (opcional)"
                }
            },
            "required": ["title", "items"]
        }
    },
    {
        "name": "search_keep_notes",
        "description": "Busca notas en Google Keep por palabra clave o frase.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Palabra o frase a buscar en las notas"
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


class GoogleKeepManager:
    """Gestor de notas de Google Keep usando gkeepapi (no oficial)"""
    
    def __init__(self, email: str = None, app_password: str = None):
        """
        Inicializa el gestor de Google Keep.
        
        Args:
            email: Email de la cuenta de Google
            app_password: Contraseña de aplicación (no la contraseña normal)
                         Generar en: https://myaccount.google.com/apppasswords
        """
        self.email = email or GOOGLE_KEEP_EMAIL
        self.app_password = app_password or GOOGLE_KEEP_APP_PASSWORD
        self.keep = gkeepapi.Keep()
        self._authenticated = False
        
        if not self.email or not self.app_password:
            raise ValueError(
                "Se requiere GOOGLE_KEEP_EMAIL y GOOGLE_KEEP_APP_PASSWORD en .env\n"
                "IMPORTANTE: Debes generar una contraseña de aplicación en:\n"
                "https://myaccount.google.com/apppasswords\n"
                "NO uses tu contraseña normal de Google."
            )
        
        self._authenticate()
    
    def _authenticate(self):
        """Autentica con Google Keep"""
        try:
            self.keep.login(self.email, self.app_password)
            self._authenticated = True
            print(f"[KeepManager] ✅ Autenticado exitosamente como {self.email}")
        except Exception as e:
            print(f"[KeepManager] ❌ Error al autenticar: {e}")
            print("Verifica que:")
            print("1. El email sea correcto")
            print("2. Hayas generado una contraseña de aplicación (no tu contraseña normal)")
            print("3. La verificación en 2 pasos esté habilitada en tu cuenta")
            raise
    
    def _ensure_authenticated(self):
        """Verifica que esté autenticado antes de realizar operaciones"""
        if not self._authenticated:
            raise RuntimeError("No autenticado con Google Keep")
    
    def create_note(
        self, 
        title: str, 
        content: str, 
        color: str = "DEFAULT",
        pinned: bool = False
    ) -> Dict[str, Any]:
        """
        Crea una nota en Google Keep.
        
        Args:
            title: Título de la nota
            content: Contenido de la nota
            color: Color de la nota (DEFAULT, RED, ORANGE, etc.)
            pinned: Si la nota debe estar fijada
            
        Returns:
            Dict con status y detalles de la nota creada
        """
        self._ensure_authenticated()
        
        try:
            # Crear nota
            note = self.keep.createNote(title, content)
            
            # Configurar color
            if color and color != "DEFAULT":
                try:
                    color_enum = getattr(gkeepapi.node.ColorValue, color)
                    note.color = color_enum
                except AttributeError:
                    print(f"[KeepManager] ⚠️ Color '{color}' no válido, usando DEFAULT")
            
            # Fijar nota si se solicita
            if pinned:
                note.pinned = True
            
            # Sincronizar cambios
            self.keep.sync()
            
            return {
                "status": "success",
                "note_id": note.id,
                "title": title,
                "content": content,
                "message": f"Nota '{title}' creada exitosamente en Google Keep"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al crear nota: {str(e)}"
            }
    
    def create_list(
        self,
        title: str,
        items: List[str],
        color: str = "DEFAULT",
        pinned: bool = False
    ) -> Dict[str, Any]:
        """
        Crea una lista de verificación (checklist) en Google Keep.
        
        Args:
            title: Título de la lista
            items: Lista de ítems a agregar
            color: Color de la lista
            pinned: Si la lista debe estar fijada
            
        Returns:
            Dict con status y detalles de la lista creada
        """
        self._ensure_authenticated()
        
        try:
            # Crear lista
            glist = self.keep.createList(title, items)
            
            # Configurar color
            if color and color != "DEFAULT":
                try:
                    color_enum = getattr(gkeepapi.node.ColorValue, color)
                    glist.color = color_enum
                except AttributeError:
                    print(f"[KeepManager] ⚠️ Color '{color}' no válido, usando DEFAULT")
            
            # Fijar lista si se solicita
            if pinned:
                glist.pinned = True
            
            # Sincronizar cambios
            self.keep.sync()
            
            return {
                "status": "success",
                "list_id": glist.id,
                "title": title,
                "items_count": len(items),
                "message": f"Lista '{title}' creada exitosamente con {len(items)} ítems"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al crear lista: {str(e)}"
            }
    
    def search_notes(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Busca notas en Google Keep.
        
        Args:
            query: Palabra o frase a buscar
            max_results: Número máximo de resultados
            
        Returns:
            Dict con status y lista de notas encontradas
        """
        self._ensure_authenticated()
        
        try:
            # Sincronizar para obtener notas actualizadas
            self.keep.sync()
            
            # Buscar notas
            results = []
            for note in self.keep.find(query=query):
                if len(results) >= max_results:
                    break
                
                results.append({
                    "id": note.id,
                    "title": note.title,
                    "content": note.text[:200] if note.text else "",  # Primeros 200 chars
                    "pinned": note.pinned,
                    "archived": note.archived
                })
            
            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results,
                "message": f"Se encontraron {len(results)} notas"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error al buscar notas: {str(e)}"
            }


def main():
    """Función de prueba"""
    print("="*60)
    print("Google Keep Manager - Prueba")
    print("="*60)
    
    try:
        manager = GoogleKeepManager()
        
        # Crear una nota de prueba
        print("\n1. Creando nota de prueba...")
        result = manager.create_note(
            title="Nota de prueba - NAO Agent",
            content="Esta es una nota de prueba creada por el agente NAO.",
            color="BLUE",
            pinned=True
        )
        print(f"Resultado: {result}")
        
        # Crear una lista de prueba
        print("\n2. Creando lista de prueba...")
        result = manager.create_list(
            title="Lista de prueba - NAO Agent",
            items=["Item 1", "Item 2", "Item 3"],
            color="GREEN"
        )
        print(f"Resultado: {result}")
        
        # Buscar notas
        print("\n3. Buscando notas...")
        result = manager.search_notes(query="NAO", max_results=5)
        print(f"Resultado: {result}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
