# ✅ Checklist de Migración a Vertex AI

## 📋 Pre-requisitos

### Cuenta y Proyecto GCP
- [ ] Tienes una cuenta de Google Cloud Platform
- [ ] Has creado un proyecto GCP (o tienes acceso a uno existente)
- [ ] Tienes permisos de administrador o Editor en el proyecto
- [ ] Has verificado la facturación habilitada en el proyecto

### Herramientas Locales
- [ ] Python 3.10 o superior instalado
- [ ] pip actualizado (`python -m pip install --upgrade pip`)
- [ ] gcloud CLI instalado ([Descargar](https://cloud.google.com/sdk/docs/install))
- [ ] Git instalado (para control de versiones)

---

## 🔧 Configuración de GCP

### 1. Configurar gcloud CLI
- [ ] Ejecutar: `gcloud init`
- [ ] Seleccionar el proyecto correcto
- [ ] Verificar: `gcloud config list`

### 2. Habilitar APIs
- [ ] Vertex AI API: `gcloud services enable aiplatform.googleapis.com`
- [ ] Google Calendar API: `gcloud services enable calendar-json.googleapis.com`
- [ ] Google Tasks API: `gcloud services enable tasks.googleapis.com`
- [ ] (Opcional) Custom Search API: `gcloud services enable customsearch.googleapis.com`
- [ ] Verificar: `gcloud services list --enabled`

### 3. Configurar Autenticación
Elegir una opción:

**Opción A: Desarrollo Local**
- [ ] Ejecutar: `gcloud auth application-default login`
- [ ] Completar el flujo de OAuth en el navegador
- [ ] Verificar el archivo de credenciales se creó en `%APPDATA%\gcloud\application_default_credentials.json`

**Opción B: Service Account (Producción)**
- [ ] Ir a IAM & Admin > Service Accounts en GCP Console
- [ ] Crear Service Account con nombre descriptivo
- [ ] Asignar roles: `Vertex AI User`, `Cloud AI Platform User`
- [ ] Crear y descargar clave JSON
- [ ] Configurar: `$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\key.json"`

### 4. Configurar Permisos
- [ ] Verificar que tu usuario/SA tiene rol `Vertex AI User`
- [ ] (Opcional) Agregar `Cloud AI Platform User` si usas otras APIs
- [ ] (Opcional) Agregar `Service Usage Consumer` para usar APIs

### 5. Configurar Región
- [ ] Decidir región (recomendado: `us-central1`)
- [ ] Verificar disponibilidad de modelos en la región elegida
- [ ] Anotar el nombre de la región para usarlo en `.env`

---

## 📦 Actualización del Proyecto

### 1. Backup del Código Actual
- [ ] Crear branch de backup: `git checkout -b backup-genai-sdk`
- [ ] Commit del estado actual: `git commit -am "Backup before Vertex AI migration"`
- [ ] (Opcional) Push a remote: `git push origin backup-genai-sdk`

### 2. Actualizar Dependencias
- [ ] Revisar `requirements.txt` actual
- [ ] Desinstalar GenAI SDK: `pip uninstall google-genai -y`
- [ ] Actualizar `requirements.txt` con `google-cloud-aiplatform>=1.38.0`
- [ ] Instalar nuevas dependencias: `pip install -r requirements.txt`
- [ ] Verificar instalación: `python -c "import vertexai; print('OK')"`

### 3. Actualizar Variables de Entorno
- [ ] Hacer backup de `.env` actual (si existe)
- [ ] Copiar `.env.example` a `.env`
- [ ] Editar `.env` y configurar:
  - [ ] `GCP_PROJECT_ID=tu-proyecto-id`
  - [ ] `GCP_LOCATION=us-central1` (o tu región preferida)
  - [ ] Otras variables existentes (Telegram, Calendar, etc.)
- [ ] **Remover** `GOOGLE_GEMINI_API_KEY` (ya no se necesita)

### 4. Actualizar Código
- [ ] ✅ Archivo `gemini_agent.py` actualizado (ya hecho)
- [ ] Verificar imports en otros archivos que usen GenAI
- [ ] Buscar referencias a `google.genai` en todo el proyecto
- [ ] Actualizar tests si los hay

---

## 🧪 Verificación y Pruebas

### 1. Test de Configuración
- [ ] Ejecutar: `python test_vertex_setup.py`
- [ ] Verificar que todas las verificaciones pasan (✅)
- [ ] Revisar mensaje final de confirmación
- [ ] Anotar cualquier advertencia o error

### 2. Tests Unitarios
- [ ] Ejecutar tests existentes del proyecto
- [ ] Verificar que no hay errores relacionados con GenAI
- [ ] Actualizar tests que fallen debido a cambios en la API

### 3. Test de Integración
- [ ] Ejecutar el nodo de speech_2_text
- [ ] Enviar un mensaje de prueba
- [ ] Verificar respuesta del modelo
- [ ] Verificar function calling funciona correctamente
- [ ] Verificar logs no muestran errores

### 4. Test de Function Calling
- [ ] Probar función de Telegram
- [ ] Probar función de Calendar
- [ ] Probar función de Tasks
- [ ] Probar función de Web Search (si aplica)

---

## 💰 Configuración de Costos

### 1. Configurar Presupuesto
- [ ] Ir a Billing > Budgets & Alerts en GCP Console
- [ ] Crear presupuesto mensual (ej: $50)
- [ ] Configurar alertas:
  - [ ] 50% del presupuesto
  - [ ] 90% del presupuesto
  - [ ] 100% del presupuesto
- [ ] Agregar email de notificación

### 2. Configurar Quotas
- [ ] Ir a IAM & Admin > Quotas
- [ ] Buscar "Vertex AI API"
- [ ] Revisar límites actuales
- [ ] (Opcional) Solicitar aumento si es necesario

### 3. Monitoreo
- [ ] Configurar dashboard en Cloud Console para Vertex AI
- [ ] Agregar métricas de uso
- [ ] Agregar métricas de costos
- [ ] Configurar alertas de uso inusual

---

## 📚 Documentación

### 1. Actualizar README
- [ ] ✅ Mencionar uso de Vertex AI (ya hecho)
- [ ] Actualizar sección de configuración
- [ ] Agregar link a guía de setup
- [ ] Actualizar instrucciones de instalación

### 2. Documentar Cambios
- [ ] Crear entry en CHANGELOG (si existe)
- [ ] Documentar breaking changes
- [ ] Documentar nuevos requisitos
- [ ] Documentar proceso de migración

### 3. Compartir Conocimiento
- [ ] Revisar documentos creados:
  - [ ] `VERTEX_AI_SETUP.md` - Guía completa
  - [ ] `MIGRACION_RESUMEN.md` - Resumen rápido
  - [ ] `COMPARACION_GENAI_VERTEXAI.md` - Comparación
- [ ] Compartir con el equipo
- [ ] Programar sesión de Q&A si es necesario

---

## 🚀 Despliegue

### Desarrollo
- [ ] Merge de cambios a branch de desarrollo
- [ ] CI/CD actualizado con nuevas variables
- [ ] Tests automáticos pasan
- [ ] Deploy a ambiente de desarrollo
- [ ] Pruebas manuales en desarrollo

### Staging
- [ ] Deploy a ambiente de staging
- [ ] Configurar credenciales de staging
- [ ] Ejecutar suite completa de tests
- [ ] Pruebas de carga (opcional)
- [ ] Validación de stakeholders

### Producción
- [ ] Crear tag de versión: `git tag v2.0.0-vertex-ai`
- [ ] Backup de configuración actual de producción
- [ ] Plan de rollback preparado
- [ ] Deploy a producción en ventana de mantenimiento
- [ ] Monitoreo activo post-deploy (primeras 24 horas)
- [ ] Verificar logs y métricas
- [ ] Confirmar funcionamiento con usuarios

---

## 🔒 Seguridad

### 1. Credenciales
- [ ] Verificar que `.env` está en `.gitignore`
- [ ] Verificar que service account keys no están en git
- [ ] Rotar API keys antiguas de GenAI (si las guardaste)
- [ ] Documentar ubicación segura de credenciales

### 2. Permisos
- [ ] Principio de menor privilegio aplicado
- [ ] Service Accounts con roles específicos
- [ ] Revisar logs de acceso en IAM
- [ ] Configurar alertas de acceso sospechoso

### 3. Auditoría
- [ ] Habilitar Cloud Audit Logs
- [ ] Configurar retención de logs (90 días mínimo)
- [ ] Revisar accesos recientes
- [ ] Documentar políticas de seguridad

---

## 📊 Monitoreo Post-Migración

### Primera Semana
- [ ] Día 1: Revisar logs cada 2 horas
- [ ] Día 2-3: Revisar logs cada 4 horas
- [ ] Día 4-7: Revisar logs diariamente
- [ ] Verificar costos diarios
- [ ] Verificar latencias están dentro de lo esperado
- [ ] Recolectar feedback de usuarios

### Primer Mes
- [ ] Revisar costos semanalmente
- [ ] Comparar con costos anteriores (GenAI)
- [ ] Identificar optimizaciones posibles
- [ ] Ajustar quotas si es necesario
- [ ] Optimizar prompts si latencia es alta

---

## ✨ Optimizaciones (Opcional)

### Performance
- [ ] Evaluar cambio a modelo Pro si se necesita mayor calidad
- [ ] Implementar caching de responses comunes
- [ ] Optimizar system instructions
- [ ] Reducir temperature si responses son inconsistentes

### Costos
- [ ] Analizar patrones de uso
- [ ] Implementar rate limiting si es necesario
- [ ] Considerar batch processing para tareas no críticas
- [ ] Optimizar longitud de prompts

### Features
- [ ] Explorar Google Search grounding
- [ ] Implementar conversaciones multi-turn más largas
- [ ] Agregar streaming de responses
- [ ] Implementar safety settings personalizados

---

## 🆘 Plan de Contingencia

### Si algo sale mal:

**Problema: Credenciales no funcionan**
- [ ] Verificar: `gcloud auth list`
- [ ] Re-autenticar: `gcloud auth application-default login`
- [ ] Verificar permisos en IAM

**Problema: Modelo no responde**
- [ ] Verificar API habilitada
- [ ] Verificar región tiene el modelo
- [ ] Revisar quotas no excedidas
- [ ] Verificar logs en Cloud Console

**Problema: Costos muy altos**
- [ ] Activar alertas de presupuesto inmediatamente
- [ ] Revisar logs de uso
- [ ] Implementar rate limiting temporal
- [ ] Contactar soporte de GCP

**Plan de Rollback:**
- [ ] Branch de backup guardado
- [ ] Proceso documentado para volver a GenAI SDK
- [ ] Variables de entorno antiguas guardadas
- [ ] Tiempo estimado de rollback: 30 minutos

---

## 📞 Recursos de Ayuda

### Documentación
- [ ] [Vertex AI Docs](https://cloud.google.com/vertex-ai/docs) bookmarked
- [ ] [Gemini API Reference](https://cloud.google.com/vertex-ai/docs/reference) bookmarked
- [ ] [Troubleshooting Guide](https://cloud.google.com/vertex-ai/docs/troubleshooting) bookmarked

### Soporte
- [ ] Email de soporte de GCP configurado
- [ ] Canal de Slack/Teams con el equipo
- [ ] Contacto de Google Cloud rep (si aplica)

---

## ✅ Sign-off Final

### Antes de marcar como completo:
- [ ] Todas las pruebas pasan
- [ ] Documentación actualizada
- [ ] Equipo notificado de cambios
- [ ] Monitoreo configurado
- [ ] Alertas de costos activas
- [ ] Plan de rollback documentado y probado
- [ ] Stakeholders aprueban deploy

### Firma de Aprobación:
- [ ] Desarrollador: _____________ Fecha: _______
- [ ] Tech Lead: _____________ Fecha: _______
- [ ] DevOps: _____________ Fecha: _______

---

**🎉 ¡Migración Completada!**

Fecha de finalización: ___________
Versión: v2.0.0-vertex-ai
Próxima revisión: ___________
