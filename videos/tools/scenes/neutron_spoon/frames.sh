#!/bin/bash
# «Ложка нейтронної зорі»: the data (once), then all frames (world.js; two processes on halves of the film;
# frames already made are kept, so a stopped render resumes), then work/neutron_spoon/frames -> w3d for compose.py.
set -e
cd "$(dirname "$0")/../.."
W=work/neutron_spoon; mkdir -p $W/tiles $W/dl
[ -f $W/dl/crab.jpg ] || curl -s -o $W/dl/crab.jpg https://images-assets.nasa.gov/image/PIA03606/PIA03606~orig.jpg
if [ ! -f $W/ground.jpg ]; then
  for x in $(seq 1190 1204); do for y in $(seq 683 697); do echo "$x $y"; done; done | xargs -P 8 -n 2 sh -c \
    '[ -s '$W'/tiles/$0_$1.jpg ] || curl -s -o '$W'/tiles/$0_$1.jpg "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/11/$1/$0.jpg"'
  python3 scenes/neutron_spoon/ground.py
fi
[ -f $W/sky.jpg ] || python3 scenes/neutron_spoon/sky.py
node scenes/neutron_spoon/labels.js
N=$(node -e "const P=require('./scenes/neutron_spoon/path'); console.log(Math.round(P.DURATION*P.FPS))")
node scenes/neutron_spoon/world.js video 0 $((N/2)) & node scenes/neutron_spoon/world.js video $((N/2)) $N & wait
ln -sfn w3d $W/frames
