#!/usr/bin/env bash
# «Знайомся: TRAPPIST-1e» — all the frames (make.sh calls this; then compose.py, audio.js, voice.py and the encode).
# First time: the baked maps (planet.py bake, ~40 s) and their pack (render.py prep). Frames already made are kept.
set -euo pipefail
cd "$(dirname "$0")"
[ -f ../../work/trappist_e/maps/alb.npy ] || python3 planet.py bake
[ -f ../../work/trappist_e/maps/pack.npy ] || python3 render.py prep
python3 timeline.py > /dev/null
python3 shots.py frames 4
