#!/usr/bin/env bash
# «Знайомся: Уран» — all the frames (make.sh calls this; then compose.py, audio.js, voice.py and the encode).
# Long: ~3 h on 4 cores (render_all.sh keeps the frames already made). Then assemble.py lays the shots end to end.
set -euo pipefail
cd "$(dirname "$0")"
[ -f ../../work/uranus_meet/clouds/near_den.npy ] || python3 clouds.py build
bash render_all.sh
python3 assemble.py 4
