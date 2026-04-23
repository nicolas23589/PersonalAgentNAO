# Guía de Configuración: Migración a Google Vertex AI

## 📋 Resumen de Cambios

Se ha migrado el código de **Google GenAI SDK** a **Google Vertex AI** para aprovechar las capacidades empresariales de GCP.

### Ventajas de Vertex AI:
- ✅ Integración nativa con GCP
- ✅ Mejor control de cuotas y límites
- ✅ Soporte para modelos personalizados
- ✅ Auditoría y logging integrado
- ✅ Sin necesidad de API Keys (usa Application Default Credentials)
- ✅ Mejor para producción y escalabilidad

---

## 🔧 Configuración en Google Cloud Platform (GCP)

### 1. Crear o Seleccionar un Proyecto GCP

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el **Project ID** (lo necesitarás para el archivo `.env`)

### 2. Habilitar las APIs Necesarias

Debes habilitar las siguientes APIs en tu proyecto:

```bash
# Opción 1: Desde la consola web
# Ve a: APIs & Services > Library
# Busca y habilita cada una:
```

- **Vertex AI API** - Para usar Gemini y otros modelos
- **Google Calendar API** - Para la funcionalidad de calendario
- **Google Tasks API** - Para la funcionalidad de tareas
- **Custom Search API** - Para búsquedas web (opcional)

```bash
# Opción 2: Usando gcloud CLI (más rápido)
gcloud services enable aiplatform.googleapis.com
gcloud services enable calendar-json.googleapis.com
gcloud services enable tasks.googleapis.com
gcloud services enable customsearch.googleapis.com
```

### 3. Configurar Credenciales de Autenticación

Vertex AI usa **Application Default Credentials (ADC)**. Hay varias formas de configurarlas:

#### Opción A: Para Desarrollo Local (Recomendado)

```bash
# Instala gcloud CLI si no lo tienes
# https://cloud.google.com/sdk/docs/install

# Autentícate con tu cuenta de Google
gcloud auth application-default login

# Configura el proyecto por defecto
gcloud config set project TU-PROJECT-ID
```

Esto creará un archivo de credenciales en:
- **Windows**: `%APPDATA%\gcloud\application_default_credentials.json`
- **Linux/Mac**: `~/.config/gcloud/application_default_credentials.json`

#### Opción B: Usar Service Account (Para Producción)

1. Ve a **IAM & Admin > Service Accounts** en GCP Console
2. Crea una nueva Service Account:
   - Nombre: `nao-agent-service`
   - Roles necesarios:
     - `Vertex AI User`
     - `Cloud AI Platform User`
     - Otros según las funcionalidades (Calendar, Tasks, etc.)
3. Crea una clave JSON para la Service Account
4. Descarga el archivo JSON
5. Configura la variable de entorno:

```bash
# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\a\tu\service-account-key.json"

# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS="/ruta/a/tu/service-account-key.json"
```

### 4. Verificar las Regiones Disponibles

Vertex AI está disponible en varias regiones. Las más comunes:

- `us-central1` (Iowa) - **Recomendada**
- `us-east1` (South Carolina)
- `us-west1` (Oregon)
- `europe-west1` (Bélgica)
- `europe-west4` (Países Bajos)
- `asia-northeast1` (Tokio)

Verifica la disponibilidad de modelos en tu región:
https://cloud.google.com/vertex-ai/docs/general/locations

---

## 📝 Configuración del Archivo .env

Crea un archivo `.env` en la raíz del proyecto basándote en `.env.example`:

```bash
# Copia el ejemplo
cp .env.example .env

# Edita el archivo .env
```

Contenido mínimo del `.env`:

```dotenv
# ============ GOOGLE VERTEX AI ============
GCP_PROJECT_ID=tu-proyecto-gcp-id
GCP_LOCATION=us-central1

# ============ TELEGRAM BOT ============
TELEGRAM_BOT_TOKEN=tu_bot_token_de_telegram_aqui

# ============ GOOGLE CALENDAR API ============
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# ============ SERPER API (Web Search) ============
SERPER_API_KEY=tu_serper_api_key_aqui

# ============ GOOGLE TASKS API ============
GOOGLE_TASKS_LIST_ID=@default
```

### Notas importantes:
- **GCP_PROJECT_ID**: El ID de tu proyecto GCP (no el nombre)
- **GCP_LOCATION**: La región donde ejecutarás Vertex AI
- Las credenciales de autenticación (ADC) se detectan automáticamente, no necesitas especificarlas en el `.env`

---

## 📦 Instalación de Dependencias

```bash
# Instala las nuevas dependencias
pip install -r requirements.txt

# O instala solo el paquete de Vertex AI
pip install google-cloud-aiplatform>=1.38.0
```

---

## 🧪 Verificar la Configuración

### 1. Verifica que las credenciales funcionan:

```python
# test_vertex_setup.py
import vertexai
from vertexai.generative_models import GenerativeModel

# Configura con tus valores
PROJECT_ID = "tu-proyecto-id"
LOCATION = "us-central1"

vertexai.init(project=PROJECT_ID, location=LOCATION)

model = GenerativeModel("gemini-2.5-pro-002")
response = model.generate_content("Hola, ¿funcionas correctamente?")
print(response.text)
```

```bash
# Ejecuta el test
python test_vertex_setup.py
```

### 2. Verifica las APIs habilitadas:

```bash
gcloud services list --enabled --project=TU-PROJECT-ID | grep -E "aiplatform|calendar|tasks"
```

---

## 💰 Costos y Cuotas

### Precios de Vertex AI Gemini (aproximados):

- **Gemini 1.5 Flash**:
  - Input: $0.000075 por 1K caracteres
  - Output: $0.0003 por 1K caracteres
  
- **Gemini 1.5 Pro**:
  - Input: $0.00125 por 1K caracteres
  - Output: $0.005 por 1K caracteres

### Cuotas por Defecto:
- **Gemini 1.5 Flash**: 2,000 requests/minuto
- **Gemini 1.5 Pro**: 1,000 requests/minuto

Consulta precios actualizados: https://cloud.google.com/vertex-ai/pricing

### Configurar Alertas de Costos:

1. Ve a **Billing > Budgets & Alerts**
2. Crea un presupuesto mensual
3. Configura alertas al 50%, 90% y 100%

---

## 🔄 Diferencias Clave con GenAI SDK

### Cambios en el Código:

| GenAI SDK | Vertex AI SDK |
|-----------|---------------|
| `from google import genai` | `import vertexai` |
| `genai.Client(api_key=...)` | `vertexai.init(project=..., location=...)` |
| `types.Tool(...)` | `Tool(function_declarations=...)` |
| `client.chats.create()` | `model.start_chat()` |
| `types.Part(function_response=...)` | `Part.from_function_response(...)` |

### Modelos Disponibles:
- ✅ `gemini-2.5-pro-002` (recomendado)
- ✅ `gemini-2.5-pro`
- ✅ `gemini-1.0-pro`

---

## 🚨 Solución de Problemas Comunes

### Error: "Could not find Application Default Credentials"

**Solución:**
```bash
gcloud auth application-default login
```

### Error: "Permission denied on aiplatform.googleapis.com"

**Solución:**
1. Verifica que la API esté habilitada
2. Asegúrate de tener los permisos correctos:
```bash
gcloud projects add-iam-policy-binding TU-PROJECT-ID \
    --member="user:tu-email@gmail.com" \
    --role="roles/aiplatform.user"
```

### Error: "Model not found in region"

**Solución:**
- Verifica que el modelo esté disponible en tu región
- Cambia `GCP_LOCATION` a `us-central1` que tiene todos los modelos

### Error: "Quota exceeded"

**Solución:**
1. Ve a **IAM & Admin > Quotas**
2. Busca "Vertex AI API"
3. Solicita aumento de cuota si es necesario

---

## 📚 Recursos Adicionales

- [Documentación de Vertex AI](https://cloud.google.com/vertex-ai/docs)
- [Gemini API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini)
- [Function Calling en Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling)
- [Best Practices](https://cloud.google.com/vertex-ai/docs/generative-ai/learn/best-practices)

---

## ✅ Checklist de Configuración

- [ ] Proyecto GCP creado
- [ ] APIs habilitadas (Vertex AI, Calendar, Tasks)
- [ ] gcloud CLI instalado y configurado
- [ ] Autenticación configurada (ADC o Service Account)
- [ ] Archivo `.env` creado con valores correctos
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Test de verificación ejecutado exitosamente
- [ ] Alertas de costos configuradas

---

## 🆘 Soporte

Si encuentras problemas:
1. Verifica los logs de errores
2. Consulta la [documentación oficial](https://cloud.google.com/vertex-ai/docs)
3. Revisa los [ejemplos de código](https://github.com/GoogleCloudPlatform/generative-ai)
