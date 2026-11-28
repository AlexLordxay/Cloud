// Pause / resume and watch for jumps: node pause_test.js <hash ('' = site)> <button id> <outdir>
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SITE = '/home/user/cloud/planetarium', HASH = process.argv[2] || '', BTN = process.argv[3], OUT = process.argv[4];
const THREE_DIR = path.join(__dirname, 'three/package'), CLOCK = '/home/user/cloud/videos/tools/clock.js';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png' };
const srv = http.createServer((req, rsp) => { let u = decodeURIComponent(req.url.split('?')[0]); if (u === '/') u = '/index.html';
  const f = path.join(SITE, u); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
  let body = fs.readFileSync(f); if (u === '/js/main.js') body = body.toString() + '\nwindow.__sb = sandbox;\n';
  rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); rsp.end(body); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 1280, height: 800 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript({ path: CLOCK });
  await p.goto(`http://127.0.0.1:${srv.address().port}/${HASH}`, { waitUntil: 'domcontentloaded' });
  for (let i = 0; i < 3000; i++) { if (await p.evaluate(() => { window.__step(1/30); return document.getElementById('loader').classList.contains('done'); })) break; await p.waitForTimeout(20); }
  if (await p.isVisible('#welcomeOk').catch(() => false)) await p.click('#welcomeOk');
  const snap = () => p.evaluate(() => { const o = {}; for (const id of ['earth', 'moon', 'mars', 'jupiter', 'io']) o[id] = byId[id].world.toArray().map(x => +x.toFixed(2)); return o; });
  const run = async (n, tag) => { let prev = await snap(); for (let i = 0; i < n; i++) { await p.evaluate(() => window.__step(1/30)); const s = await snap();
    for (const k in s) { const d = Math.hypot(...s[k].map((v, j) => v - prev[k][j])); if (d > 2) console.log(tag, i, 'JUMP', k, d.toFixed(2), JSON.stringify(prev[k]), '->', JSON.stringify(s[k])); } prev = s; } };
  await run(150, 'warm');
  await p.screenshot({ path: path.join(OUT, 'p1_before.png') });
  console.log('before', JSON.stringify(await snap()));
  await p.click('#' + BTN); console.log('clicked pause');
  await run(90, 'paused');
  await p.screenshot({ path: path.join(OUT, 'p2_paused.png') });
  console.log('paused', JSON.stringify(await snap()));
  await p.click('#' + BTN); console.log('clicked play');
  await run(120, 'resumed');
  await p.screenshot({ path: path.join(OUT, 'p3_after.png') });
  console.log('after', JSON.stringify(await snap()));
  await br.close(); srv.close();
})();
