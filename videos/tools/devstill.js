// A dev harness for scenes that keep their shots in a separate file (e.g. scenes/blackhole2/shots.js): loads the scene
// once (the slow part: the site, the galaxy, the sky, the astronaut), then waits for requests and renders stills at once.
//
//   node devstill.js <scene> &                     then write work/<scene>/cmd.json:
//   {"t": [0.5, 12, 30.2], "tag": "a", "reload": true}   -> work/<scene>/dev_a_<t>.jpg, a line in work/<scene>/dev.log
// "reload": re-read every scenes/<scene>/*.js listed in scene.json "include" plus shots, then window.__bhReload().
// Shots must be pure functions of time (the clock jumps straight to each t).
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const { SITE, sitePage } = require('./site');
const TOOLS = __dirname, THREE_DIR = path.join(TOOLS, 'node_modules/three');
const sceneName = process.argv[2];
const SCENE = path.join(TOOLS, 'scenes', sceneName), WORK = path.join(TOOLS, 'work', sceneName);
const cfg = JSON.parse(fs.readFileSync(path.join(SCENE, 'scene.json'), 'utf8'));
const W = cfg.width || 720, H = cfg.height || 1280;
const log = s => { fs.appendFileSync(path.join(WORK, 'dev.log'), s + '\n'); console.log(s); };

function recPage() {
  let src = sitePage();
  const rep = (x, y) => { if (!src.includes(x)) throw new Error('hook not found: ' + x.slice(0, 40)); src = src.replace(x, y); };
  rep('function tick() {', 'window.__rec = { state, byId, BODIES, camera, controls, renderer, scene, THREE, shadowU, titanU };\nfunction tick() {');
  rep('  renderer.render(scene, camera);\n  requestAnimationFrame(tick);', '  if (window.__recCam) window.__recCam();\n  renderer.render(scene, camera);\n  requestAnimationFrame(tick);');
  rep('return LARGE_MAPS.has(key) ? f.replace(".jpg", "_2k.jpg") : f;', 'return f;');
  rep('const FIRST_MAPS = [', 'const FIRST_MAPS = Object.keys(TEXTURES) || [');
  rep('function updateHiRes(dt) {', 'function updateHiRes(dt) { return;');
  rep('loadTexture("moon_normal_2k.jpg", "moonNormal")', 'loadTexture("moon_normal.jpg", "moonNormal")');
  for (const [x, y] of cfg.patches || []) rep(x, y);
  return src;
}
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.jpg': 'image/jpeg', '.png': 'image/png' };
const serve = page => new Promise(res => {
  const srv = http.createServer((req, rsp) => {
    const u = decodeURIComponent(req.url.split('?')[0]); let file = null;
    if (u === '/' || u === '/rec.html') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
    if (u.startsWith('/textures/')) file = path.join(SITE, u);
    if (u.startsWith('/scene/')) file = path.join(SCENE, u.slice(7));
    if (u.startsWith('/fonts/')) file = path.join(TOOLS, u);
    if (!file || !fs.existsSync(file)) { rsp.writeHead(404); return rsp.end(); }
    rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(rsp);
  }).listen(0, '127.0.0.1', () => res(srv));
});

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const srv = await serve(recPage());
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--disable-gpu-watchdog'] });
  const p = await br.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  p.on('pageerror', e => log('pageerror: ' + e.message));
  p.on('crash', () => log('page crashed')); br.on('disconnected', () => log('browser disconnected'));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('[scene]')) log(m.text().slice(0, 300)); });
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript(() => { try { localStorage.setItem('planetarium.quality', 'high'); } catch (e) {} });
  await p.addInitScript({ path: path.join(TOOLS, 'clock.js') });
  for (const f of cfg.include || []) await p.addInitScript({ path: path.join(TOOLS, f) });
  await p.addInitScript({ path: path.join(SCENE, 'cam.js') });
  await p.goto(`http://127.0.0.1:${srv.address().port}/rec.html`);
  await p.addStyleTag({ content: '.topbar,.info,.dock,.tags,.toast,.catalog{display:none!important}' });
  for (let i = 0; i < 4000; i++) {
    const done = await p.evaluate(() => { window.__step(1 / 30); return document.getElementById('loader').classList.contains('done') && !!window.__rec; });
    if (done) break; await p.waitForTimeout(20);
  }
  const t0 = Date.now();
  await p.evaluate(async c => { const r = window.__rec, s = r.state; s.live = false; s.simMs = Date.parse(c.date); s.rate = c.rate; s.paused = false; if (window.__sceneSetup) await window.__sceneSetup(r, c); }, cfg);
  for (let i = 0; i < 20; i++) { await p.evaluate(() => window.__step(1 / 30)); await p.waitForTimeout(20); }
  log(`ready (setup ${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  const cmdFile = path.join(WORK, 'cmd.json');
  for (;;) {
    if (!fs.existsSync(cmdFile)) { await new Promise(r => setTimeout(r, 700)); continue; }
    let cmd; try { cmd = JSON.parse(fs.readFileSync(cmdFile, 'utf8')); } catch (e) { await new Promise(r => setTimeout(r, 300)); continue; }
    fs.unlinkSync(cmdFile);
    if (cmd.quit) break;
    if (cmd.reload) {
      for (const f of (cfg.include || []).filter(f => f.startsWith('scenes/'))) await p.evaluate(src => { (0, eval)(src); }, fs.readFileSync(path.join(TOOLS, f), 'utf8'));
      await p.evaluate(() => window.__bhReload && window.__bhReload());
    }
    for (const t of cmd.t || []) {
      const s0 = Date.now();
      const url = await p.evaluate(t => { window.__t0 = window.__vt() + 1 / 30 - t; window.__step(1 / 30); return document.getElementById('scene').toDataURL('image/jpeg', 0.92); }, t);
      fs.writeFileSync(path.join(WORK, `dev_${cmd.tag || 'x'}_${t}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
      log(`still ${cmd.tag || 'x'} ${t}: ${((Date.now() - s0) / 1000).toFixed(1)} s`);
    }
    log('done ' + (cmd.tag || 'x'));
  }
  await br.close(); srv.close();
})();
