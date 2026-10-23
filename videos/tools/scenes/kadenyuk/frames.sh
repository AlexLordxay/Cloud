#!/bin/bash
# The picture of the Kadenyuk video: the 3D shots (if not rendered yet; ~1 h) and the timeline (assemble.py).
set -e
cd "$(dirname "$0")/../.."
[ -f work/kadenyuk/patch.jpg ] || python3 scenes/kadenyuk/patch.py
for s in hook home night finale; do [ -f work/kadenyuk/shot_$s/marks.json ] || node scenes/kadenyuk/render.js $s video; done
rm -rf work/kadenyuk/frames
python3 scenes/kadenyuk/assemble.py
