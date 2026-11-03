// «На якій я планеті?» — головоломка №1 (Венера): the frames. page.js draws them on survive2's Venus (its ground.js);
// the beats and the camera are in scene.json.
//
//   node scenes/puzzle_venus/render.js stills 1.5,3                -> work/puzzle_venus/still_<t>.jpg
//   node scenes/puzzle_venus/render.js video [from to] [dir]       -> work/puzzle_venus/<dir|frames>/f_00000.jpg …
//   node scenes/puzzle_venus/render.js fill [from] [-] [dir]       -> the same, several processes side by side
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'puzzle_venus'), S2 = path.join(TOOLS, 'scenes', 'survive2');
const SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [mode = 'stills', a1 = '1', a2, a3] = process.argv.slice(2);
const W = +(process.env.W || 720), H = +(process.env.H || 1280), FPS = 30;
const SC = JSON.parse(fs.readFileSync(path.join(__dirname, 'scene.json')));
const DUR = SC.duration;

// survive2's Venus, as it is
const worlds = {
  venus: { R: 6051.8e3, sun: [-20, 55], sunC: [0.45, 0.32, 0.15], amb: [0.62, 0.42, 0.19], alb: [0.26, 0.23, 0.21], grain: 0.8, shadowHard: 0.2, Rmax: 2500,
    ground: { swell: 0.5, plates: 0.16, mountains: [260, 650, 900] }, sky: [[0.64, 0.46, 0.2], [0.93, 0.73, 0.42]], fog: [[0.88, 0.66, 0.38], 1 / 900], haze: 1,
    glowC: [0.05, 0.012, 0.0], expo: 0.8, grade: [1.0, 0.92, 0.82],
    keyC: [1, 0.76, 0.42], keyK: 0.7, hemi: [[1, 0.75, 0.42], [0.5, 0.35, 0.2], 1.3], rim: [0.6, 0.4, 0.15], blob: 0.35 },
};
const CFG = { W, H, worlds, beats: SC.beats, cam: SC.cam, sky: SC.sky };
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script>
<script>window.__CFG = ${JSON.stringify(CFG)};</script>
<script src="/ground.js"></script><script src="/page.js"></script></body></html>`;

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js'), '/page.js': path.join(__dirname, 'page.js'), '/ground.js': path.join(S2, 'ground.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u] || (u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null);
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
    for (const t of a1.split(',').map(Number)) { const t0 = Date.now(); await save(t, path.join(WORK, `still_${t}.jpg`)); console.log('still', t, ((Date.now() - t0) / 1000).toFixed(1) + ' s'); }
  } else {
    const dir = path.join(WORK, a3 || 'frames'); fs.mkdirSync(dir, { recursive: true });
    const N = Math.round(DUR * FPS);
    if (mode === 'fill') {
      const s0 = Math.round((+a1 || 0) * FPS);
      for (let k = 0; k < N; k++) {
        const i = (s0 + k) % N, f = path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`), lock = f + '.lock';
        if (fs.existsSync(f)) continue;
        try { fs.closeSync(fs.openSync(lock, 'wx')); } catch (e) { continue; }
        await save(i / FPS, f + '.tmp'); fs.renameSync(f + '.tmp', f); fs.unlinkSync(lock);
        if (i % 30 === 0) console.log('frame', i);
      }
    } else {
      const i0 = Math.round((+a1 || 0) * FPS), i1 = Math.min(N, a2 ? Math.round(+a2 * FPS) : Infinity);
      for (let i = i0; i < i1; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', i1); }
    }
  }
  await br.close(); srv.close();
})();
