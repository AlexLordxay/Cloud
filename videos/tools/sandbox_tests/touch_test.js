// Run a story and log close passes: pairs whose drawn spheres overlap (scene distance < drawn radii), with the real distance.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const SITE = '/home/user/cloud/planetarium', SCEN = process.argv[2], FROM = +(process.argv[3] || 0), SECS = +(process.argv[4] || 60);
const THREE_DIR = path.join(__dirname, 'three/package'), CLOCK = '/home/user/cloud/videos/tools/clock.js';
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png' };
const srv = http.createServer((req, rsp) => { let u = decodeURIComponent(req.url.split('?')[0]); if (u === '/') u = '/index.html';
  const f = path.join(SITE, u); if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
  let body = fs.readFileSync(f); if (u === '/js/main.js') body = body.toString() + '\nwindow.__sb = sandbox;\n';
  rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); rsp.end(body); });
(async () => {
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 300, height: 500 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
  await p.route('**/fonts.g*/**', r => r.abort());
  await p.addInitScript({ path: CLOCK });
  await p.goto(`http://127.0.0.1:${srv.address().port}/#sandbox-${SCEN}`, { waitUntil: 'domcontentloaded' });
  for (let i = 0; i < 3000; i++) { if (await p.evaluate(() => { window.__step(1/30); return document.getElementById('loader').classList.contains('done'); })) break; await p.waitForTimeout(20); }
  for (let i = 0; i < 60; i++) await p.evaluate(() => window.__step(1/30));
  await p.evaluate(k => window.__sb._storyStep(k), FROM);
  const seen = {};
  for (let i = 0; i < SECS * 30; i++) {
    const r = await p.evaluate(() => { window.__step(1/30); const S = window.__sb._state, out = [];
      const draw = id => id === 'sun' ? byId.sun.radius * 0.5 : id === 'sun2' ? byId.sun.radius * 0.5 * 0.95 * (S.sun2K || 1) : byId[id] ? byId[id].radius * (byId[id].sbScale || 1) : 0;
      const pos = b => b.id === 'sun2' ? S.sun2.position.clone() : b.id === 'sun' ? byId.sun.world.clone() : byId[b.id] ? byId[b.id].world.clone() : null;
      const B = S.bodies.filter(b => b.alive);
      for (let a = 0; a < B.length; a++) for (let c = a + 1; c < B.length; c++) {
        const pa = pos(B[a]), pc = pos(B[c]); if (!pa || !pc) continue;
        const d = pa.distanceTo(pc), rr = draw(B[a].id) + draw(B[c].id);
        if (d < rr) out.push([B[a].id, B[c].id, +d.toFixed(2), +rr.toFixed(2), +(B[a].p.distanceTo(B[c].p)).toFixed(4)]);
      }
      return { day: +S.days.toFixed(1), st: window.__sb._story.i, out }; });
    for (const o of r.out) { const k = o[0] + '-' + o[1]; if (!seen[k] || r.day - seen[k] > 30) console.log('day', r.day, 'step', r.st, 'OVERLAP', o[0], o[1], 'scene', o[2], 'drawn r', o[3], 'real AU', o[4]); seen[k] = r.day; }
  }
  await br.close(); srv.close();
})();
