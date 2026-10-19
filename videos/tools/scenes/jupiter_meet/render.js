// Renders the shots of "Знайомся: Юпітер" frame by frame (headless Chromium + three.js, swiftshader), each shot into
// work/jupiter_meet/shot_<name>/f_00000.jpg … The world (Jupiter, its moons, Earth and Mercury for scale, Pele's plume,
// the Europa Clipper, the dive into the clouds, the dawn sky) is built in world.js; the shots — camera, light and what
// is shown, as functions of time — are in shots.js. Both run in the page.
//
//   node scenes/jupiter_meet/render.js <shot> video          -> work/jupiter_meet/shot_<shot>/…
//   node scenes/jupiter_meet/render.js <shot> stills 0,2,4   -> work/jupiter_meet/shot_<shot>_<t>.jpg
//   node scenes/jupiter_meet/render.js list                  -> the shots and their lengths
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'jupiter_meet');
const SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
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
        : u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      if (f.endsWith('.js')) rsp.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('[jm]')) console.log(m.text().slice(0, 4000)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.SHOTS && window.WORLD_READY, null, { timeout: 180000 });
  if (name === 'list') {
    console.log(await p.evaluate(() => Object.entries(window.SHOTS).map(([k, v]) => `${k} ${v.dur}`).join('\n')));
  } else {
    const dur = await p.evaluate(n => { const s = window.SHOTS[n]; if (!s) throw new Error('no shot ' + n); return s.dur; }, name);
    await p.evaluate(async n => { await window.startShot(n); }, name);
    if (process.env.JM_RAW) await p.evaluate((RAW) => { for (const b of Object.values(window.J.bodies)) { const m = b.material; m.fragmentShader = m.fragmentShader.replace('gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);', RAW); m.needsUpdate = true; } }, process.env.JM_RAW);
    if (process.env.JM_DEBUG) console.log(await p.evaluate(() => Object.entries(window.J.bodies).map(([k, b]) => k + ' ' + b.userData.u.map.value.image.src + ' ' + b.userData.u.map.value.image.width).join('\n')));
    const save = async (t, file) => {
      const url = await p.evaluate(([n, tt]) => window.renderShot(n, tt), [name, t]);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    };
    fs.mkdirSync(WORK, { recursive: true });
    if (mode === 'stills') {
      for (const t of list.split(',').map(Number)) await save(t, path.join(WORK, `shot_${name}_${t}.jpg`));
    } else {
      const dir = path.join(WORK, 'shot_' + name); fs.mkdirSync(dir, { recursive: true });
      const n = Math.round(dur * FPS);
      for (let i = 0; i < n; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log(name, 'frame', i, '/', n); }
    }
  }
  await br.close(); srv.close();
})();
