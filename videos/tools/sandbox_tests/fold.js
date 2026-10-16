const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SITE = '/home/user/cloud/planetarium', OUT = process.argv[2], SCEN = process.argv[3] || 'stop-earth', SECS = +(process.argv[4] || 50);
const THREE_DIR = (process.env.THREE_DIR || path.join(__dirname, 'three/package')), CLOCK = '/home/user/cloud/videos/tools/clock.js';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };
const srv = http.createServer((req, rsp) => { let u = decodeURIComponent(req.url.split('?')[0]); if (u === '/') u = '/index.html';
  const f = path.join(SITE, u); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
  rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  let body = fs.readFileSync(f); if (u === '/js/main.js') body = body.toString() + '\nwindow.__sb = sandbox;\n'; rsp.end(body); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const url = `http://127.0.0.1:${srv.address().port}/#sandbox-${SCEN}`;
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript({ path: CLOCK });
  await p.goto(url, { waitUntil: 'domcontentloaded' });
  for (let i = 0; i < 3000; i++) { if (await p.evaluate(() => { window.__step(1/30); return document.getElementById('loader').classList.contains('done'); })) break; await p.waitForTimeout(20); }
  await p.waitForLoadState('networkidle').catch(() => {});
  if (await p.isVisible('#welcomeOk').catch(() => false)) await p.click('#welcomeOk');
  for (let i = 0; i < 120; i++) await p.evaluate(() => window.__step(1/30));
  await p.screenshot({ path: path.join(OUT, 'open.png') });
  await p.click('#sbsMin'); for (let i = 0; i < 10; i++) await p.evaluate(() => window.__step(1/30));
  await p.screenshot({ path: path.join(OUT, 'min.png') });
  console.log(await p.evaluate(() => localStorage.getItem('sbStoryMin')));
  await br.close(); srv.close();
})();
