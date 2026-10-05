// Screenshots of the site along a fixed route (overview, several bodies, the catalogue), on a computer and a phone,
// with a virtual clock and fixed random numbers — so two versions of the site can be compared picture by picture.
//
//   node snap.js <out dir> [three.js package dir]
//
// Needs Playwright (global) and three@0.147.0 unpacked locally (npm pack three@0.147.0), since the CDN may be blocked.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');

const SITE = path.resolve(__dirname, '..'), OUT = path.resolve(process.argv[2] || 'snaps');
const THREE_DIR = path.resolve(process.argv[3] || path.join(__dirname, '../../videos/tools/node_modules/three'));
const CLOCK = path.resolve(__dirname, '../../videos/tools/clock.js');
const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };

const serve = () => new Promise(res => {
  const srv = http.createServer((req, rsp) => {
    let u = decodeURIComponent(req.url.split('?')[0]);
    if (u === '/') u = '/index.html';
    const file = path.join(SITE, u);
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
    rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(rsp);
  }).listen(0, '127.0.0.1', () => res(srv));
});

const ROUTE = [['Сонце'], ['Земля'], ['Марс'], ['Юпітер'], ['Сатурн'], ['Титан', true], ['Іо', true], ['67P'], ['Нептун']];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const srv = await serve(), url = `http://127.0.0.1:${srv.address().port}/`;
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const errors = [];
  for (const [dev, opts] of [['desk', { viewport: { width: 1280, height: 800 } }], ['phone', { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }]]) {
    const p = await br.newPage(opts);
    p.on('pageerror', e => errors.push(`${dev}: ${e.message}`));
    p.on('console', m => { if (m.type() === 'error') errors.push(`${dev} console: ${m.text().slice(0, 200)}`); });
    await p.route('**/cdn.jsdelivr.net/npm/three@0.147.0/**', r => r.fulfill({ path: path.join(THREE_DIR, r.request().url().split('three@0.147.0/')[1]), contentType: 'application/javascript' }));
    await p.route('**/fonts.g*/**', r => r.abort());
    await p.addInitScript({ path: CLOCK });
    await p.goto(url, { waitUntil: 'domcontentloaded' });
    // Run the virtual clock; real pauses let textures arrive.
    const run = async (secs, realMs = 1500) => {
      const n = Math.round(secs * 30);
      for (let i = 0; i < n; i++) await p.evaluate(() => window.__step(1 / 30));
      await p.waitForLoadState('networkidle').catch(() => {});
      await p.waitForTimeout(realMs);
      await p.evaluate(() => window.__step(1 / 30));
    };
    for (let i = 0; i < 3000; i++) {
      if (await p.evaluate(() => { window.__step(1 / 30); return document.getElementById('loader').classList.contains('done'); })) break;
      await p.waitForTimeout(20);
    }
    await run(5, 3000);
    const snap = async name => { await p.screenshot({ path: path.join(OUT, `${dev}_${name}.png`) }); };
    await snap('00_overview');
    if (await p.isVisible('#welcomeOk')) await p.click('#welcomeOk');
    await run(1);
    let k = 1;
    for (const [label, viaCatalog] of ROUTE) {
      if (viaCatalog) {
        await p.click('#allBtn');
        if (dev === 'phone') await p.click('.cat-tabs button[data-tab="moons"]');
        await p.click(`#catalog .chip:text-is("${label}")`);
      } else {
        await p.click(`#chips .chip:text-is("${label}")`);
      }
      await run(3, 2500);
      await snap(String(k++).padStart(2, '0') + '_' + label);
    }
    await p.click('#more');
    await run(0.5, 300);
    await snap(String(k++).padStart(2, '0') + '_info');
    await p.close();
  }
  await br.close(); srv.close();
  fs.writeFileSync(path.join(OUT, 'errors.txt'), errors.join('\n'));
  console.log(errors.length ? errors.join('\n') : 'no page errors');
})();
