#!/bin/bash
# Builds «Що, якби Місяць упав на Землю?»:  scenes/moonfall/build.sh  ->  videos/moonfall.mp4
#   frames (render.js; resumable: run it again after the container restarts, it carries on), glow (post.py), captions
#   and the helmet overlay (compose.py), sound (sound.py: the breathing), then H.264 + AAC at -14 LUFS.
#   Maps first, once: python3 scenes/moonfall/maps.py
set -euo pipefail
cd "$(dirname "$0")/../.."
work=work/moonfall
[ -f $work/maps/hgt.png ] || python3 scenes/moonfall/maps.py
node scenes/moonfall/render.js film video
python3 scenes/moonfall/post.py
python3 compose.py moonfall
python3 scenes/moonfall/sound.py
ffmpeg=$(python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")
"$ffmpeg" -y -loglevel error -i $work/audio.wav -framerate 30 -i $work/out/f_%05d.jpg \
  -filter_complex "[0:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]" -map "[a]" -c:a aac -b:a 160k -ar 48000 \
  -map 1:v -c:v libx264 -preset slow -crf 22 -maxrate 9M -bufsize 18M -pix_fmt yuv420p -profile:v high \
  -movflags +faststart -t 46 ../moonfall.mp4
echo "done: videos/moonfall.mp4"
