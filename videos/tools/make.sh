#!/usr/bin/env bash
# Builds a whole video:  ./make.sh <scene>   ->   videos/<scene>.mp4
#   ./make.sh <scene> sound   puts the soundtrack (music, voiceover) over the picture of the existing videos/<scene>.mp4
#                             -> videos/<scene>_voice.mp4 (the original stays as is)
# Steps can be run on their own too: rec.js (frames), audio.js (sound), voice.py (voiceover), compose.py (captions
# and logo), then this encode.
set -euo pipefail
cd "$(dirname "$0")"
scene="${1:?usage: ./make.sh <scene> [sound]}"
mode="${2:-all}"
work="work/$scene"
duration=$(python3 -c "import json;print(json.load(open('scenes/$scene/scene.json'))['duration'])")
narrated=$(python3 -c "import json;print(1 if 'narration' in json.load(open('scenes/$scene/scene.json')) else 0)")

[ -d node_modules/three ] || npm install --silent
python3 -c "import PIL, imageio_ffmpeg" 2>/dev/null || pip install -q pillow imageio-ffmpeg
ffmpeg=$(python3 -c "import imageio_ffmpeg as i; print(i.get_ffmpeg_exe())")

if [ "$mode" != sound ]; then
  node rec.js "$scene" video
  python3 compose.py "$scene"
fi
node audio.js "$scene"

# Voiceover: the music (with the planet's voice) ducks by ~10 dB under speech, then everything goes to -14 LUFS.
if [ "$narrated" = 1 ]; then
  python3 voice.py "$scene"
  mix="[1:a]volume=2.0,asplit=2[v][sc];[0:a]volume=0.8[m];[m][sc]sidechaincompress=threshold=0.04:ratio=3:attack=60:release=800[md];[md][v]amix=inputs=2:normalize=0"
  extra=(-i "$work/voice.wav")
else
  mix="[0:a]anull"; extra=()
fi
fade=$(python3 -c "print($duration - 1.5)")
audio=(-filter_complex "$mix,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=$fade:d=1.5[a]" -map "[a]" -c:a aac -b:a 160k -ar 48000)

if [ "$mode" = sound ]; then
  "$ffmpeg" -y -loglevel error -i "$work/audio.wav" "${extra[@]}" -i "../$scene.mp4" "${audio[@]}" \
    -map "$(( ${#extra[@]} / 2 + 1 )):v" -c:v copy -movflags +faststart -t "$duration" "../${scene}_voice.mp4"
  echo "done: videos/${scene}_voice.mp4"; exit 0
else
  "$ffmpeg" -y -loglevel error -i "$work/audio.wav" "${extra[@]}" -framerate 30 -i "$work/out/f_%05d.jpg" "${audio[@]}" \
    -map "$(( ${#extra[@]} / 2 + 1 )):v" -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -profile:v high \
    -movflags +faststart -t "$duration" "../$scene.mp4"
fi
echo "done: videos/$scene.mp4"
