#!/bin/bash
# «У Землі колись могли бути кільця»: the data (once), then all frames (frames.py, numba on all cores; resumable),
# merged labels, then work/earth_rings/frames -> w3d for compose.py.
set -e
cd "$(dirname "$0")/../.."
W=work/earth_rings; mkdir -p $W work/neutron_spoon
[ -f work/neutron_spoon/sky.jpg ] || python3 scenes/neutron_spoon/sky.py
[ -f $W/inner_col.png ] || { python3 scenes/earth_rings/fetch.py; python3 scenes/earth_rings/prep.py; python3 scenes/earth_rings/monument.py; }
[ -f work/earth_history/paleo/ep_465.png ] || python3 scenes/earth_history/paleo.py 465
python3 scenes/earth_rings/frames.py 0 1335
python3 -c "import json,glob; d={}; [d.update(json.load(open(f))) for f in sorted(glob.glob('$W/labels_*.json'))]; json.dump(d, open('$W/labels.json','w'))"
ln -sfn w3d $W/frames
