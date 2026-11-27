#!/bin/bash
# «А ти уявляєш Титан так?»: the star sky and the two landscapes (once), then all frames (frames.py, numba on all cores;
# resumable), merged labels, then work/titan_imagine/frames -> w3d for compose.py.
set -e
cd "$(dirname "$0")/../.."
W=work/titan_imagine; mkdir -p $W work/neutron_spoon
[ -f work/neutron_spoon/sky.jpg ] || python3 scenes/neutron_spoon/sky.py
[ -f $W/dunes_w.npy ] || python3 scenes/titan_imagine/prep.py
python3 scenes/titan_imagine/frames.py 0 1245
python3 -c "import json,glob; d={}; [d.update(json.load(open(f))) for f in sorted(glob.glob('$W/labels_*.json'))]; json.dump(d, open('$W/labels.json','w'))"
ln -sfn w3d $W/frames
