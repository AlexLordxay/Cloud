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
const SHOTS = require('./shots');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const shot = SHOTS[name];
if (!shot) { console.log('shots:', Object.keys(SHOTS).join(', ')); process.exit(1); }
const W = 720, H = 1280, FPS = 30;
const meta = JSON.parse(fs.readFileSync(path.join(WORK, shot.site, 'meta.json')));
const EX = meta.ex, RKM = meta.R / 1000;

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script><script>
async function setup() {
  const meta = ${JSON.stringify(meta)};
  const hb = new Float32Array(await (await fetch('/data/height.bin')).arrayBuffer());
  const N = meta.n, S = ${shot.mesh || 1280}, step = (N - 1) / (S - 1), EX = meta.ex;
  const R = meta.R / 1000, dx = meta.dx / 1000, dy = meta.dy / 1000;
  const pos = new Float32Array(S * S * 3), uv = new Float32Array(S * S * 2);
  for (let j = 0; j < S; j++) for (let i = 0; i < S; i++) {
    const gi = Math.round(i * step), gj = Math.round(j * step), k = j * S + i;
    const x = (gi - (N - 1) / 2) * dx, z = (gj - (N - 1) / 2) * dy;          // j runs north → south
    const h = hb[gj * N + gi] / 1000 * EX;
    pos[k * 3] = x; pos[k * 3 + 1] = h - (x * x + z * z) / (2 * R); pos[k * 3 + 2] = z;
    uv[k * 2] = gi / (N - 1); uv[k * 2 + 1] = 1 - gj / (N - 1);
  }
  const idx = new Uint32Array((S - 1) * (S - 1) * 6); let n = 0;
  for (let j = 0; j < S - 1; j++) for (let i = 0; i < S - 1; i++) { const a = j * S + i; idx.set([a, a + S, a + 1, a + 1, a + S, a + S + 1], n); n += 6; }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  const load = f => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }));
  const [col, nrm, shd] = await Promise.all([load('/data/colour.jpg'), load('/data/normal.png'), load('/data/shadow.png')]);
  const sun = new THREE.Vector3(...meta.sun).normalize();
  const mat = new THREE.ShaderMaterial({
    uniforms: { col: { value: col }, nrm: { value: nrm }, shd: { value: shd }, sun: { value: sun }, ex: { value: EX }, es: { value: ${shot.earthshine || 1} } },
    vertexShader: 'varying vec2 vUv; varying vec3 vW; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D col; uniform sampler2D nrm; uniform sampler2D shd; uniform vec3 sun; uniform float ex; uniform float es;
      varying vec2 vUv; varying vec3 vW;
      void main() {
        vec3 c = pow(texture2D(col, vUv).rgb, vec3(2.2));
        vec3 t = texture2D(nrm, vUv).rgb * 2.0 - 1.0;                     // x east, y north, z up
        vec3 n = normalize(vec3(t.x * ex, t.z, -t.y * ex));
        // lunar soil throws light back toward the Sun (it looks flat and bright when lit head-on): a plain Lambert
        // mixed with Lommel-Seeliger, which does that
        float mu0 = max(dot(n, sun), 0.0);
        vec3 v = normalize(cameraPosition - vW);
        float mu = max(dot(n, v), 0.05);
        float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.35);
        float s = texture2D(shd, vUv).r;
        vec3 col = c * (vec3(1.0, 0.98, 0.95) * 2.3 * lit * s + vec3(0.010, 0.012, 0.016) * es);   // shadows: only earthshine
        vec2 e2 = min(vUv, 1.0 - vUv);
        col *= smoothstep(0.0, 0.18, min(e2.x, e2.y));                     // the patch's edges fade into the dark
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }\`,
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(geo, mat));
  // faint stars (a camera exposed for the sunlit ground would hardly show them)
  const sg = new THREE.BufferGeometry(), sp = [], sc = [];
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 2500; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.15 + 0.5 * Math.pow(rnd(), 3);
    sp.push(r * Math.cos(a) * 9000, u * 9000, r * Math.sin(a) * 9000); sc.push(b, b, b * 1.05);
  }
  sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.Float32BufferAttribute(sc, 3));
  const stars = new THREE.Points(sg, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);
  // the Earth, if the shot has it: [azimuth from north through east, elevation], 1.9° across as seen from the Moon,
  // lit by the same Sun (its phase is the Moon's turned inside out)
  let earth = null;
  const EARTH = ${JSON.stringify(shot.earth || null)};
  if (EARTH) {
    const tex = await load('/site/earth_day_2k.jpg');
    earth = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 32), new THREE.ShaderMaterial({
      uniforms: { tex: { value: tex }, sun: { value: sun } },
      vertexShader: 'varying vec2 vUv; varying vec3 vN; void main() { vUv = uv; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: \`uniform sampler2D tex; uniform vec3 sun; varying vec2 vUv; varying vec3 vN;
        void main() { vec3 c = pow(texture2D(tex, vUv).rgb, vec3(2.2));
          float d = dot(normalize(vN), sun);
          vec3 lit = c * 1.7 * smoothstep(-0.05, 0.25, d) + vec3(0.25, 0.45, 0.9) * 0.12 * smoothstep(-0.1, 0.3, d);
          gl_FragColor = vec4(pow(lit, vec3(1.0 / 2.2)), 1.0); }\` }));
    const a = EARTH[0] * Math.PI / 180, e = EARTH[1] * Math.PI / 180, D = 8000;
    earth.userData.dir = new THREE.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
    earth.scale.setScalar(D * Math.tan(0.95 * Math.PI / 180));
    earth.rotation.y = ${shot.earthSpin || 0};
    scene.add(earth);
  }
  // a marked place (Apollo 11): a bright dot on the ground and a thin line up from it
  const MARK = ${JSON.stringify(shot.marker || null)};
  if (MARK) {
    const gi = Math.round(MARK[0] / dx + (N - 1) / 2), gj = Math.round(MARK[1] / dy + (N - 1) / 2);
    const y = hb[gj * N + gi] / 1000 * EX - (MARK[0] * MARK[0] + MARK[1] * MARK[1]) / (2 * R);
    const pg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y + 0.02, MARK[1])]);
    scene.add(new THREE.Points(pg, new THREE.PointsMaterial({ size: 9, sizeAttenuation: false, color: 0xffd27a, depthTest: false })));
    const lg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y, MARK[1]), new THREE.Vector3(MARK[0], y + 2.5, MARK[1])]);
    scene.add(new THREE.Line(lg, new THREE.LineBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.8, depthTest: false })));
  }
  const camera = new THREE.PerspectiveCamera(${shot.fov || 50}, ${W} / ${H}, 0.05, 20000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  window.__render = (p, l) => {
    camera.position.set(...p); camera.lookAt(...l); stars.position.copy(camera.position);
    if (earth) earth.position.copy(camera.position).addScaledVector(earth.userData.dir, 8000);
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
  return [place(f('pos')), place(f('look'))];
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
    const [pos, look] = cam(t);
    const url = await p.evaluate(([a, b]) => window.__render(a, b), [pos, look]);
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
