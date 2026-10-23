// Renders the 3D shots of the Kadenyuk video frame by frame (headless Chromium + three.js, swiftshader) into
// work/kadenyuk/shot_<name>/f_00000.jpg … and marks.json (where the shot's map mark lands, per frame).
// The world (the Earth, the NASA shuttle model) is world.js, the shots shots.js.
//
//   node scenes/kadenyuk/render.js <shot> video           -> work/kadenyuk/shot_<shot>/…
//   node scenes/kadenyuk/render.js <shot> stills 0,2,4    -> work/kadenyuk/shot_<shot>_<t>.jpg
//   (models: work/kadenyuk/model/, the detailed map: python3 scenes/kadenyuk/patch.py)
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'kadenyuk');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30;
const NM = path.join(TOOLS, 'node_modules/three');

const page = `<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/GLTFLoader.js"></script><script src="/DRACOLoader.js"></script>
<script src="/scene/world.js"></script><script src="/scene/shots.js"></script></body></html>`;

(async () => {
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(NM, 'build/three.min.js')
        : u === '/GLTFLoader.js' ? path.join(NM, 'examples/js/loaders/GLTFLoader.js')
        : u === '/DRACOLoader.js' ? path.join(NM, 'examples/js/loaders/DRACOLoader.js')
        : u.startsWith('/draco/') ? path.join(NM, 'examples/js/libs/draco/gltf', u.slice(7))
        : u.startsWith('/work/') ? path.join(WORK, u.slice(6))
        : u.startsWith('/scene/') ? path.join(__dirname, u.slice(7))
        : u.startsWith('/model/') ? path.join(WORK, 'model', u.slice(7))
        : u.startsWith('/tex/') ? path.join(TOOLS, '../../planetarium/textures', u.slice(5)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      if (f.endsWith('.wasm')) rsp.writeHead(200, { 'Content-Type': 'application/wasm' });
      else if (f.endsWith('.js')) rsp.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { const s = m.text(); if (!/Failed to load|SHUT-|GPU stall|\[part\]/.test(s)) console.log(s.slice(0, 2000)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.WORLD_READY && window.SHOTS, null, { timeout: 180000 });
  const dur = await p.evaluate(n => { const s = window.SHOTS[n]; if (!s) throw new Error('no shot ' + n); return s.dur; }, name);
  const shot = t => p.evaluate(([n, tt]) => window.render(window.SHOTS[n].at(tt)), [name, t]);
  fs.mkdirSync(WORK, { recursive: true });
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) {
      const r = await shot(t); fs.writeFileSync(path.join(WORK, `shot_${name}_${t}.jpg`), Buffer.from(r.url.split(',')[1], 'base64'));
    }
  } else {
    const dir = path.join(WORK, 'shot_' + name); fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const n = Math.round(dur * FPS), marks = [];
    for (let i = 0; i < n; i++) {
      const r = await shot(i / FPS); marks.push(r.mark);
      fs.writeFileSync(path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`), Buffer.from(r.url.split(',')[1], 'base64'));
      if (i % 30 === 0) console.log(name, 'frame', i, '/', n);
    }
    fs.writeFileSync(path.join(dir, 'marks.json'), JSON.stringify(marks));
  }
  await br.close(); srv.close();
})();
