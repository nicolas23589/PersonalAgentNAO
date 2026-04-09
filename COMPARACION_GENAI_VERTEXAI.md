# Comparación: GenAI SDK vs Vertex AI

## 📊 Tabla Comparativa

| Aspecto | Google GenAI SDK | Google Vertex AI |
|---------|------------------|------------------|
| **Autenticación** | API Key | Application Default Credentials |
| **Setup** | `genai.Client(api_key=...)` | `vertexai.init(project=..., location=...)` |
| **Ubicación** | Global | Por región (us-central1, etc.) |
| **Modelos** | Preview models | Production-ready models |
| **Pricing** | Pay-per-use | Pay-per-use con mejores controles |
| **Quotas** | Limitadas | Configurables y escalables |
| **Enterprise** | No | Sí (auditoría, VPC, etc.) |
| **Grounding** | Limitado | Full Google Search integration |
| **Producción** | Beta/Preview | Production-ready |

---

## 🔄 Comparación de Código

### Importaciones

**Antes (GenAI SDK):**
```python
from google import genai
from google.genai import types
```

**Ahora (Vertex AI):**
```python
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    GenerationConfig,
    Content,
    Part
)
```

---

### Inicialización

**Antes (GenAI SDK):**
```python
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)
```

**Ahora (Vertex AI):**
```python
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'us-central1')
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
```

---

### Configuración de Tools

**Antes (GenAI SDK):**
```python
tools = [
    types.Tool(
        function_declarations=AVAILABLE_TOOLS
    )
]
```

**Ahora (Vertex AI):**
```python
vertex_functions = []
for func_dict in AVAILABLE_TOOLS:
    vertex_func = FunctionDeclaration(
        name=func_dict.get('name'),
        description=func_dict.get('description'),
        parameters=func_dict.get('parameters', {})
    )
    vertex_functions.append(vertex_func)

tools = [Tool(function_declarations=vertex_functions)]
```

---

### Creación del Modelo/Chat

**Antes (GenAI SDK):**
```python
chat = client.chats.create(
    model='gemini-3-flash-preview',
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=tools,
        temperature=0.7,
    )
)
```

**Ahora (Vertex AI):**
```python
model = GenerativeModel(
    model_name='gemini-1.5-pro-002-002',
    system_instruction=[SYSTEM_INSTRUCTION],
    tools=tools,
    generation_config=GenerationConfig(
        temperature=0.7,
    )
)
chat = model.start_chat()
```

---

### Enviar Mensaje

**Antes (GenAI SDK):**
```python
response = self.chat.send_message(user_message)
```

**Ahora (Vertex AI):**
```python
response = self.chat.send_message(user_message)
```
✅ **Sin cambios** - La API es compatible

---

### Function Response

**Antes (GenAI SDK):**
```python
response = self.chat.send_message(
    types.Part(
        function_response=types.FunctionResponse(
            name=function_name,
            response=function_result
        )
    )
)
```

**Ahora (Vertex AI):**
```python
response = self.chat.send_message(
    Part.from_function_response(
        name=function_name,
        response=function_result
    )
)
```

---

### Procesar Response

**Antes (GenAI SDK):**
```python
function_call = response.candidates[0].content.parts[0].function_call
function_name = function_call.name
function_args = dict(function_call.args)
```

**Ahora (Vertex AI):**
```python
function_call = response.candidates[0].content.parts[0].function_call
function_name = function_call.name
function_args = dict(function_call.args) if function_call.args else {}
```
⚠️ **Pequeña diferencia:** Manejo de args vacíos

---

## 🔐 Autenticación

### GenAI SDK (API Key)

**Variables de entorno:**
```env
GOOGLE_GEMINI_API_KEY=AIza...
```

**Código:**
```python
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)
```

**Seguridad:**
- ⚠️ API Key visible en logs si no se tiene cuidado
- ⚠️ Fácil de filtrar accidentalmente
- ✅ Simple de configurar

---

### Vertex AI (ADC)

**Variables de entorno:**
```env
GCP_PROJECT_ID=mi-proyecto
GCP_LOCATION=us-central1
```

**Configuración de credenciales:**
```bash
# Opción 1: Usuario (desarrollo)
gcloud auth application-default login

# Opción 2: Service Account (producción)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

**Código:**
```python
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
# Las credenciales se detectan automáticamente
```

**Seguridad:**
- ✅ No hay API Keys en el código
- ✅ Auditoría completa en GCP
- ✅ Rotación automática de credenciales
- ✅ Control granular de permisos (IAM)

---

## 📦 Dependencias

### GenAI SDK
```txt
google-genai>=0.1.0
```

### Vertex AI
```txt
google-cloud-aiplatform>=1.38.0
```

**Nota:** Vertex AI incluye más funcionalidades (AutoML, Pipelines, etc.)

---

## 🌍 Modelos Disponibles

### GenAI SDK
- `gemini-2-flash-preview` (experimental)
- `gemini-3-flash-preview` (experimental)
- Modelos en preview/beta

### Vertex AI
- `gemini-1.5-pro-002-002` ⭐ **Recomendado**
- `gemini-1.5-pro-002`
- `gemini-1.0-pro`
- Modelos estables para producción

---

## 💡 Ventajas de Vertex AI

### Para Desarrollo:
- ✅ Mejor integración con otros servicios de GCP
- ✅ Logs centralizados en Cloud Logging
- ✅ Debugging más fácil con Cloud Trace
- ✅ No necesitas gestionar API Keys

### Para Producción:
- ✅ SLAs empresariales
- ✅ Soporte técnico de Google Cloud
- ✅ Cumplimiento (HIPAA, SOC 2, etc.)
- ✅ VPC Service Controls para mayor seguridad
- ✅ Quotas configurables y escalables

### Para Costos:
- ✅ Presupuestos y alertas integradas
- ✅ Análisis de costos detallado
- ✅ Compromisos de uso (discounts)

---

## 📈 Migración: Paso a Paso

### 1. Backup
```bash
git checkout -b backup-genai
git commit -am "Backup before Vertex AI migration"
```

### 2. Actualizar dependencias
```bash
pip uninstall google-genai
pip install google-cloud-aiplatform
```

### 3. Configurar GCP
```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com
```

### 4. Actualizar código
- Cambiar imports
- Cambiar inicialización
- Adaptar function declarations
- Ajustar function responses

### 5. Actualizar .env
```env
# Remover:
# GOOGLE_GEMINI_API_KEY=...

# Agregar:
GCP_PROJECT_ID=tu-proyecto-id
GCP_LOCATION=us-central1
```

### 6. Probar
```bash
python test_vertex_setup.py
```

---

## 🎯 Recomendaciones

### Cuándo usar GenAI SDK:
- ❌ Ya no se recomienda para nuevos proyectos
- ⚠️ Solo para prototipos rápidos
- ⚠️ Modelos experimentales/preview

### Cuándo usar Vertex AI:
- ✅ **Siempre** para producción
- ✅ Proyectos que usan otros servicios de GCP
- ✅ Necesitas auditoría y compliance
- ✅ Aplicaciones enterprise
- ✅ Escalabilidad y reliability

---

## 📞 Contacto y Soporte

- **Documentación Vertex AI:** https://cloud.google.com/vertex-ai/docs
- **API Reference:** https://cloud.google.com/vertex-ai/docs/reference
- **Ejemplos de código:** https://github.com/GoogleCloudPlatform/generative-ai
- **Foro de soporte:** https://cloud.google.com/support
