// A story step with a wide shot (heavy-sun, step 3: the whole inner system): pause, pick Mercury, play.
// Does the camera come back to the wide shot (not pulled in by the site's limits)? node focus_test3.js <resume button id> <outdir>
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SITE = '/home/user/cloud/planetarium', BTN = process.argv[2], OUT = process.argv[3];
const THREE_DIR = path.join(__dirname, 'three/package'), CLOCK = '/home/user/cloud/videos/tools/clock.js';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png' };
const srv = http.createServer((req, rsp) => { let u = decodeURIComponent(req.url.split('?')[0]); if (u === '/') u = '/index.html';
  const f = path.join(SITE, u); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
  let body = fs.readFileSync(f); if (u === '/js/main.js') body = body.toString() + '\nwindow.__sb = sandbox;\n';
  rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); rsp.end(body); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript({ path: CLOCK });
  await p.goto(`http://127.0.0.1:${srv.address().port}/#sandbox-heavy-sun`, { waitUntil: 'domcontentloaded' });
  for (let i = 0; i < 3000; i++) { if (await p.evaluate(() => { window.__step(1/30); return document.getElementById('loader').classList.contains('done'); })) break; await p.waitForTimeout(20); }
  const step = async n => { for (let i = 0; i < n; i++) await p.evaluate(() => window.__step(1/30)); };
  const where = () => p.evaluate(() => `cam→Sun ${camera.position.distanceTo(byId.sun.world).toFixed(1)}, target→Mercury ${controls.target.distanceTo(byId.mercury.world).toFixed(1)}, maxD ${controls.maxDistance}, index ${state.index}`);
  await step(120); await p.evaluate(() => window.__sb._storyStep(2)); await step(150);
  console.log('story     ', await where()); await p.screenshot({ path: path.join(OUT, 'f0.png') });
  await p.click('#sbsPause'); await step(10);
  await p.evaluate(() => focusBody(byId.mercury.index)); await step(120); console.log('picked    ', await where());
  await p.screenshot({ path: path.join(OUT, 'f1.png') });
  await p.click('#' + BTN); await step(3); console.log('played+3f ', await where()); await step(60); console.log('played+2s ', await where());
  await p.screenshot({ path: path.join(OUT, 'f2.png') });
  await br.close(); srv.close();
})();
