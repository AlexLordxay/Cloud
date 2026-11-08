#!/usr/bin/env bash
# «Знайомся: Уран» — every shot's frames (kept if already there; delete a shot's folder in work/uranus_meet/shots to redo)
#   first time: python3 clouds.py build  (the cloud volumes, ~6 min); the Miranda grids bake themselves (~15 s)
set -uo pipefail
cd "$(dirname "$0")"
python3 timeline.py > /dev/null
python3 shots.py vspec
(cd ../.. && node scenes/uranus_meet/voyager.js work/uranus_meet/voyager_spec.json work/uranus_meet/voyager)
for s in hook scale orbit moons mystery voyager final; do python3 shots.py video $s > /dev/null && echo "done $s"; done
for s in herschel mirphoto skynow; do python3 flat.py video $s > /dev/null && echo "done $s"; done
python3 shots.py video rockfall > /dev/null && echo "done rockfall"
python3 clouds.py video 0 15.25 > /dev/null && echo "done clouds"
for s in ringdive under; do python3 shots.py video $s > /dev/null && echo "done $s"; done
echo ALL DONE
