# Resumen: Migración a Vertex AI - Guía Rápida

## ✅ Cambios Realizados

### Archivos Modificados:
1. **gemini_agent.py** - Migrado de Google GenAI SDK a Vertex AI SDK
2. **requirements.txt** - Actualizado `google-genai` → `google-cloud-aiplatform`
3. **.env.example** - Nueva configuración para Vertex AI
4. **README.md** - Actualizado con referencias a la nueva configuración

### Archivos Nuevos:
1. **VERTEX_AI_SETUP.md** - Guía completa de configuración (en español)
2. **test_vertex_setup.py** - Script de verificación de configuración
3. **setup_vertex_ai.ps1** - Script automático de configuración para Windows

---

## 🚀 Inicio Rápido (3 Pasos)

### 1️⃣ Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2️⃣ Configurar GCP (Opción A: Automático)
```powershell
.\setup_vertex_ai.ps1
```

### 2️⃣ Configurar GCP (Opción B: Manual)
```bash
# Habilitar APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable calendar-json.googleapis.com
gcloud services enable tasks.googleapis.com

# Autenticar
gcloud auth application-default login

# Crear .env
cp .env.example .env
# Edita .env y agrega tu GCP_PROJECT_ID
```

### 3️⃣ Verificar
```bash
python test_vertex_setup.py
```

---

## 📝 Configuración de .env

**Mínimo requerido:**
```env
GCP_PROJECT_ID=tu-proyecto-gcp-id
GCP_LOCATION=us-central1
```

**Completo (con opcionales):**
```env
# Vertex AI (REQUERIDO)
GCP_PROJECT_ID=tu-proyecto-gcp-id
GCP_LOCATION=us-central1

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=tu_token_telegram

# Google Calendar (opcional)
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# Web Search (opcional)
SERPER_API_KEY=tu_api_key_serper

# Google Tasks (opcional)
GOOGLE_TASKS_LIST_ID=@default
```

---

## 🔑 Autenticación

### Desarrollo Local (Recomendado):
```bash
gcloud auth application-default login
```

### Producción (Service Account):
```bash
# Descargar service-account-key.json desde GCP Console
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\a\service-account-key.json"
```

---

## 🌍 Regiones Recomendadas

| Región | Ubicación | Uso |
|--------|-----------|-----|
| `us-central1` | Iowa, USA | ⭐ **Recomendada** |
| `us-east1` | South Carolina | Alternativa USA |
| `europe-west1` | Bélgica | Europa |
| `asia-northeast1` | Tokio | Asia |

---

## 💡 Diferencias Principales

### Antes (GenAI SDK):
```python
from google import genai
client = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)
chat = client.chats.create(model='gemini-3-flash-preview')
```

### Ahora (Vertex AI):
```python
import vertexai
vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
model = GenerativeModel('gemini-1.5-pro-002-002')
chat = model.start_chat()
```

---

## 🔧 Comandos Útiles

### Verificar configuración actual:
```bash
gcloud config list
```

### Listar proyectos:
```bash
gcloud projects list
```

### Ver APIs habilitadas:
```bash
gcloud services list --enabled
```

### Ver credenciales actuales:
```bash
gcloud auth list
```

---

## ❌ Problemas Comunes

### "Could not find Application Default Credentials"
**Solución:**
```bash
gcloud auth application-default login
```

### "Permission denied on aiplatform.googleapis.com"
**Solución:**
```bash
gcloud services enable aiplatform.googleapis.com
```

### "Model not found in region"
**Solución:** Cambia `GCP_LOCATION` a `us-central1` en tu `.env`

### "Quota exceeded"
**Solución:** Ve a GCP Console → IAM & Admin → Quotas y solicita aumento

---

## 💰 Costos Aproximados

### Gemini 1.5 Flash (Recomendado):
- **Input:** $0.000075 por 1K caracteres (~$0.075 por 1M)
- **Output:** $0.0003 por 1K caracteres (~$0.30 por 1M)

### Ejemplo:
- 100 conversaciones/día
- ~500 palabras por conversación
- **Costo mensual:** ~$5-10 USD

**💡 Tip:** Configura alertas de presupuesto en GCP Console → Billing

---

## 📚 Recursos

- 📖 [Guía Completa (VERTEX_AI_SETUP.md)](VERTEX_AI_SETUP.md)
- 🔗 [Vertex AI Docs](https://cloud.google.com/vertex-ai/docs)
- 🔗 [Gemini API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini)
- 🔗 [GCP Console](https://console.cloud.google.com/)

---

## ✅ Checklist de Verificación

- [ ] Python 3.10+ instalado
- [ ] gcloud CLI instalado y configurado
- [ ] Proyecto GCP creado
- [ ] APIs habilitadas (Vertex AI, Calendar, Tasks)
- [ ] Autenticación configurada (ADC)
- [ ] Archivo `.env` creado con `GCP_PROJECT_ID`
- [ ] `pip install -r requirements.txt` ejecutado
- [ ] `python test_vertex_setup.py` exitoso
- [ ] Alertas de costos configuradas en GCP

---

## 🆘 Soporte

¿Problemas? Revisa en este orden:
1. Ejecuta `python test_vertex_setup.py` para diagnóstico
2. Verifica `gcloud auth list` para ver credenciales activas
3. Revisa logs de errores en la salida de la aplicación
4. Consulta [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) para detalles
5. Revisa [Vertex AI troubleshooting](https://cloud.google.com/vertex-ai/docs/troubleshooting)
