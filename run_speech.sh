#!/bin/bash
# Script para lanzar el nodo speech_2_text con las variables de entorno correctas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Exportar ruta absoluta del .env para que todos los módulos Python lo encuentren
export DOTENV_PATH="$SCRIPT_DIR/.env"

echo "Usando .env: $DOTENV_PATH"

. "$SCRIPT_DIR/install/setup.bash"
ros2 run speech_2_text speech2text_node
