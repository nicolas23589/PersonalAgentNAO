#!/bin/bash
cd /home/robotica/Documents/nmurilloc/PersonalAgentNAO
source nicoenv/bin/activate
export PYTHONPATH="${PYTHONPATH}:/home/robotica/Documents/nmurilloc/PersonalAgentNAO/src/external-integrations"
source install/setup.bash
ros2 run speech_2_text speech2text_node
