// Site -> sandbox (run, pause/play) -> close: do the planets go back to their real places?
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SITE = '/home/user/cloud/planetarium', OUT = process.argv[2], MODE = process.argv[3] || 'plain';
const THREE_DIR = path.join(__dirname, 'three/package'), CLOCK = '/home/user/cloud/videos/tools/clock.js';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png' };
const srv = http.createServer((req, rsp) => { let u = decodeURIComponent(req.url.split('?')[0]); if (u === '/') u = '/index.html';
  const f = path.join(SITE, u); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
  rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); rsp.end(fs.readFileSync(f)); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 1280, height: 800 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript({ path: CLOCK });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`, { waitUntil: 'domcontentloaded' });
  for (let i = 0; i < 3000; i++) { if (await p.evaluate(() => { window.__step(1/30); return document.getElementById('loader').classList.contains('done'); })) break; await p.waitForTimeout(20); }
  if (await p.isVisible('#welcomeOk').catch(() => false)) await p.click('#welcomeOk');
  const step = async n => { for (let i = 0; i < n; i++) await p.evaluate(() => window.__step(1/30)); };
  const snap = () => p.evaluate(() => { const o = {}; for (const id of ['earth', 'moon', 'mars', 'jupiter']) o[id] = byId[id].world.toArray().map(x => +x.toFixed(1)); o.paused = state.paused; o.date = document.getElementById('date').value; return JSON.stringify(o); });
  await step(90); console.log('site   ', await snap()); await p.screenshot({ path: path.join(OUT, 'c0.png') });
  await p.click('#sandboxBtn'); await step(120); console.log('sandbox', await snap());
  if (MODE === 'pause') { await p.click('#pause'); await step(30); await p.click('#pause'); await step(60); console.log('sb p/p ', await snap()); }
  if (MODE === 'sbpause') { await p.click('#sbPlay'); await step(30); await p.click('#sbPlay'); await step(60); console.log('sb p/p ', await snap()); }
  if (MODE === 'pauseclose') { await p.click('#pause'); await step(30); }
  await p.screenshot({ path: path.join(OUT, 'c1.png') });
  await p.click('#sbClose'); await step(150); console.log('closed ', await snap()); await p.screenshot({ path: path.join(OUT, 'c2.png') });
  if (MODE === 'pauseclose') { await p.click('#pause'); await step(90); console.log('resumed', await snap()); await p.screenshot({ path: path.join(OUT, 'c3.png') }); }
  await br.close(); srv.close();
})();
