#!/usr/bin/env bash
# Builds a whole video:  ./make.sh <scene>   ->   videos/<scene>.mp4
# Steps can be run on their own too: rec.js (frames), audio.js (sound), compose.py (captions and logo), then this encode.
set -euo pipefail
cd "$(dirname "$0")"
scene="${1:?usage: ./make.sh <scene>}"
work="work/$scene"
duration=$(python3 -c "import json;print(json.load(open('scenes/$scene/scene.json'))['duration'])")

[ -d node_modules/three ] || npm install --silent
python3 -c "import PIL, imageio_ffmpeg" 2>/dev/null || pip install -q pillow imageio-ffmpeg

node rec.js "$scene" video
node audio.js "$scene"
python3 compose.py "$scene"

ffmpeg=$(python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")
fade=$(python3 -c "print($duration - 1.5)")
"$ffmpeg" -y -loglevel error -framerate 30 -i "$work/out/f_%05d.jpg" -i "$work/audio.wav" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=$fade:d=1.5" -c:a aac -b:a 160k -ar 48000 -t "$duration" \
  "../$scene.mp4"
echo "done: videos/$scene.mp4"
