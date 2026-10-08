// Records a scene from the planetarium frame by frame, with a virtual clock (every frame exactly 1/FPS apart).
//
//   node rec.js <scene> video [t0] [t1]    -> work/<scene>/frames/f_00000.jpg … (default: whole scene)
//   node rec.js <scene> stills 5,12,30     -> work/<scene>/still_<t>.jpg (quick storyboard)
//
// The page is the real site (planetarium/index.html with its css/ and js/ inline, see site.js) with two small hooks added in memory, served by a built-in
// static server; the scene's cam.js is injected before the page loads and drives the camera.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const { SITE, sitePage } = require('./site');
const TOOLS = __dirname, THREE_DIR = path.join(TOOLS, 'node_modules/three');
const [sceneName, mode = 'video', a, b] = process.argv.slice(2);
if (!sceneName) { console.log('usage: node rec.js <scene> video [t0 t1] | stills t1,t2,…'); process.exit(1); }
// REC_W / REC_H override the frame size (e.g. a 1600×630 still for a link card); REC_TAG keeps such stills apart.
const SCENE = path.join(TOOLS, 'scenes', sceneName), WORK = path.join(TOOLS, 'work', sceneName + (process.env.REC_TAG ? '_' + process.env.REC_TAG : ''));
const cfg = JSON.parse(fs.readFileSync(path.join(SCENE, 'scene.json'), 'utf8'));
const FPS = cfg.fps || 30, W = +process.env.REC_W || cfg.width || 720, H = +process.env.REC_H || cfg.height || 1280;

// The site with the recording hooks: expose a few internals, and let the scene move the camera right before rendering.
function recPage() {
  let src = sitePage();
  const rep = (x, y) => { if (!src.includes(x)) throw new Error('site changed, hook not found: ' + x.slice(0, 40)); src = src.replace(x, y); };
  rep('function tick() {', 'window.__rec = { state, byId, BODIES, camera, controls, renderer, scene, THREE, shadowU, titanU };\nfunction tick() {');
  rep('  renderer.render(scene, camera);\n  requestAnimationFrame(tick);', '  if (window.__recCam) window.__recCam();\n  renderer.render(scene, camera);\n  requestAnimationFrame(tick);');
  // Videos: every map at full size from the first frame (the site starts at 2K and swaps in 4K near a body,
  // which would show as a pop mid-shot), all loaded before the scene opens.
  rep('return LARGE_MAPS.has(key) ? f.replace(".jpg", "_2k.jpg") : f;', 'return f;');
  rep('const FIRST_MAPS = [', 'const FIRST_MAPS = Object.keys(TEXTURES) || [');
  rep('function updateHiRes(dt) {', 'function updateHiRes(dt) { return;');
  rep('loadTexture("moon_normal_2k.jpg", "moonNormal")', 'loadTexture("moon_normal.jpg", "moonNormal")');
  for (const [x, y] of cfg.patches || []) rep(x, y);
  return src;
}
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.jpg': 'image/jpeg', '.png': 'image/png' };
function serve(page) {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      let file = null;
      if (u === '/' || u === '/rec.html') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      if (u.startsWith('/textures/')) file = path.join(SITE, u);
      if (!file || !file.startsWith(SITE) || !fs.existsSync(file)) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}

(async () => {
  if (!fs.existsSync(THREE_DIR)) { console.log('run "npm install" in videos/tools first'); process.exit(1); }
  fs.mkdirSync(WORK, { recursive: true });
  const srv = await serve(recPage());
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('[scene]')) console.log(m.text().slice(0, 300)); });
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript(() => { try { localStorage.setItem('planetarium.quality', 'high'); } catch (e) {} });
  await p.addInitScript({ path: path.join(TOOLS, 'clock.js') });
  await p.addInitScript({ path: path.join(SCENE, 'cam.js') });
  await p.goto(`http://127.0.0.1:${srv.address().port}/rec.html`);
  await p.addStyleTag({ content: '.topbar,.info,.dock,.tags,.toast,.catalog{display:none!important}' });
  for (let i = 0; i < 4000; i++) {
    const done = await p.evaluate(() => { window.__step(1 / 30); return document.getElementById('loader').classList.contains('done') && !!window.__rec; });
    if (done) break;
    await p.waitForTimeout(20);
  }
  // Scene setup: date, speed and anything scene-specific (cam.js defines window.__sceneSetup).
  await p.evaluate(async c => {
    const r = window.__rec, s = r.state;
    s.live = false; s.simMs = Date.parse(c.date); s.rate = c.rate; s.paused = false;
    if (window.__sceneSetup) await window.__sceneSetup(r, c);
  }, cfg);
  for (let i = 0; i < 45; i++) { await p.evaluate(() => window.__step(1 / 30)); await p.waitForTimeout(30); }   // textures settle, particles warm up
  await p.evaluate(() => { window.__t0 = window.__vt(); });
  const grab = async dt => {
    const url = await p.evaluate(dt => { window.__step(dt); return document.getElementById('scene').toDataURL('image/jpeg', 0.94); }, dt);
    return Buffer.from(url.split(',')[1], 'base64');
  };
  if (mode === 'stills') {
    let cur = 0;
    for (const t of String(a).split(',').map(Number)) {
      while (cur < t - 1e-6) {
        // FAST=1: jump to each still in one-second steps (for scenes whose camera is a pure function of time)
        const d = process.env.FAST && t - cur > 1.5 / FPS ? Math.min(1, t - cur - 1 / FPS) : Math.min(1 / FPS, t - cur);
        if (t - cur > 1 / FPS + 1e-6) await p.evaluate(d => window.__step(d), d);
        else fs.writeFileSync(path.join(WORK, `still_${t}.jpg`), await grab(d));
        cur += d;
      }
    }
  } else {
    const dir = path.join(WORK, 'frames');
    fs.mkdirSync(dir, { recursive: true });
    const t0 = a != null ? +a : 0, t1 = b != null ? +b : cfg.duration;
    const n0 = Math.round(t0 * FPS), n1 = Math.round(t1 * FPS);
    for (let i = 0; i < n0; i++) await p.evaluate(dt => window.__step(dt), 1 / FPS);   // run up to t0 without saving
    const start = Date.now();
    for (let i = n0; i < n1; i++) {
      fs.writeFileSync(path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`), await grab(1 / FPS));
      if (i % 150 === 0) console.log('frame', i, '/', n1, ((Date.now() - start) / 1000 / (i - n0 + 1)).toFixed(2), 's/frame');
    }
  }
  await br.close();
  srv.close();
})();
