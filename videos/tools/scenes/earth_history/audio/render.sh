#!/bin/bash
# Re-render the whole audio: music.wav, sfx.wav (work/earth_history/, not in git) and the rough preview mix.
# ~2 min, one heavy process (numpy/scipy + ffmpeg). Needs timeline.json, timing.json and voice_p1-3.mp3 next to this folder.
set -e
cd "$(dirname "$0")"
python3 music.py && python3 sfx.py && python3 mix.py
for f in music sfx; do python3 check.py ../../../work/earth_history/$f.wav | tail -2; done
