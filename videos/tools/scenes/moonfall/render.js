// Renders «Що, якби Місяць упав на Землю?» frame by frame (headless Chromium + three.js, swiftshader), each shot into
// work/moonfall/shot_<name>/f_00000.jpg … The world (the Earth, the Moon, the rubble) is
// built in world.js; the film — the clock, the camera, what is shown — is in shots.js. Both run in the page.
// MF_FROM / MF_TO (frame numbers): render only that stretch of a video (frames already on disk are skipped).
//
//   node scenes/moonfall/render.js <shot> video          -> work/moonfall/shot_<shot>/…
//   node scenes/moonfall/render.js <shot> stills 0,2,4   -> work/moonfall/shot_<shot>_<t>.jpg
//   node scenes/moonfall/render.js list                  -> the shots and their lengths
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'moonfall');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30;

const page = `<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/scene/world.js"></script><script src="/scene/shots.js"></script>
</body></html>`;

(async () => {
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u.startsWith('/scene/') ? path.join(__dirname, u.slice(7))
        : u.startsWith('/maps/') ? path.join(WORK, 'maps', u.slice(6))
        : u.startsWith('/tex/') ? path.join(TOOLS, '../../planetarium/textures', u.slice(5)) : null;   // the site's textures
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      if (f.endsWith('.js')) rsp.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('[mf]')) console.log(m.text().slice(0, 4000)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.SHOTS && window.WORLD_READY, null, { timeout: 180000 });
  if (name === 'list') {
    console.log(await p.evaluate(() => Object.entries(window.SHOTS).map(([k, v]) => `${k} ${v.dur}`).join('\n')));
  } else {
    const dur = await p.evaluate(n => { const s = window.SHOTS[n]; if (!s) throw new Error('no shot ' + n); return s.dur; }, name);
    await p.evaluate(async n => { await window.startShot(n); }, name);
    // CX_EVAL: a line of JS run in the page after the shot is set up (for checks: hide a layer, change a value)
    if (process.env.CX_EVAL) await p.evaluate(src => { (new Function('X', 'SHOTS', src))(window.X, window.SHOTS); }, process.env.CX_EVAL);
    const save = async (t, file) => {
      const url = await p.evaluate(([n, tt]) => window.renderShot(n, tt), [name, t]);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    };
    fs.mkdirSync(WORK, { recursive: true });
    if (mode === 'stills') {
      for (const t of list.split(',').map(Number)) {
        await save(t, path.join(WORK, `shot_${name}_${t}.jpg`));
        fs.writeFileSync(path.join(WORK, `shot_${name}_${t}.json`), JSON.stringify(await p.evaluate(() => window.X.state || {})));
      }
    } else {
      const dir = path.join(WORK, 'shot_' + name); fs.mkdirSync(dir, { recursive: true });
      const n = Math.round(dur * FPS);
      const from = +(process.env.MF_FROM || 0), to = Math.min(n, +(process.env.MF_TO || n));
      for (let i = from; i < to; i++) {
        const f = path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`);
        if (fs.existsSync(f) && fs.statSync(f).size > 1000) continue;
        await save(i / FPS, f);
        fs.writeFileSync(f.replace('.jpg', '.json'), JSON.stringify(await p.evaluate(() => window.X.state || {})));
        if (i % 30 === 0) console.log(name, 'frame', i, '/', n, new Date().toISOString().slice(11, 19));
      }
    }
  }
  await br.close(); srv.close();
})();
