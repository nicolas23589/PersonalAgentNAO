#!/bin/bash
# Script para lanzar el nodo speech_2_text con las variables de entorno correctas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Exportar ruta absoluta del .env para que todos los módulos Python lo encuentren
export DOTENV_PATH="$SCRIPT_DIR/.env"

echo "Usando .env: $DOTENV_PATH"

# Agregar site-packages del venv al PYTHONPATH para que ROS2 encuentre las librerías instaladas
VENV_SITE_PACKAGES="$SCRIPT_DIR/venv/lib/python3.12/site-packages"
if [ -d "$VENV_SITE_PACKAGES" ]; then
    export PYTHONPATH="$VENV_SITE_PACKAGES:${PYTHONPATH:-}"
    echo "✅ PYTHONPATH con venv: $VENV_SITE_PACKAGES"
else
    echo "⚠️  No se encontró el venv en $VENV_SITE_PACKAGES"
fi

. "$SCRIPT_DIR/install/setup.bash"
ros2 run speech_2_text speech2text_node
