#!/bin/bash
# A shot as a short clip to look at: frames, glow, mp4.   scenes/chicxulub/preview.sh <shot>  -> work/chicxulub/<shot>.mp4
set -e
cd "$(dirname "$0")/../.."
shot=$1; dir=work/chicxulub/shot_$shot
rm -rf "$dir"
node scenes/chicxulub/render.js "$shot" video
python3 scenes/chicxulub/post.py "$dir"
ffmpeg -loglevel error -y -framerate 30 -i "$dir/f_%05d.jpg" -c:v libx264 -pix_fmt yuv420p -crf 18 "work/chicxulub/$shot.mp4"
echo "work/chicxulub/$shot.mp4"
