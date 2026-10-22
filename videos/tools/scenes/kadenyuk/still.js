// A test still for the Kadenyuk video: the Space Shuttle (NASA 3D Resources, "Space Shuttle (D)") in orbit above the Earth
// (the site's textures). The Earth is drawn in km, the shuttle in metres with its own camera of the same orientation,
// so the 37 m orbiter and the 6371 km planet share one picture without depth trouble.
//
//   node scenes/kadenyuk/still.js [out.jpg]      (models in work/kadenyuk/model/)
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'kadenyuk');
const out = process.argv[2] || path.join(WORK, 'still.jpg');
const W = 720, H = 1280;

const page = `<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/GLTFLoader.js"></script><script src="/DRACOLoader.js"></script><script src="/scene/world.js"></script>
</body></html>`;

(async () => {
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u === '/GLTFLoader.js' ? path.join(TOOLS, 'node_modules/three/examples/js/loaders/GLTFLoader.js')
        : u === '/DRACOLoader.js' ? path.join(TOOLS, 'node_modules/three/examples/js/loaders/DRACOLoader.js')
        : u.startsWith('/draco/') ? path.join(TOOLS, 'node_modules/three/examples/js/libs/draco/gltf', u.slice(7))
        : u.startsWith('/work/') ? path.join(WORK, u.slice(6))
        : u.startsWith('/scene/') ? path.join(__dirname, u.slice(7))
        : u.startsWith('/model/') ? path.join(WORK, 'model', u.slice(7))
        : u.startsWith('/tex/') ? path.join(TOOLS, '../../planetarium/textures', u.slice(5)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      if (f.endsWith('.wasm')) rsp.writeHead(200, { 'Content-Type': 'application/wasm' });
      else if (f.endsWith('.js')) rsp.writeHead(200, { 'Content-Type': 'application/javascript; charset=utf-8' });
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => console.log(m.text().slice(0, 2000)));
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.WORLD_READY, null, { timeout: 180000 });
  const url = await p.evaluate(() => window.render());
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  console.log(out);
  await br.close(); srv.close();
})();
