// «Скільки ти важиш на інших планетах?» — frames. The astronaut on a bathroom scale on ten worlds, one shot per line
// of the voiceover (scenes/weight/voice.mp3, sped up 1.07 → work/weight/voice.wav, 72.3 s); page.js draws them.
//
//   node scenes/weight/render.js stills 1,15,30      -> work/weight/still_<t>.jpg
//   node scenes/weight/render.js video [from to]     -> work/weight/frames/f_00000.jpg … (seconds; default all)
//
// The Moon is the real one (moon_meet's site 'south': LOLA heights, the Earth where it hangs, drawn twice life size as
// in moon_final); the other worlds are built from a recipe each (scenes/weight/page.js) with their real light and air.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const { moonWorld } = require('../moon_meet/world');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'weight');
const MOON = path.join(TOOLS, 'work', 'moon_meet', 'south'), SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [mode = 'stills', a1 = '1', a2] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30, DUR = 72.3;
if (!fs.existsSync(path.join(MOON, 'meta.json'))) { console.log('first: python3 scenes/moon_meet/terrain_data.py south'); process.exit(1); }
const moonMeta = JSON.parse(fs.readFileSync(path.join(MOON, 'meta.json')));
const moonShot = { site: 'south', mesh: 1600, earth: [0, 4.5], earthFace: [49, 31, 40], earthLean: 28, earthshine: 2.5, earthScale: 2 };

// The worlds. sun [compass azimuth: 0 = -z, the way he faces unless `face` turns him; 180 = toward the camera's view in
// most shots], elevation°; sunC/amb: linear light on the ground; sky [zenith, horizon] and fog colour: gamma-encoded;
// keyC/keyK, hemi [sky, ground, k], under: the lights on the figure; ground: the height recipe (page.js).
const MOON_CRATERS = [[5.0, 0.3, 1.1, 0.22, 11], [14, 1.2, 4.5, 0.4, 23], [45, 5, 18, 0.6, 37], [190, 18, 75, 0.7, 53]];
const worlds = {
  moon: { moon: true, face: Math.PI, sunC: [2.3, 2.25, 2.19], amb: [0.025, 0.03, 0.04], Rmax: 2600,
    ground: { craters: MOON_CRATERS, swell: 0.9 }, keyC: [1, 0.965, 0.92], keyK: 3.2, hemi: [[0.04, 0.045, 0.07], [0.54, 0.53, 0.51], 0.16] },
  mercury: { R: 2439.7e3, sun: [174, 9], sunC: [3.2, 3.1, 2.95], amb: [0.012, 0.012, 0.015], alb: [0.22, 0.2, 0.18], Rmax: 4000,
    ground: { craters: [[5.0, 0.3, 1.1, 0.3, 11], [14, 1.2, 4.5, 0.5, 23], [45, 5, 18, 0.7, 37], [190, 18, 75, 0.8, 53]], swell: 0.9, mountains: [140, 700, 800] },
    sky: [[0, 0, 0], [0, 0, 0]], sunDisc: [1.6, 1.55, 1.45], sunDeg: 1.6, sunGlow: 1.4, stars: 1200,
    keyC: [1, 0.97, 0.93], keyK: 3.6, hemi: [[0.03, 0.03, 0.04], [0.32, 0.3, 0.27], 0.2], rim: [0.9, 0.85, 0.75] },
  mars: { R: 3389.5e3, sun: [-35, 32], sunC: [1.9, 1.75, 1.6], amb: [0.3, 0.2, 0.13], alb: [0.46, 0.25, 0.13], grain: 0.8, Rmax: 3000,
    ground: { craters: [[6, 0.4, 1.2, 0.18, 11], [18, 1.5, 5, 0.35, 23], [60, 6, 20, 0.5, 37]], craterK: 0.7, swell: 0.8, dunes: [9, 0.3], mountains: [70, 600, 700] },
    sky: [[0.56, 0.44, 0.34], [0.87, 0.71, 0.53]], fog: [[0.84, 0.66, 0.5], 1 / 2200], sunDisc: [1.2, 1.15, 1.1], sunDeg: 0.35, sunGlow: 0.6, haze: 1,
    keyC: [1, 0.92, 0.84], keyK: 2.6, hemi: [[0.78, 0.62, 0.5], [0.55, 0.32, 0.2], 0.5], marsEnv: true, rim: [0.5, 0.35, 0.25] },
  venus: { R: 6051.8e3, sun: [-20, 55], sunC: [0.45, 0.32, 0.15], amb: [0.62, 0.42, 0.19], alb: [0.26, 0.23, 0.21], grain: 0.8, shadowHard: 0.2, Rmax: 2500,
    ground: { swell: 0.5, plates: 0.16 }, sky: [[0.64, 0.46, 0.2], [0.93, 0.73, 0.42]], fog: [[0.88, 0.66, 0.38], 1 / 320], haze: 1,
    keyC: [1, 0.76, 0.42], keyK: 0.7, hemi: [[1, 0.75, 0.42], [0.5, 0.35, 0.2], 1.3], rim: [0.6, 0.4, 0.15] },
  jupiter: { sun: [-30, 28], sunC: [1.6, 1.55, 1.5], amb: [0.2, 0.2, 0.22], deck: [[0.93, 0.86, 0.74], [0.62, 0.38, 0.22], [0.98, 0.96, 0.92]], deckY: 14,
    sky: [[0.1, 0.14, 0.28], [0.64, 0.68, 0.74]], fog: [[0.72, 0.7, 0.68], 1 / 2500], sunDisc: [2, 2, 2], sunDeg: 0.12, sunGlow: 0.8, haze: 0.5,
    bodies: [{ tex: 'io.jpg', az: 158, el: 7, deg: 0.9, k: 1.8 }, { tex: 'europa.jpg', az: 172, el: 9, deg: 0.55, k: 1.8 }],
    keyC: [1, 0.97, 0.92], keyK: 2.2, hemi: [[0.5, 0.56, 0.66], [0.72, 0.62, 0.5], 0.6], rim: [0.3, 0.35, 0.45] },
  saturn: { sun: [-40, 30], sunC: [1.4, 1.35, 1.25], amb: [0.2, 0.19, 0.17], deck: [[0.95, 0.88, 0.7], [0.76, 0.62, 0.4], [0.99, 0.96, 0.88]], deckY: 14,
    sky: [[0.12, 0.15, 0.3], [0.82, 0.79, 0.7]], fog: [[0.86, 0.81, 0.7], 1 / 2500], sunDisc: [2, 2, 2], sunDeg: 0.1, sunGlow: 0.6, haze: 0.5,
    rings: { size: 560, pos: [0, -200, 0], rot: [-2.269, 0, 0] },
    keyC: [1, 0.96, 0.9], keyK: 2.0, hemi: [[0.5, 0.55, 0.65], [0.8, 0.72, 0.55], 0.6], rim: [0.3, 0.35, 0.45] },
  titan: { R: 2574.7e3, sun: [-25, 50], sunC: [0.25, 0.17, 0.09], amb: [0.62, 0.38, 0.17], alb: [0.22, 0.17, 0.12], grain: 0.6, shadowHard: 0.2, Rmax: 2500,
    ground: { swell: 0.6, dunes: [14, 0.6] }, sky: [[0.52, 0.32, 0.14], [0.86, 0.56, 0.26]], fog: [[0.82, 0.52, 0.24], 1 / 220], haze: 1,
    keyC: [1, 0.72, 0.42], keyK: 0.8, hemi: [[0.95, 0.62, 0.32], [0.42, 0.26, 0.13], 1.2], wings: true, rim: [0.6, 0.35, 0.15] },
  pluto: { R: 1188.3e3, sun: [-40, 18], sunC: [1.5, 1.45, 1.4], amb: [0.02, 0.02, 0.03], alb: [0.78, 0.7, 0.63], grain: 0.55, Rmax: 4000,
    ground: { craters: [[8, 0.4, 1.5, 0.15, 11], [30, 2, 8, 0.3, 23]], craterK: 0.6, swell: 0.4, mountains: [380, 900, 600] },
    sky: [[0, 0, 0], [0, 0, 0]], sunDisc: [2, 2, 2], sunDeg: 0.08, sunGlow: 0.5, stars: 2200,
    bodies: [{ tex: 'charon.jpg', az: 190, el: 13, deg: 3.8, k: 1.4 }],
    keyC: [1, 0.98, 0.95], keyK: 2.2, hemi: [[0.04, 0.04, 0.06], [0.6, 0.55, 0.5], 0.25], rim: [0.3, 0.32, 0.4] },
  sun: { sun: [-20, 35], sunC: [1, 1, 1], amb: [0.3, 0.2, 0.1], deck: [[1.0, 0.97, 0.84], [1.0, 0.8, 0.4], [0.95, 0.5, 0.12]], deckY: 25, deckGlow: 1.0,
    sky: [[0.75, 0.38, 0.1], [1.0, 0.78, 0.42]], fog: [[1.0, 0.8, 0.45], 1 / 260], haze: 1,
    keyC: [1, 0.78, 0.45], keyK: 2.6, under: [[1, 0.62, 0.25], 3.2], hemi: [[1, 0.62, 0.28], [1, 0.72, 0.32], 1.0], rim: [1, 0.6, 0.25] },
};

// The shots, on the voice's lines (work/weight/voice.wav). cam: [t, azimuth° round him from his front, distance, height,
// fov, look height] (the pulsar: [t, azimuth, distance, height, fov]); kg: what the scale rolls to (from the last one)
const S = (t0, t1, world, kg, cam, act) => ({ t0, t1, world, kg, cam, act });
const shots = [
  // the Moon: he glances down at the scale as it settles, back at us; leaps on «тому й стрибаєш у шість разів вище»
  S(0, 14.41, 'moon', 11.6, [[0, 8, 6.5, 0.8, 36, 1.6], [8.8, 6, 7.2, 0.75, 36, 1.7], [10.2, 4, 10, 0.7, 40, 2.2], [14.41, 3, 10.5, 0.7, 40, 1.9]],
    { jump: [10.4, 3.85, 3.0], look: 0.5, peek: [2.6, 5.6] }),
  S(14.41, 17.44, 'mercury', 26.4, [[0, -8, 6.5, 0.7, 36, 1.7], [3.03, -4, 6.0, 0.7, 36, 1.7]], { look: 0.4 }),
  S(17.44, 20.67, 'mars', 26.6, [[0, 25, 6.5, 1.4, 36, 1.7], [3.23, 15, 6.0, 1.3, 36, 1.7]], { look: 0.6 }),
  S(20.67, 27.54, 'venus', 63.3, [[0, -20, 6.5, 1.2, 38, 1.7], [6.87, 10, 5.8, 1.1, 38, 1.7]], { look: 0.3 }),
  S(27.54, 32.69, 'jupiter', 177, [[0, 30, 6.5, 2.2, 38, 1.3], [5.15, 15, 5.5, 2.0, 38, 1.3]], { heavy: [0.8, 0.09, 0.12] }),
  S(32.69, 43.25, 'saturn', 74.5, [[0, -25, 6.0, 0.6, 40, 2.4], [10.56, 20, 7.5, 0.5, 46, 2.8]], { look: 0.5 }),
  S(43.25, 50.64, 'titan', 9.7, [[0, 20, 7, 1.0, 40, 1.8], [7.39, 0, 9, 0.8, 44, 2.6]], { wings: true }),
  S(50.64, 54.34, 'pluto', 4.4, [[0, -15, 6.5, 0.9, 36, 1.7], [3.7, -5, 6.0, 0.8, 36, 1.7]], { look: 0.6 }),
  S(54.34, 57.91, 'sun', 1950, [[0, 15, 6.0, 2.0, 38, 1.2], [3.57, 5, 5.5, 1.8, 38, 1.0]], { heavy: [0.5, 0.12, 0.15], squash: 0.7 }),
  S(57.91, 66.12, 'pulsar', null, [[0, 0, 18, 3, 40], [8.21, 50, 13, 2, 40]]),
  S(66.12, DUR, 'mars', 26.6, [[0, 10, 6.0, 1.4, 36, 1.7], [6.18, 0, 5.4, 1.3, 36, 1.75]], { wave: 0.4, look: 0.8 }),
];
shots.forEach((s, i) => { s.from = i === 0 ? 70 : (shots.slice(0, i).reverse().find(p => p.kg) || {}).kg || 70; });

const CFG = { W, H, worlds, shots, moonMeta, moonSpot: [68100, 4600] };
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script><script>
${moonWorld(moonShot, moonMeta)}
window.__CFG = ${JSON.stringify(CFG)};
// what the scale shows: rolling from the last world's number to this one's over the first second
window.__CFG.shots.forEach(s => { s.lcd = lt => { if (!s.kg) return ''; const u = Math.min(1, Math.max(0, (lt - 0.15) / 1.1)), e = u * u * (3 - 2 * u), v = s.from + (s.kg - s.from) * e; return v >= 1000 ? String(Math.round(v)) : v.toFixed(1); }; });
</script><script src="/page.js"></script></body></html>`;

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js'), '/page.js': path.join(__dirname, 'page.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u] || (u.startsWith('/data/') ? path.join(MOON, u.slice(6)) : u.startsWith('/moon/') ? path.join(MOON, u.slice(6)) : u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null);
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' && !m.text().includes('GL Driver')) console.log(m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 500 });
  const save = async (t, file) => {
    const url = await p.evaluate(t => window.__frame(t), t);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of a1.split(',').map(Number)) { const t0 = Date.now(); await save(t, path.join(WORK, `still_${t}.jpg`)); console.log('still', t, ((Date.now() - t0) / 1000).toFixed(1) + ' s'); }
  } else {
    const dir = path.join(WORK, 'frames'); fs.mkdirSync(dir, { recursive: true });
    const i0 = Math.round((+a1 || 0) * FPS), i1 = Math.min(Math.round(DUR * FPS), a2 ? Math.round(+a2 * FPS) : Infinity);
    for (let i = i0; i < i1; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', i1); }
  }
  await br.close(); srv.close();
})();
