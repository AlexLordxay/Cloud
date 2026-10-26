#!/bin/bash
# The picture of «Чорна діра» v2, recorded in 20-s pieces: each a fresh browser with the clock set straight to the
# piece's first missing frame (JUMP=1: every shot is a function of time), so a piece that crashes is simply tried
# again from where it stopped; finished frames are kept (delete work/blackhole2/frames to record everything anew).
set -e
cd "$(dirname "$0")/../.."
D=$(python3 -c "import json;print(json.load(open('scenes/blackhole2/scene.json'))['duration'])")
for p0 in $(seq 0 20 80); do
  p1=$(python3 -c "print(min($p0 + 20, $D))")
  for try in 1 2 3 4; do
    a=$(python3 -c "
import os
a, b = round($p0 * 30), round($p1 * 30)
m = [i for i in range(a, b) if not os.path.exists('work/blackhole2/frames/f_%05d.jpg' % i)]
print(m[0] if m else -1)")
    [ "$a" = -1 ] && break
    echo "piece $p0-$p1: from frame $a (try $try)"
    JUMP=1 node rec.js blackhole2 video "$(python3 -c "print($a / 30)")" "$p1" || echo "piece $p0 stopped, again"
  done
done
