// «Скільки ти протримаєшся на кожній планеті?» v2 — frames (page.js draws them, fx.js lays the effects on the figure).
//
//   node scenes/survive2/render.js stills 1.5,3            -> work/survive2/still_<t>.jpg
//   node scenes/survive2/render.js video [from to] [dir]   -> work/survive2/<dir|frames>/f_00000.jpg … (seconds)
//
// For now the timeline holds the two test shots of 2.11.2026 (the Sun 0–6.5 s, Neptune 6.5–13 s).
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'survive2');
const [mode = 'stills', a1 = '1', a2, a3] = process.argv.slice(2);
const W = +(process.env.W || 720), H = +(process.env.H || 1280), FPS = 30;
const shots = [{ t0: 0, t1: 4.8, world: "sun" }, { t0: 4.8, t1: 11.3, world: "neptune" }];
const DUR = shots[shots.length - 1].t1;

const page = `<!doctype html><html><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script>
<script>window.__CFG = ${JSON.stringify({ W, H, shots })};</script>
<script src="/fx.js"></script><script src="/page.js"></script></body></html>`;

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js'), '/page.js': path.join(__dirname, 'page.js'), '/fx.js': path.join(__dirname, 'fx.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u];
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
    const i0 = Math.round((+a1 || 0) * FPS), i1 = Math.min(Math.round(DUR * FPS), a2 ? Math.round(+a2 * FPS) : Infinity);
    for (let i = i0; i < i1; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', i1); }
  }
  await br.close(); srv.close();
})();
