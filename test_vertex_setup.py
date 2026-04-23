#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Vertex AI
Ejecuta este script después de configurar tu entorno para verificar que todo funciona correctamente.
"""

import os
import sys
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
_env_file = os.getenv('DOTENV_PATH') or find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
if _env_file:
    load_dotenv(dotenv_path=_env_file)
    print(f"✅ Archivo .env cargado desde: {_env_file}")
else:
    print("⚠️  No se encontró archivo .env")
    sys.exit(1)

# Verificar variables de entorno
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'us-central1')

print("\n" + "="*60)
print("VERIFICACIÓN DE CONFIGURACIÓN DE VERTEX AI")
print("="*60 + "\n")

# 1. Verificar variables de entorno
print("1️⃣  Verificando variables de entorno...")
if not GCP_PROJECT_ID:
    print("   ❌ GCP_PROJECT_ID no está configurado en .env")
    print("   Por favor, agrega: GCP_PROJECT_ID=tu-proyecto-id")
    sys.exit(1)
else:
    print(f"   ✅ GCP_PROJECT_ID: {GCP_PROJECT_ID}")
    print(f"   ✅ GCP_LOCATION: {GCP_LOCATION}")

# 2. Verificar instalación de Vertex AI SDK
print("\n2️⃣  Verificando instalación de Vertex AI SDK...")
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    print("   ✅ Vertex AI SDK instalado correctamente")
except ImportError as e:
    print(f"   ❌ Error al importar Vertex AI SDK: {e}")
    print("   Ejecuta: pip install google-cloud-aiplatform>=1.38.0")
    sys.exit(1)

# 3. Verificar credenciales de autenticación
print("\n3️⃣  Verificando credenciales de autenticación...")
try:
    import google.auth
    credentials, project = google.auth.default()
    print(f"   ✅ Credenciales encontradas")
    print(f"   ✅ Proyecto por defecto: {project or 'N/A'}")
except Exception as e:
    print(f"   ❌ No se encontraron credenciales: {e}")
    print("\n   Solución:")
    print("   1. Ejecuta: gcloud auth application-default login")
    print("   2. O configura GOOGLE_APPLICATION_CREDENTIALS con tu service account")
    sys.exit(1)

# 4. Inicializar Vertex AI
print("\n4️⃣  Inicializando Vertex AI...")
try:
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    print(f"   ✅ Vertex AI inicializado en proyecto: {GCP_PROJECT_ID}")
    print(f"   ✅ Región: {GCP_LOCATION}")
except Exception as e:
    print(f"   ❌ Error al inicializar Vertex AI: {e}")
    print("\n   Posibles causas:")
    print("   1. El proyecto no existe o no tienes acceso")
    print("   2. La API de Vertex AI no está habilitada")
    print("   3. No tienes los permisos necesarios")
    sys.exit(1)

# 5. Probar el modelo Gemini
print("\n5️⃣  Probando modelo Gemini...")
try:
    model = GenerativeModel(
        model_name="gemini-2.5-pro",
        generation_config=GenerationConfig(temperature=0.7)
    )
    print("   ✅ Modelo Gemini cargado correctamente")
    
    # Hacer una petición simple
    print("\n   📤 Enviando mensaje de prueba al modelo...")
    response = model.generate_content(" Puedes mandarme un mensaje de hola al telegram?.")
    
    if response and response.text:
        print(f"   📥 Respuesta del modelo:")
        print(f"   '{response.text.strip()}'")
        print("\n   ✅ ¡El modelo respondió correctamente!")
    else:
        print("   ⚠️  El modelo no generó respuesta")
        
except Exception as e:
    print(f"   ❌ Error al usar el modelo: {e}")
    print("\n   Posibles causas:")
    print("   1. El modelo no está disponible en tu región")
    print("   2. Cuota excedida o problemas de facturación")
    print("   3. Permisos insuficientes")
    sys.exit(1)

# 6. Verificar APIs opcionales
print("\n6️⃣  Verificando APIs opcionales...")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if TELEGRAM_BOT_TOKEN:
    print("   ✅ TELEGRAM_BOT_TOKEN configurado")
else:
    print("   ⚠️  TELEGRAM_BOT_TOKEN no configurado (opcional)")

# Serper (búsqueda web)
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
if SERPER_API_KEY:
    print("   ✅ SERPER_API_KEY configurado")
else:
    print("   ⚠️  SERPER_API_KEY no configurado (opcional)")

# Resumen final
print("\n" + "="*60)
print("✅ CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
print("="*60)
print("\nTu entorno está listo para usar Vertex AI.")
print("Puedes ejecutar tu aplicación con confianza.")
print("\nPróximos pasos:")
print("  1. Ejecuta tu aplicación principal")
print("  2. Configura las APIs opcionales si las necesitas")
print("  3. Revisa los logs para confirmar el funcionamiento")
print("\n" + "="*60 + "\n")
