// 3D flights over real Moon relief for "Знайомся: Місяць" (data from terrain_data.py): a mesh from the LOLA heights,
// coloured with the LROC brightness, lit with a normal map and the shadows baked for the site's Sun, bent to the
// Moon's curvature. No air: a black sky with faint stars, no haze, and the Earth where it really hangs.
//
//   node scenes/moon_meet/terrain.js <shot> video        -> work/moon_meet/shot_<shot>/f_00000.jpg …
//   node scenes/moon_meet/terrain.js <shot> stills 0,2,4 -> work/moon_meet/shot_<shot>_<t>.jpg
//
// Shots are in shots.js: the site, the length, and camera keyframes (km east, real km of altitude, km south of the patch
// centre). The Sun is the site's (terrain_data.py), so the shadows match it.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'moon_meet');
const SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const SHOTS = require('./shots'), { moonWorld } = require('./world');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const shot = SHOTS[name];
if (!shot) { console.log('shots:', Object.keys(SHOTS).join(', ')); process.exit(1); }
const W = 720, H = 1280, FPS = 30;
const meta = JSON.parse(fs.readFileSync(path.join(WORK, shot.site, 'meta.json')));
const EX = meta.ex, RKM = meta.R / 1000;

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script><script>
${moonWorld(shot, meta)}
async function setup() {
  const { scene, stars, earth, halo, earthFrame } = await buildMoon();
  const camera = new THREE.PerspectiveCamera(${shot.fov || 50}, ${W} / ${H}, 0.05, 20000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  window.__render = (p, l, fov) => {
    if (fov && Math.abs(camera.fov - fov) > 1e-4) { camera.fov = fov; camera.updateProjectionMatrix(); }
    camera.position.set(...p); camera.lookAt(...l); stars.position.copy(camera.position);
    if (earth) {
      earth.position.copy(camera.position).addScaledVector(earthFrame.dir, earthFrame.D); halo.position.copy(earth.position);
      earthFrame.U.C.value.copy(earth.position); earthFrame.U.R.value = earthFrame.R;
    }
    renderer.render(scene, camera); return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  window.ready = 1;
}
setup();
</script></body></html>`;

// camera at time t: Catmull-Rom through the keyframes, eased by the shot's own timing
function cam(t) {
  const K = shot.keys, last = K.length - 1;
  let i = 0; while (i < last - 1 && t > K[i + 1].t) i++;
  const k0 = K[Math.max(i - 1, 0)], k1 = K[i], k2 = K[Math.min(i + 1, last)], k3 = K[Math.min(i + 2, last)];
  let u = Math.min(1, Math.max(0, (t - k1.t) / Math.max(k2.t - k1.t, 1e-6)));
  if (shot.ease) u = u * u * (3 - 2 * u);
  const cr = (a, b, c, d) => 0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (3 * b - a - 3 * c + d) * u * u * u);
  const f = key => [0, 1, 2].map(j => cr(k0[key][j], k1[key][j], k2[key][j], k3[key][j]));
  // keyframes give the real altitude in km; the scene's heights are exaggerated and bent to the Moon's curvature
  const place = ([x, a, z]) => [x, a * EX - (x * x + z * z) / (2 * RKM), z];
  // a slow zoom (shot.fovTo), eased over the whole shot
  const z = Math.min(1, Math.max(0, t / shot.dur)), ze = z * z * (3 - 2 * z);
  const fov = shot.fovTo ? (shot.fov || 50) + (shot.fovTo - (shot.fov || 50)) * ze : (shot.fov || 50);
  return [place(f('pos')), place(f('look')), fov];
}

(async () => {
  const data = path.join(WORK, shot.site);
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = req.url.split('?')[0];
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u.startsWith('/data/') ? path.join(data, u.slice(6)) : u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error') console.log(m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 120000 });
  const save = async (t, file) => {
    const [pos, look, fov] = cam(t);
    const url = await p.evaluate(([a, b, c]) => window.__render(a, b, c), [pos, look, fov]);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) await save(t, path.join(WORK, `shot_${name}_${t}.jpg`));
  } else {
    const dir = path.join(WORK, 'shot_' + name); fs.mkdirSync(dir, { recursive: true });
    const n = Math.round(shot.dur * FPS);
    for (let i = 0; i < n; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', n); }
  }
  await br.close(); srv.close();
})();
