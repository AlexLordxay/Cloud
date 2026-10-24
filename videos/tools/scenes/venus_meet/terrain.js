// 3D flights over real Venus relief for "Знайомся: Венера" (data from terrain_data.py): a mesh from the Magellan
// heights, coloured from the Magellan radar mosaic, lit with a normal map, bent to the planet's curvature, under the
// thick sulphuric-acid overcast: no Sun to be seen, a dim orange-yellow sky, light coming soft from above, the distance
// drowning in hot haze. (Same machinery as mars_meet/terrain.js.)
//
//   node scenes/venus_meet/terrain.js <shot> video        -> work/venus_meet/shot_<shot>/f_00000.jpg …
//   node scenes/venus_meet/terrain.js <shot> stills 0,2,4 -> work/venus_meet/shot_<shot>_<t>.jpg
//
// Shots are in shots.js: the site, the length, and camera keyframes (km east, real km of altitude, km south of the patch
// centre).
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'venus_meet');
const SHOTS = require('./shots');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const shot = SHOTS[name];
if (!shot) { console.log('shots:', Object.keys(SHOTS).join(', ')); process.exit(1); }
const W = 720, H = 1280, FPS = 30, EX = shot.ex || 2.5;

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script><script>

const SKY = \`
  uniform vec3 sun; uniform vec3 haze; uniform float dusk;
  vec3 skyCol(vec3 d, float g) {
    float e = clamp(d.y, -0.2, 1.0);
    // the overcast: hot yellow haze at the horizon, a heavier orange-brown cloud deck overhead, a soft brighter patch
    // where the hidden Sun is (no disc); at dusk everything sinks to a dull red-brown
    // the cloud deck overhead: darker, with slow streaks of the super-rotating clouds
    float st = 0.5 + 0.25 * sin(d.x * 9.0 / max(e, 0.08) + sin(d.z * 5.0 / max(e, 0.08)) * 1.7) + 0.15 * sin(d.z * 23.0 / max(e, 0.08));
    vec3 deck = mix(vec3(0.40, 0.24, 0.10), vec3(0.58, 0.36, 0.15), st);
    vec3 day = mix(haze * 1.05, deck, smoothstep(0.0, 0.45, e));
    float a = acos(clamp(dot(d, sun), -1.0, 1.0));
    day += vec3(0.35, 0.26, 0.12) * exp(-a / 0.5) * smoothstep(-0.05, 0.3, e) * g;
    vec3 dk = day * vec3(0.38, 0.26, 0.18);
    return mix(day, dk, dusk);
  }\`;
const EX = ${shot.ex || 2.5};                          // vertical exaggeration (stated in the notes)
async function setup() {
  const meta = await (await fetch('/data/meta.json')).json();
  const hb = new Float32Array(await (await fetch('/data/height.bin')).arrayBuffer());
  const N = meta.n, S = ${shot.mesh || 1280}, step = (N - 1) / (S - 1);
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
  const [col, nrm] = await Promise.all([load('/data/colour.jpg'), load('/data/normal.png')]);
  const sun = new THREE.Vector3(...${JSON.stringify(shot.sun || [-0.75, 0.42, -0.35])}).normalize();
  const DUSK = ${shot.dusk || 0};
  const HAZE = new THREE.Color(${JSON.stringify(shot.haze || '#e0b36a')});
  const mat = new THREE.ShaderMaterial({
    uniforms: { col: { value: col }, nrm: { value: nrm }, sun: { value: sun }, haze: { value: HAZE }, ex: { value: EX }, dusk: { value: DUSK },
      fogK: { value: ${shot.fog || 1 / 800} } },
    vertexShader: 'varying vec2 vUv; varying vec3 vW; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D col; uniform sampler2D nrm; uniform float ex; uniform float fogK; const float SHB = ${(shot.shadowBias || 0).toFixed(3)};\` + SKY + \`
      varying vec2 vUv; varying vec3 vW;
      void main() {
        vec3 c = pow(texture2D(col, vUv).rgb, vec3(2.2));
        vec3 t = texture2D(nrm, vUv).rgb * 2.0 - 1.0;                     // x east, y north, z up
        vec3 n = normalize(vec3(t.x * ex, t.z, -t.y * ex));
        float d = max(dot(n, sun), 0.0);
        // soft terminator on slopes facing away; at sunset (grazing light) a bias stands in for the shadows that
        // hills cast on each other, so the land toward the Sun goes dark and stands out against the glow
        float sh = smoothstep(-0.05 + SHB, 0.25 + SHB, dot(n, sun));
        // under the clouds the light is mostly diffuse: a strong sky term from above, a weak direct one for the relief
        float sky = 0.55 + 0.45 * n.y;
        vec3 amb = vec3(1.0, 0.78, 0.48) * mix(0.36, 0.16, dusk) * sky;
        vec3 lit = c * (vec3(1.0, 0.86, 0.62) * mix(1.9, 0.6, dusk) * d * sh + amb);
        float dist = length(vW - cameraPosition);
        float f = 1.0 - exp(-dist * fogK);
        vec2 e2 = min(vUv, 1.0 - vUv);
        float edge = 1.0 - smoothstep(0.0, 0.14, min(e2.x, e2.y));          // the patch's edges melt into the haze
        f = max(f * 0.8, edge);
        lit = mix(lit, pow(skyCol(normalize(normalize(vW - cameraPosition) * vec3(1.0, 0.0, 1.0) + vec3(0.0, 0.02, 0.0)), 0.3), vec3(2.2)) * 0.95, f);
        gl_FragColor = vec4(pow(lit, vec3(1.0 / 2.2)), 1.0);
      }\`,
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(geo, mat));
  // the sky: butterscotch near the horizon, darker and browner overhead
  const sky = new THREE.Mesh(new THREE.SphereGeometry(5000, 32, 16), new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false,
    uniforms: { haze: { value: HAZE }, sun: { value: sun }, dusk: { value: DUSK } },
    vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: SKY + \`varying vec3 vD; void main() {
      vec3 d = normalize(vD); vec3 c = skyCol(d, 1.0);
      float a = acos(clamp(dot(d, sun), -1.0, 1.0));
      gl_FragColor = vec4(c, 1.0); }\` }));
  scene.add(sky);
  const camera = new THREE.PerspectiveCamera(${shot.fov || 50}, ${W} / ${H}, 0.05, 20000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  window.__render = (p, l, sv) => { if (sv) sun.set(...sv).normalize(); camera.position.set(...p); camera.lookAt(...l); sky.position.copy(camera.position); renderer.render(scene, camera); return renderer.domElement.toDataURL('image/jpeg', 0.93); };
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
  // keyframes give the real altitude in km; the scene's heights are exaggerated and bent to the planet's curvature
  const place = ([x, a, z]) => [x, a * EX - (x * x + z * z) / (2 * 6051.8), z];
  return [place(f('pos')), place(f('look'))];
}

(async () => {
  const data = path.join(WORK, shot.site);
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = req.url.split('?')[0];
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js') : u.startsWith('/data/') ? path.join(data, u.slice(6)) : null;
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
    // shot.sunPath: [[azimuth, elevation] at the start, … at the end], degrees (azimuth from north through east)
    let sv = null;
    if (shot.sunPath) {
      const k = t / shot.dur, [[a0, e0], [a1, e1]] = shot.sunPath, az = (a0 + (a1 - a0) * k) * Math.PI / 180, el = (e0 + (e1 - e0) * k) * Math.PI / 180;
      sv = [Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)];
    }
    const url = await p.evaluate(([a, b, c]) => window.__render(a, b, c), [pos, look, sv]);
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
