// Screen positions for the drawings over the frames (captions.py): per frame, the star's centre and radius in the Kyiv
// shot, the two pans in the balance shot. -> work/neutron_spoon/labels.json
const P = require('./path'), fs = require('fs'), path = require('path');
const out = [];
for (let i = 0; i < Math.round(P.DURATION * P.FPS); i++) {
  const s = P.state(i / P.FPS), e = { mode: s.mode };
  if (s.mode === 'kyiv') {
    const c = P.project(s, [0, P.STAR_Y, 0]); e.star = [c[0], c[1], P.R / c[2] * 640 / Math.tan(s.fov * Math.PI / 360)];
  } else if (s.mode === 'balance') {
    const th = s.bal.theta, ARM = 13, HANG = 21;
    e.panL = P.project(s, [-ARM * Math.cos(th), 45 - ARM * Math.sin(th) - HANG, 0]); e.panR = P.project(s, [ARM * Math.cos(th), 45 + ARM * Math.sin(th) - HANG + 3, 0]);
  }
  out.push(e);
}
fs.mkdirSync(path.join(__dirname, '../../work/neutron_spoon'), { recursive: true });
fs.writeFileSync(path.join(__dirname, '../../work/neutron_spoon/labels.json'), JSON.stringify(out));
console.log('labels', out.length);
