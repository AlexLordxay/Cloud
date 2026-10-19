#!/usr/bin/env bash
# Frames of "Знайомся: Юпітер": every shot rendered (render.js; a shot already rendered at its current length is kept),
# then laid end to end with crossfades (assemble.py). Run by make.sh instead of rec.js.
set -euo pipefail
cd "$(dirname "$0")/../.."
for s in $(python3 -c "import sys; sys.path.insert(0, 'scenes/jupiter_meet'); from timeline import ORDER; print(' '.join(ORDER))"); do
  want=$(python3 -c "import sys; sys.path.insert(0, 'scenes/jupiter_meet'); from timeline import lengths; print(round(lengths()['$s'] * 30))")
  have=$(ls "work/jupiter_meet/shot_$s" 2>/dev/null | grep -c '\.jpg$' || true)
  if [ "$have" != "$want" ]; then rm -rf "work/jupiter_meet/shot_$s"; node scenes/jupiter_meet/render.js "$s" video; fi
done
python3 scenes/jupiter_meet/assemble.py
