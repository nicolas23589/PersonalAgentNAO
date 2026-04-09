# Script de configuración rápida para Vertex AI en GCP
# Ejecuta este script en PowerShell para configurar automáticamente tu proyecto

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN RÁPIDA DE VERTEX AI" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Verificar si gcloud está instalado
Write-Host "Verificando instalación de gcloud CLI..." -ForegroundColor Yellow
$gcloudPath = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudPath) {
    Write-Host "❌ gcloud CLI no está instalado" -ForegroundColor Red
    Write-Host "`nDescarga e instala desde: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ gcloud CLI encontrado`n" -ForegroundColor Green

# Obtener o solicitar Project ID
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN DE PROYECTO" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$projectId = Read-Host "Ingresa tu GCP Project ID (o presiona Enter para listar proyectos disponibles)"

if ([string]::IsNullOrWhiteSpace($projectId)) {
    Write-Host "`nListando proyectos disponibles...`n" -ForegroundColor Yellow
    gcloud projects list --format="table(projectId,name,projectNumber)"
    Write-Host ""
    $projectId = Read-Host "Ingresa el Project ID que deseas usar"
}

# Configurar proyecto
Write-Host "`nConfigurando proyecto: $projectId" -ForegroundColor Yellow
gcloud config set project $projectId

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al configurar el proyecto" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Proyecto configurado`n" -ForegroundColor Green

# Solicitar región
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN DE REGIÓN" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Regiones comunes para Vertex AI:" -ForegroundColor Yellow
Write-Host "  1. us-central1 (Iowa) - Recomendada"
Write-Host "  2. us-east1 (South Carolina)"
Write-Host "  3. us-west1 (Oregon)"
Write-Host "  4. europe-west1 (Bélgica)"
Write-Host "  5. europe-west4 (Países Bajos)"
Write-Host "  6. asia-northeast1 (Tokio)`n"

$location = Read-Host "Selecciona región (presiona Enter para us-central1)"
if ([string]::IsNullOrWhiteSpace($location)) {
    $location = "us-central1"
}
Write-Host "✅ Región seleccionada: $location`n" -ForegroundColor Green

# Habilitar APIs
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HABILITANDO APIs NECESARIAS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$apis = @(
    "aiplatform.googleapis.com",
    "calendar-json.googleapis.com",
    "tasks.googleapis.com"
)

foreach ($api in $apis) {
    Write-Host "Habilitando $api..." -ForegroundColor Yellow
    gcloud services enable $api --project=$projectId
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $api habilitada" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Error al habilitar $api" -ForegroundColor Red
    }
}

# API opcional de búsqueda
Write-Host "`n¿Deseas habilitar Custom Search API? (búsquedas web) (S/N)" -ForegroundColor Yellow
$enableSearch = Read-Host
if ($enableSearch -eq "S" -or $enableSearch -eq "s") {
    Write-Host "Habilitando customsearch.googleapis.com..." -ForegroundColor Yellow
    gcloud services enable customsearch.googleapis.com --project=$projectId
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Custom Search API habilitada" -ForegroundColor Green
    }
}

# Configurar autenticación
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CONFIGURACIÓN DE AUTENTICACIÓN" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Configurando Application Default Credentials..." -ForegroundColor Yellow
Write-Host "Se abrirá un navegador para autenticarte.`n" -ForegroundColor Yellow

gcloud auth application-default login

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al configurar autenticación" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Autenticación configurada`n" -ForegroundColor Green

# Crear archivo .env
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CREANDO ARCHIVO .ENV" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$envPath = ".env"
if (Test-Path $envPath) {
    Write-Host "⚠️  Ya existe un archivo .env" -ForegroundColor Yellow
    $overwrite = Read-Host "¿Deseas sobrescribirlo? (S/N)"
    if ($overwrite -ne "S" -and $overwrite -ne "s") {
        Write-Host "Manteniendo archivo .env existente" -ForegroundColor Yellow
    } else {
        Write-Host "Creando nuevo archivo .env..." -ForegroundColor Yellow
        @"
# ============ GOOGLE VERTEX AI ============
GCP_PROJECT_ID=$projectId
GCP_LOCATION=$location

# ============ TELEGRAM BOT ============
TELEGRAM_BOT_TOKEN=

# ============ GOOGLE CALENDAR API ============
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# ============ SERPER API (Web Search) ============
SERPER_API_KEY=

# ============ GOOGLE TASKS API ============
GOOGLE_TASKS_LIST_ID=@default
"@ | Out-File -FilePath $envPath -Encoding UTF8
        Write-Host "✅ Archivo .env creado`n" -ForegroundColor Green
    }
} else {
    Write-Host "Creando archivo .env..." -ForegroundColor Yellow
    @"
# ============ GOOGLE VERTEX AI ============
GCP_PROJECT_ID=$projectId
GCP_LOCATION=$location

# ============ TELEGRAM BOT ============
TELEGRAM_BOT_TOKEN=

# ============ GOOGLE CALENDAR API ============
GOOGLE_CALENDAR_CREDENTIALS_FILE=credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# ============ SERPER API (Web Search) ============
SERPER_API_KEY=

# ============ GOOGLE TASKS API ============
GOOGLE_TASKS_LIST_ID=@default
"@ | Out-File -FilePath $envPath -Encoding UTF8
    Write-Host "✅ Archivo .env creado`n" -ForegroundColor Green
}

# Instalar dependencias Python
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INSTALANDO DEPENDENCIAS PYTHON" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "¿Deseas instalar las dependencias de Python ahora? (S/N)" -ForegroundColor Yellow
$installDeps = Read-Host
if ($installDeps -eq "S" -or $installDeps -eq "s") {
    Write-Host "Instalando dependencias..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dependencias instaladas`n" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Error al instalar dependencias. Ejecuta manualmente: pip install -r requirements.txt" -ForegroundColor Red
    }
}

# Ejecutar test de verificación
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE CONFIGURACIÓN" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "¿Deseas ejecutar el test de verificación ahora? (S/N)" -ForegroundColor Yellow
$runTest = Read-Host
if ($runTest -eq "S" -or $runTest -eq "s") {
    Write-Host "`nEjecutando test de verificación...`n" -ForegroundColor Yellow
    python test_vertex_setup.py
}

# Resumen final
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ CONFIGURACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Resumen de configuración:" -ForegroundColor Yellow
Write-Host "  • Project ID: $projectId"
Write-Host "  • Región: $location"
Write-Host "  • APIs habilitadas: Vertex AI, Calendar, Tasks"
Write-Host "  • Archivo .env: $envPath`n"
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "  1. Edita el archivo .env para agregar tokens opcionales (Telegram, Serper)"
Write-Host "  2. Ejecuta: python test_vertex_setup.py (para verificar)"
Write-Host "  3. Ejecuta tu aplicación principal`n"
Write-Host "Para más información, consulta: VERTEX_AI_SETUP.md`n" -ForegroundColor Cyan
