#!/usr/bin/env bash
# «Знайомся: Нептун» — all the frames (make.sh calls this; then compose.py, audio.js, voice.py and the encode).
# Long: the clouds ~1 h, the three.js layer ~1 h, on 4 cores. Frames already made are kept (delete to redo).
#   first time: python3 scenes/neptune_meet/clouds.py build   (the cloud volumes, ~10 min)
#               curl the Voyager photo: see flat.py (work/neptune_meet/nasa/pia01492.jpg, NASA PIA01492)
set -euo pipefail
cd "$(dirname "$0")/../.."
S=scenes/neptune_meet
python3 $S/timeline.py
python3 $S/shots.py flat
for shot in jump sun wind deep hook cold diamonds final; do python3 $S/shots.py clouds $shot; done
python3 $S/shots.py spec
node $S/layer.js work/neptune_meet/layer_spec.json work/neptune_meet/layer 2 0 &
node $S/layer.js work/neptune_meet/layer_spec.json work/neptune_meet/layer 2 1 &
wait
for k in 0 1 2 3; do python3 $S/shots.py comp 4 $k & done
wait
