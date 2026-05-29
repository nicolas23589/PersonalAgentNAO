# NAO Emotion Detection WS (ROS2 Jazzy)

Este repositorio contiene el workspace de ROS2 Jazzy desarrollado para implementar un modelo afectivo en el robot humanoide NAO V6 (Orion). La propuesta busca mejorar la interacción social del robot mediante un pipeline modular que integra percepción multimodal, planeación con un modelo de lenguaje y ejecución de comportamientos verbales y no verbales.

El sistema fue construido como parte de un proyecto de grado en Ingeniería de Sistemas y Computación de la Universidad de los Andes (Bogotá, Colombia).

> **🆕 ACTUALIZACIÓN:** El sistema ahora usa **Google Vertex AI** en lugar de Google GenAI SDK.  
> Consulta [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md) para la guía completa de migración y configuración.

---

## Objetivo general

Dotar al NAO V6 de un modelo afectivo capaz de reconocer señales del usuario (voz, emoción facial y contexto visual) para generar respuestas empáticas y coherentes, manteniendo una arquitectura modular en ROS2 que pueda extenderse fácilmente.

---

## Estructura del repositorio

- `src/`: paquetes ROS2 del sistema.
- `compile.sh`: compila el workspace con `colcon`.
- `run_emotion.sh`: ejecuta la interacción completa (pipeline integrado).
- `dump_nao_services.sh` / `nao_services.txt`: scripts y listado de servicios NAOqi usados como referencia.
- `.env.example`: ejemplo de variables de entorno necesarias (no contiene credenciales reales).
- `.gitignore`: excluye archivos locales y sensibles (build, logs, .env, venv, etc.).

---

## Requisitos

**Software**
- ROS2 Jazzy instalado y configurado.
- Python 3.10+.
- Colcon (`colcon build`).
- Dependencias Python requeridas por cada paquete (por ejemplo: OpenCV, requests, etc.).
- Deependencias incluidas en requirements.txt, para esto correr el comando `pip install -r requirements.txt`

**Hardware**
- Robot NAO V6 con NAOqi activo.
- `naoqi_bridge` configurado para ROS2 y conectado al robot.
- Cámara frontal del NAO operativa.

---

## Configuración de variables de entorno

Este proyecto utiliza **Google Vertex AI** para el modelo de lenguaje Gemini.  
Las credenciales se gestionan mediante **Application Default Credentials (ADC)** de GCP.

### Configuración Rápida

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```

2. Edita `.env` y configura:
   ```env
   GCP_PROJECT_ID=tu-proyecto-gcp-id
   GCP_LOCATION=us-central1
   ```

3. Configura las credenciales de GCP:
   ```bash
   gcloud auth application-default login
   ```


📖 **Para instrucciones detalladas:** consulta [VERTEX_AI_SETUP.md](VERTEX_AI_SETUP.md)

> Nota: `.env` no se sube al repositorio por seguridad.

---

## Compilación

Desde la raíz del workspace:

```bash
bash compile.sh
```

Esto ejecuta `colcon build` y deja el workspace listo para correr.

---

## Ejecución del sistema completo

```bash
bash run_emotion.sh
```

Este script lanza el flujo integrado de interacción con Orion:

1. **Tap 1** en la cabeza: inicia captura multimodal (audio + imagen + contexto).  
   - LEDs en ojos: **amarillo** (grabando).

2. **Tap 2** en la cabeza: finaliza captura y dispara inferencias.  
   - LEDs en ojos: **verde** (captura finalizada y procesando).

3. El LLM genera un plan en JSON con acciones válidas.  
4. El Behavior Renderer ejecuta el plan en secuencia.  
   - LEDs en ojos: **morado** (interacción por finalizar).

---

## Paquetes principales (resumen)

La arquitectura está compuesta por módulos desacoplados que se comunican vía tópicos:

- **Speech2Text Node:** transcripción de voz con Whisper.
Se puede ejecutar con el comando ros2 run speech_2_text speech_2_text_node
- **EmotionClassifier Node:** clasificación emocional facial a partir de la cámara frontal.
- **Context Node:** descripción de contexto visual para enriquecer la conversación.
Se puede ejecutar con el comando ros2 run context_node context_node
- **LLM Bridge Node:** generación de plan de interacción usando un modelo de lenguaje (JSON).
Se puede ejecutar con ros2 run llm_bridge llm_bridge_node
- **Behavior Renderer Node:** ejecución de voz, posturas, animaciones y LEDs mediante NAOqi.

Cada paquete se encuentra dentro de `src/` y puede ser ejecutado individualmente para pruebas unitarias.

---

## Notas de uso

- Si no hay API Key configurada, el sistema mantiene robustez devolviendo respuestas neutrales donde aplique.
- La latencia puede variar según disponibilidad de red y modelo LLM utilizado.
- Se recomienda ejecutar en red estable para pruebas con usuarios.

---

## Validación

El sistema fue validado mediante:
- Pruebas unitarias por módulo.
- Pruebas de integración del pipeline completo.
- Pruebas con usuarios reales (n = 22), con encuestas Likert y preguntas abiertas.

Los resultados mostraron alta aceptación en claridad, comprensión de intención, empatía y comodidad, con oportunidad de mejora en latencia y naturalidad verbal.

---

## Autor

Proyecto desarrollado por:  
**Juan Pablo Peña Jaime**  (Emociones)
**Nicolas Migul Murillo Cristancho**  (Integraciones con tool-calling)

### Equipo de Apoyo

Profesor asesor: 
**Fernando De la Rosa Rosero.**

Asistente graduado: 
**David Cuevas Alba.**


**Universidad de los Andes – Ingeniería de Sistemas y Computación  
Bogotá, Colombia<br>
Agosto - Diciembre (2025)**

---

## Licencia

Este repositorio se publica con fines académicos.  
Si deseas reutilizar código o extender el sistema, por favor cita el proyecto y conserva los créditos correspondientes.




