#!/bin/bash
# «А ти уявляєш Плутон так?»: the data (once), then the one continuous flight (world3d.js; frames already made are
# kept, so a stopped render resumes), then work/pluto_imagine/frames -> w3d for compose.py.
set -e
cd "$(dirname "$0")/../.."
W=work/pluto_imagine
[ -f $W/mosaic8.tif ] || curl -sL -o $W/mosaic8.tif https://planetarymaps.usgs.gov/mosaic/Pluto_NewHorizons_Global_Mosaic_300m_Jul2017_8bit.tif
[ -f $W/globe.jpg ] || python3 scenes/pluto_imagine/globe_tex.py
[ -f $W/overlay.png ] || python3 scenes/pluto_imagine/overlay.py
[ -f $W/heart/meta.json ] || python3 scenes/pluto_imagine/patches.py heart
[ -f $W/tenzing/meta.json ] || python3 scenes/pluto_imagine/patches.py tenzing
node -e "
const P=require('./scenes/pluto_imagine/path'); const out=[];
for (let i=0;i<Math.round(P.DURATION*30);i++){ const t=i/30; const a=P.project(t,[0,0,0]), b=P.project(t,P.MOON), f=640/Math.tan(P.state(t).fov*Math.PI/360);
  out.push([+a[0].toFixed(1),+a[1].toFixed(1),+(P.R/a[2]*f).toFixed(1),+b[0].toFixed(1),+b[1].toFixed(1),+(1737.4/b[2]*f).toFixed(1)]); }
require('fs').writeFileSync('$W/labels.json', JSON.stringify(out));"
node scenes/pluto_imagine/world3d.js video
ln -sfn w3d $W/frames
