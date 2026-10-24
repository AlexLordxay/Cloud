#!/bin/bash
# The picture of "Знайомся: Венера": the relief data and 3D flights (if not there yet), the site's Venus (two short
# stretches, recorded once), then the timeline (assemble.py).
set -e
cd "$(dirname "$0")/../.."
[ -f work/venus_meet/maat/meta.json ] || python3 scenes/venus_meet/terrain_data.py maat
for s in dawn plains deck maat dusk; do
  [ -f work/venus_meet/shot_$s/.done ] || { rm -rf work/venus_meet/shot_$s; node scenes/venus_meet/terrain.js $s video; touch work/venus_meet/shot_$s/.done; }
done
if [ ! -f work/venus_meet/site/.done ]; then
  rm -rf work/venus_meet/frames work/venus_meet/site
  node rec.js venus_meet video 2.8 18.6
  mv work/venus_meet/frames work/venus_meet/site; touch work/venus_meet/site/.done
fi
rm -rf work/venus_meet/frames
python3 scenes/venus_meet/assemble.py
