#!/bin/bash
# =============================================================
#  start_nao.sh — Arranca el sistema completo del agente NAO
#
#  Uso:  bash start_nao.sh
#
#  Qué hace (en orden):
#    1. Activa el venv y exporta PYTHONPATH
#    2. Compila el workspace (colcon build)
#    3. Hace source del install/setup.bash
#    4. Abre una terminal nueva con el bringup de NAOqi
#    5. Abre una terminal nueva con el nodo de emoción
#    6. Corre el nodo de speech en la terminal actual
# =============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAOQI_WS="$HOME/ros2_naoqi_ws"

# Colores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   🤖  Iniciando sistema NAO Agent     ${NC}"
echo -e "${CYAN}========================================${NC}"

# ── 1. Activar venv ─────────────────────────────────────────
echo -e "\n${YELLOW}[1/5] Activando venv...${NC}"
VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
    echo -e "${GREEN}✅ venv activado${NC}"
else
    echo -e "${RED}⚠️  No se encontró venv en $SCRIPT_DIR/venv — continuando sin él${NC}"
fi

# Exportar PYTHONPATH para que ROS2 encuentre las librerías del venv
VENV_SITE_PACKAGES="$SCRIPT_DIR/venv/lib/python3.12/site-packages"
if [ -d "$VENV_SITE_PACKAGES" ]; then
    export PYTHONPATH="$VENV_SITE_PACKAGES:${PYTHONPATH:-}"
    echo -e "${GREEN}✅ PYTHONPATH configurado${NC}"
fi

# Exportar .env para módulos Python
export DOTENV_PATH="$SCRIPT_DIR/.env"

# ── 2. Compilar workspace ────────────────────────────────────
echo -e "\n${YELLOW}[2/5] Compilando workspace (colcon build)...${NC}"
cd "$SCRIPT_DIR"
colcon build --symlink-install
echo -e "${GREEN}✅ Compilación completada${NC}"

# ── 3. Source del workspace ──────────────────────────────────
echo -e "\n${YELLOW}[3/5] Cargando setup.bash...${NC}"
source "$SCRIPT_DIR/install/setup.bash"
echo -e "${GREEN}✅ Workspace cargado${NC}"

# ── 4. Lanzar bringup NAOqi en terminal nueva ────────────────
echo -e "\n${YELLOW}[4/5] Lanzando bringup NAOqi...${NC}"
if [ -d "$NAOQI_WS" ]; then
    gnome-terminal --title="NAOqi Bringup" -- bash -c "
        cd '$NAOQI_WS'
        source install/setup.bash
        echo '🤖 Lanzando NAOqi bringup...'
        bash launch_bringup.sh
        echo 'Presiona Enter para cerrar...'
        read
    " &
    echo -e "${GREEN}✅ Terminal de bringup abierta${NC}"
else
    echo -e "${RED}⚠️  No se encontró $NAOQI_WS — omitiendo bringup${NC}"
fi

# Esperar a que el bringup levante los servicios
echo -e "${CYAN}   ⏳ Esperando 8s para que el bringup levante servicios...${NC}"
sleep 8

# ── 5. Lanzar nodo de detección de emociones en terminal nueva
echo -e "\n${YELLOW}[5/5] Lanzando nodo de detección de emociones...${NC}"
gnome-terminal --title="Emotion Detection" -- bash -c "
    cd '$SCRIPT_DIR'
    source install/setup.bash
    export DOTENV_PATH='$SCRIPT_DIR/.env'
    VENV_SITE='$VENV_SITE_PACKAGES'
    [ -d \"\$VENV_SITE\" ] && export PYTHONPATH=\"\$VENV_SITE:\${PYTHONPATH:-}\"
    echo '🧠 Lanzando emotion_detection_node...'
    ros2 run nao_emotion_detection emotion_detection_node
    echo 'Presiona Enter para cerrar...'
    read
" &
echo -e "${GREEN}✅ Terminal de emoción abierta${NC}"

# ── 6. Correr nodo de speech en esta terminal ────────────────
echo -e "\n${CYAN}========================================${NC}"
echo -e "${CYAN}  🎙️  Lanzando nodo speech_2_text...    ${NC}"
echo -e "${CYAN}========================================${NC}"
ros2 run speech_2_text speech2text_node
