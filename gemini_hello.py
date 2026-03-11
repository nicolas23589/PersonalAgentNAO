#!/usr/bin/env python3
"""
Script de ejemplo: agente simple con Gemini.
Nota: La API de Gemini no expone el tipo de plan ni cuotas directamente.
Para revisar tu plan y límites visita:
  - https://aistudio.google.com/plan
  - https://ai.dev/rate-limit
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Cargar .env desde la raíz del proyecto (si existe)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

if not API_KEY:
    raise EnvironmentError(
        "No se encontró GOOGLE_GEMINI_API_KEY.\n"
        "Agrégala en el archivo .env de la raíz del proyecto o como variable de entorno."
    )

client = genai.Client(api_key=API_KEY)

# Crear un chat (agente simple con historial)
chat = client.chats.create(
    model='gemini-3-flash-preview',
    config=genai.types.GenerateContentConfig(
        system_instruction=(
            "Eres un asistente personal amigable y conciso. "
            "Responde siempre de forma breve y en español."
        ),
        temperature=0.7,
    )
)

# Enviar mensaje con detección de límite de cuota
try:
    response = chat.send_message("Hola")
    print("✅ API key válida y activa.")
    print("\nRespuesta del agente:")
    print(response.text)
except Exception as e:
    error_str = str(e)
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
        print("⚠️  API key válida pero cuota agotada (plan gratuito o límite alcanzado).")
        print("   Revisa tu uso en: https://ai.dev/rate-limit")
        print("   Revisa tu plan en: https://aistudio.google.com/plan")
    elif "401" in error_str or "API_KEY_INVALID" in error_str:
        print("❌ API key inválida o revocada.")
    elif "403" in error_str or "PERMISSION_DENIED" in error_str:
        print("❌ API key sin permisos para este modelo.")
    else:
        print(f"❌ Error inesperado: {e}")

