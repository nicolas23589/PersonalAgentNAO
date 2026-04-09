# Guía de Configuración: Google Keep

## ⚠️ Importante

**Google Keep NO tiene una API oficial pública.** Esta integración usa `gkeepapi`, una biblioteca no oficial de Python que funciona mediante ingeniería inversa. 

### Limitaciones:
- ❌ No es una solución oficial de Google
- ❌ Puede dejar de funcionar si Google cambia su sistema
- ❌ No recomendado para producción crítica
- ⚠️ Requiere credenciales de cuenta de Google directas

### ¿Por qué usar Keep entonces?
- ✅ Es la única forma de integrar con Keep actualmente
- ✅ Funciona bien para proyectos personales y prototipos
- ✅ Mantiene sincronización con la app oficial de Keep

---

## 📋 Requisitos Previos

1. Una cuenta de Google (Gmail)
2. Verificación en 2 pasos habilitada
3. Python 3.7 o superior

---

## 🔧 Configuración Paso a Paso

### 1. Habilitar Verificación en 2 Pasos

Si no la tienes habilitada:

1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security)
2. En "Acceso a Google", selecciona **"Verificación en dos pasos"**
3. Sigue las instrucciones para habilitarla
4. Usa tu método preferido (SMS, app Authenticator, etc.)

### 2. Generar Contraseña de Aplicación

**IMPORTANTE:** No uses tu contraseña normal de Google, genera una específica para la aplicación.

1. Ve a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Es posible que debas ingresar tu contraseña de Google
3. En "Seleccionar app", elige **"Otra (nombre personalizado)"**
4. Escribe un nombre como: `NAO Agent - Keep`
5. Haz clic en **"Generar"**
6. Google mostrará una contraseña de 16 caracteres (ejemplo: `abcd efgh ijkl mnop`)
7. **Copia esta contraseña** (solo se muestra una vez)
8. Guárdala de forma segura

### 3. Instalar Dependencias

```bash
pip install gkeepapi
```

O instala todas las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Edita tu archivo `.env`:

```env
# ============ GOOGLE KEEP (No oficial) ============
GOOGLE_KEEP_EMAIL=tu_email@gmail.com
GOOGLE_KEEP_APP_PASSWORD=abcdefghijklmnop
```

**Notas:**
- Usa tu email completo (ejemplo: `juan@gmail.com`)
- La contraseña de aplicación NO tiene espacios
- Copia la contraseña exactamente como Google la generó

---

## ✅ Verificar la Configuración

### Opción 1: Script de Prueba

```bash
cd src/speech_2_text/speech_2_text/external_integrations
python keep_manager.py
```

Si todo está bien, verás:
```
============================================================
Google Keep Manager - Prueba
============================================================
[KeepManager] ✅ Autenticado exitosamente como tu_email@gmail.com

1. Creando nota de prueba...
Resultado: {'status': 'success', ...}
```

### Opción 2: Prueba Manual en Python

```python
from keep_manager import GoogleKeepManager

# Crear manager
manager = GoogleKeepManager()

# Crear una nota
result = manager.create_note(
    title="Prueba desde Python",
    content="Esta es una nota de prueba",
    color="BLUE"
)
print(result)
```

---

## 🎨 Colores Disponibles

Puedes usar estos colores para tus notas:

| Color | Descripción |
|-------|-------------|
| `DEFAULT` | Blanco/Predeterminado |
| `RED` | Rojo |
| `ORANGE` | Naranja |
| `YELLOW` | Amarillo |
| `GREEN` | Verde |
| `TEAL` | Verde azulado |
| `BLUE` | Azul |
| `DARKBLUE` | Azul oscuro |
| `PURPLE` | Morado |
| `PINK` | Rosa |
| `BROWN` | Café |
| `GRAY` | Gris |

---

## 🚀 Uso con el Agente NAO

Una vez configurado, el agente podrá:

### Crear Notas
**Usuario:** "Guarda esta receta: Mezcla 2 tazas de harina con 1 huevo"
**Agente:** Crea nota en Keep con el contenido

### Crear Listas
**Usuario:** "Crea una lista de compras con leche, pan y huevos"
**Agente:** Crea una checklist en Keep

### Buscar Notas
**Usuario:** "Busca mis notas sobre recetas"
**Agente:** Busca y lee las notas encontradas

---

## ❗ Solución de Problemas

### Error: "Login failed"

**Causa:** Credenciales incorrectas

**Solución:**
1. Verifica que el email sea correcto
2. Genera una nueva contraseña de aplicación
3. Asegúrate de copiar la contraseña sin espacios
4. Verifica que la verificación en 2 pasos esté habilitada

### Error: "BadAuthentication"

**Causa:** Google bloqueó el acceso

**Solución:**
1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security)
2. Revisa "Eventos de seguridad recientes"
3. Si hay un intento bloqueado, autorízalo
4. Intenta nuevamente

### Error: "Permission denied"

**Causa:** Contraseña de aplicación no válida

**Solución:**
1. Revoca la contraseña de aplicación anterior
2. Genera una nueva en [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Actualiza el `.env`

### Las notas no aparecen en Keep

**Causa:** Sincronización pendiente

**Solución:**
- Espera unos segundos y refresca la app de Keep
- El script llama a `keep.sync()` automáticamente
- Cierra y vuelve a abrir la app de Keep

---

## 🔒 Seguridad

### Mejores Prácticas:

✅ **Hacer:**
- Usar contraseñas de aplicación (no tu contraseña principal)
- Mantener el archivo `.env` fuera de Git
- Revocar contraseñas de aplicación que no uses
- Revisar accesos regularmente en Google Account

❌ **No Hacer:**
- Compartir tu contraseña de aplicación
- Subir el `.env` a repositorios públicos
- Usar tu contraseña principal de Google
- Dejar contraseñas en código fuente

### Revocar Acceso:

Si quieres revocar el acceso:
1. Ve a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Encuentra "NAO Agent - Keep"
3. Haz clic en el ícono de la papelera
4. Confirma la revocación

---

## 📚 Funciones Disponibles

### `create_note()`
Crea una nota de texto.

```python
manager.create_note(
    title="Mi Nota",
    content="Contenido de la nota",
    color="BLUE",      # Opcional
    pinned=True        # Opcional
)
```

### `create_list()`
Crea una lista de verificación (checklist).

```python
manager.create_list(
    title="Lista de Compras",
    items=["Leche", "Pan", "Huevos"],
    color="GREEN",     # Opcional
    pinned=False       # Opcional
)
```

### `search_notes()`
Busca notas por palabra clave.

```python
manager.search_notes(
    query="recetas",
    max_results=5      # Opcional
)
```

---

## 🔄 Alternativas a Google Keep

Si prefieres usar APIs oficiales:

### Google Tasks API ✅ (Ya implementado)
- API oficial de Google
- Perfecto para tareas y to-dos
- Integración estable y confiable

### Google Drive API ✅
- API oficial
- Puedes guardar notas como documentos
- Más complejo pero más robusto

### Notion API ✅
- API oficial y moderna
- Excelente para notas y bases de datos
- Requiere cuenta de Notion

### Evernote API ✅
- API oficial
- Diseñado específicamente para notas
- Requiere cuenta de Evernote

---

## 📞 Recursos

- [gkeepapi GitHub](https://github.com/kiwiz/gkeepapi)
- [gkeepapi Documentación](https://gkeepapi.readthedocs.io/)
- [Google App Passwords](https://myaccount.google.com/apppasswords)
- [Google Security Settings](https://myaccount.google.com/security)

---

## 💡 Consejos

- Usa Keep para notas rápidas e ideas
- Usa Google Tasks para tareas con fechas
- Usa Calendar para eventos específicos
- Considera usar colores para organizar por categoría
- Las notas fijadas aparecen primero en Keep

---

## ⚖️ Disclaimer

Esta integración usa una biblioteca no oficial (`gkeepapi`). El uso de esta biblioteca:
- No está respaldado por Google
- Puede violar los Términos de Servicio de Google
- Es bajo tu propio riesgo
- Recomendado solo para uso personal/educativo

Para uso en producción, considera usar APIs oficiales como Google Tasks o alternativas como Notion.
