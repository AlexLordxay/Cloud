#!/bin/bash
# 16:9 frames of the given shots (resumable): 1600 x 900 (assemble16.py resizes to 1920 x 1080), then the glow (post.py, once).
#   bash scenes/chicxulub/render16.sh hook kpg_earth approach entry     (CX_W / CX_H override the size)
cd "$(dirname "$0")/../.."
export CX_W=${CX_W:-1600} CX_H=${CX_H:-900}
for s in "$@"; do
  dir=work/chicxulub/shot16_$s
  node scenes/chicxulub/render.js "$s" video || exit 1
  [ -f "$dir/.post_done" ] || { python3 scenes/chicxulub/post.py "$dir" && touch "$dir/.post_done"; }
  echo "$s done $(ls $dir | wc -l)"
done
