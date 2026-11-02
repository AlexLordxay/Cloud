// «Скільки ти протримаєшся на кожній планеті?» v2 — frames. page.js draws them (fx.js lays the effects on the figure,
// ground.js builds the worlds with ground); the shots come from timeline.json (timeline.py, on the author's voice).
//
//   node scenes/survive2/render.js stills 1.5,3            -> work/survive2/still_<t>.jpg
//   node scenes/survive2/render.js video [from to] [dir]   -> work/survive2/<dir|frames>/f_00000.jpg … (seconds)
//   TEST=1 …                                               -> the two test shots of 2.11 (the Sun, Neptune) instead
//
// The Moon is the real one (moon_meet's site 'south'; first: python3 scenes/moon_meet/terrain_data.py south).
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const { moonWorld } = require('../moon_meet/world');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'survive2');
const MOON = path.join(TOOLS, 'work', 'moon_meet', 'south'), SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [mode = 'stills', a1 = '1', a2, a3] = process.argv.slice(2);
const W = +(process.env.W || 720), H = +(process.env.H || 1280), FPS = 30;
const TL = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.json')));
const shots = process.env.TEST ? [{ t0: 0, t1: 4.8, world: 'sun' }, { t0: 4.8, t1: 11.3, world: 'neptune' }] : TL.shots;
const DUR = shots[shots.length - 1].t1;
if (!fs.existsSync(path.join(MOON, 'meta.json'))) { console.log('first: python3 scenes/moon_meet/terrain_data.py south'); process.exit(1); }
const moonMeta = JSON.parse(fs.readFileSync(path.join(MOON, 'meta.json')));
const moonShot = { site: 'south', mesh: 1000, earth: [0, 4.5], earthFace: [49, 31, 40], earthLean: 28, earthshine: 2.5, earthScale: 2 };

// The worlds with ground (as scenes/weight/render.js): sun [azimuth from his front, elevation]; sunC/amb: linear light on
// the ground; sky [zenith, horizon] and fog: gamma-encoded; keyC/keyK, hemi: the light on the figure; ground: the recipe.
const MOON_CRATERS = [[5.0, 0.3, 1.1, 0.22, 11], [14, 1.2, 4.5, 0.4, 23], [45, 5, 18, 0.6, 37], [190, 18, 75, 0.7, 53]];
const worlds = {
  moon: { moon: true, face: Math.PI, sunC: [2.3, 2.25, 2.19], amb: [0.025, 0.03, 0.04], Rmax: 2600,
    ground: { craters: MOON_CRATERS, swell: 0.9 }, keyC: [1, 0.965, 0.92], keyK: 3.2, hemi: [[0.04, 0.045, 0.07], [0.54, 0.53, 0.51], 0.16], blob: 0.9 },
  mercury: { R: 2439.7e3, sun: [174, 9], sunC: [3.4, 3.2, 3.0], amb: [0.012, 0.012, 0.015], alb: [0.22, 0.2, 0.18], Rmax: 4000,
    ground: { craters: [[5.0, 0.3, 1.1, 0.3, 11], [14, 1.2, 4.5, 0.5, 23], [45, 5, 18, 0.7, 37], [190, 18, 75, 0.8, 53]], swell: 0.9, mountains: [140, 700, 800], rocks: 0.08 },
    sky: [[0, 0, 0], [0, 0, 0]], sunDisc: [3.0, 2.9, 2.7], sunDeg: 1.6, sunGlow: 2.2, stars: 1200,
    keyC: [1, 0.97, 0.93], keyK: 3.6, hemi: [[0.03, 0.03, 0.04], [0.32, 0.3, 0.27], 0.2], rim: [0.9, 0.85, 0.75], blob: 0.85 },
  mars: { R: 3389.5e3, sun: [105, 22], sunC: [1.9, 1.75, 1.6], amb: [0.3, 0.2, 0.13], alb: [0.46, 0.25, 0.13], grain: 0.8, Rmax: 3000,
    ground: { craters: [[6, 0.4, 1.2, 0.18, 11], [18, 1.5, 5, 0.35, 23], [60, 6, 20, 0.5, 37]], craterK: 0.7, swell: 0.8, dunes: [9, 0.3], mountains: [70, 600, 700], rocks: 0.14 },
    sky: [[0.56, 0.44, 0.34], [0.87, 0.71, 0.53]], fog: [[0.84, 0.66, 0.5], 1 / 2200], sunDisc: [1.2, 1.15, 1.1], sunDeg: 0.35, sunGlow: 0.6, haze: 1, dust: 1,
    keyC: [1, 0.92, 0.84], keyK: 2.6, hemi: [[0.78, 0.62, 0.5], [0.55, 0.32, 0.2], 0.5], marsEnv: true, rim: [0.5, 0.35, 0.25], blob: 0.6 },
  venus: { R: 6051.8e3, sun: [-20, 55], sunC: [0.45, 0.32, 0.15], amb: [0.62, 0.42, 0.19], alb: [0.26, 0.23, 0.21], grain: 0.8, shadowHard: 0.2, Rmax: 2500,
    ground: { swell: 0.5, plates: 0.16, mountains: [260, 650, 900] }, sky: [[0.64, 0.46, 0.2], [0.93, 0.73, 0.42]], fog: [[0.88, 0.66, 0.38], 1 / 900], haze: 1,
    glowC: [0.05, 0.012, 0.0], expo: 0.8, grade: [1.0, 0.92, 0.82],
    keyC: [1, 0.76, 0.42], keyK: 0.7, hemi: [[1, 0.75, 0.42], [0.5, 0.35, 0.2], 1.3], rim: [0.6, 0.4, 0.15], blob: 0.35 },
  titan: { R: 2574.7e3, sun: [100, 35], sunC: [0.5, 0.34, 0.18], amb: [0.45, 0.28, 0.12], alb: [0.22, 0.17, 0.12], grain: 0.6, shadowHard: 0.2, Rmax: 2500,
    ground: { swell: 0.6, dunes: [14, 0.6] }, sky: [[0.52, 0.32, 0.14], [0.86, 0.56, 0.26]], fog: [[0.82, 0.52, 0.24], 1 / 380], haze: 1,
    keyC: [1, 0.72, 0.42], keyK: 0.8, hemi: [[0.95, 0.62, 0.32], [0.42, 0.26, 0.13], 1.2], rim: [0.6, 0.35, 0.15], blob: 0.35 },
};

const CFG = { W, H, worlds, shots, moonMeta, moonSpot: [68100, 4600] };
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script>
<script>${moonWorld(moonShot, moonMeta)}
window.__CFG = ${JSON.stringify(CFG)};</script>
<script src="/fx.js"></script><script src="/ground.js"></script><script src="/page.js"></script></body></html>`;

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js'), '/page.js': path.join(__dirname, 'page.js'), '/fx.js': path.join(__dirname, 'fx.js'),
    '/ground.js': path.join(__dirname, 'ground.js') };
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
  p.on('console', m => { if ((m.type() === 'error' || m.type() === 'warning') && !m.text().includes('GL Driver') && !m.text().includes('GPU stall')) console.log(m.type(), m.text().slice(0, 600)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 500 });
  const save = async (t, file) => {
    const url = await p.evaluate(t => window.__frame(t), t);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of a1.split(',').map(Number)) { const t0 = Date.now(); await save(t, path.join(WORK, `still_${t}.jpg`)); console.log('still', t, ((Date.now() - t0) / 1000).toFixed(1) + ' s', process.env.DBG ? await p.evaluate(() => JSON.stringify(window.__last)) : ''); }
  } else {
    const dir = path.join(WORK, a3 || 'frames'); fs.mkdirSync(dir, { recursive: true });
    const i0 = Math.round((+a1 || 0) * FPS), i1 = Math.min(Math.round(DUR * FPS), a2 ? Math.round(+a2 * FPS) : Infinity);
    for (let i = i0; i < i1; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', i1); }
  }
  await br.close(); srv.close();
})();
