#!/bin/bash
# «А ти уявляєш Європу так?»: the data (once), then all frames (frames.py, numba on all cores; resumable),
# then work/europa_imagine/frames -> w3d for compose.py.
set -e
cd "$(dirname "$0")/../.."
W=work/europa_imagine; mkdir -p $W
[ -f $W/europa_500m.tif ] || curl -sL -o $W/europa_500m.tif https://planetarymaps.usgs.gov/mosaic/Europa_Voyager_GalileoSSI_global_mosaic_500m.tif
[ -f work/neutron_spoon/sky.jpg ] || python3 scenes/neutron_spoon/sky.py
[ -f $W/hf.npy ] || python3 scenes/europa_imagine/prep.py
python3 scenes/europa_imagine/frames.py
ln -sfn w3d $W/frames
