#!/bin/bash
# The picture of "Знайомся: Меркурій": relief data (if not there yet), the 3D flights and the globe shots (four at a
# time; a finished one has .done — delete its folder to render it again; frames are overwritten in place), the overlay,
# then the timeline (assemble.py).
set -e
cd "$(dirname "$0")/../.."
for s in hokusai caloris discovery pole; do [ -f work/mercury_meet/$s/meta.json ] || python3 scenes/mercury_meet/terrain_data.py $s; done
[ -f work/mercury_meet/overlay.png ] || python3 scenes/mercury_meet/overlay.py
printf '%s\n' "shot hook" "shot terminator" "shot rupes" "shot shev" "shot pole" "globe turn" "globe calo" "globe shock" "globe bepi" "globe outro" \
  | xargs -P 4 -L 1 node scenes/mercury_meet/render_one.js
python3 scenes/mercury_meet/assemble.py
