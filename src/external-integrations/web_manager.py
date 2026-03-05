import os
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv


# Cargar variables del env
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

# 1. Configurar el cliente (usa tu API Key)
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)

# 2. Definir la herramienta de búsqueda de Google
# En la nueva librería se llama 'google_search' dentro de types.Tool
tools = [
    types.Tool(
        google_search=types.GoogleSearch()
    )
]

# 3. Generar contenido
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="¿Cuál es el precio actual de Bitcoin y qué eventos lo movieron hoy?",
    config=types.GenerateContentConfig(
        tools=tools
    )
)

print(response.text)

# Para ver las fuentes de información (Grounding metadata)
if response.candidates[0].grounding_metadata:
    print("\nFuentes consultadas:")
    for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
        if chunk.web:
            print(f"- {chunk.web.title}: {chunk.web.uri}")