#!/bin/bash
# «Термометр Сонячної системи»: the spinning planet sprites (once), then the frames
set -e
cd "$(dirname "$0")/../.."
[ -f work/planet_temps/spin/pluto_95.png ] || python3 scenes/planet_temps/render.py sprites
python3 scenes/planet_temps/render.py
