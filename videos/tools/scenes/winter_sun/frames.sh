#!/bin/bash
# «Чому взимку холодно»: the maps (once), then all frames (render.py, 2 workers; frames already made are kept)
set -e
cd "$(dirname "$0")/../.."
W=work/winter_sun; mkdir -p $W/tiles13
[ -f work/sun_imagine/day.npy ] || python3 scenes/sun_imagine/textures.py
if [ ! -f $W/kyiv.npy ]; then
  for x in $(seq 4786 4794); do for y in $(seq 2758 2766); do echo "$x $y"; done; done | xargs -P 6 -n 2 sh -c \
    '[ -s '$W'/tiles13/$0_$1.jpg ] || curl -s -o '$W'/tiles13/$0_$1.jpg "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/13/$1/$0.jpg"'
  python3 scenes/winter_sun/kyivmap.py
fi
[ -f $W/kyiv_w.npy ] || python3 scenes/winter_sun/winterize.py   # needs work/winter_sun/kyiv75.jpg (the neutron_spoon ground map)
python3 scenes/winter_sun/render.py 2
