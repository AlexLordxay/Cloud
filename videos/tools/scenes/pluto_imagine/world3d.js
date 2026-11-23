// The continuous flight of «А ти уявляєш Плутон так?»: one three.js scene in km, Pluto at the origin (x toward lon 0,
// y north, z toward lon −90°), so the camera goes from space down to the mountains with no cut:
//   * the globe (R 1188.3 km) with the New Horizons colour map (globe_tex.py), hidden under the 'heart' patch;
//   * the relief patches (patches.py), every vertex placed on the sphere: 'heart' (Sputnik Planitia, 1400 km square)
//     hidden under 'tenzing' (Tenzing Montes, 220 km); world normals and baked shadows for the shared Sun;
//   * the haze: a shell to 260 km whose glow follows the path a ray grazes through it — the thin blue ring round the
//     limb from space, the band along the horizon from the ground, brighter toward the Sun;
//   * the Sun: a dazzling point (0.015° from 34 AU), a little glare;
//   * Ukraine's outline (with Crimea) laid on the heart at true size, the Moon beside Pluto at true size, faint stars.
// Camera path and events: path.js.
//   node scenes/pluto_imagine/world3d.js stills 0,5,12      -> work/pluto_imagine/still_<t>.jpg
//   node scenes/pluto_imagine/world3d.js video [from to]    -> work/pluto_imagine/w3d/f_00000.jpg …
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'pluto_imagine');
const TEX = path.resolve(TOOLS, '../../planetarium/textures');
const PATH = require('./path');
const [mode = 'stills', list = '0', upto] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30;
const R = 1188.3, EX = 1.3;
const metaH = JSON.parse(fs.readFileSync(path.join(WORK, 'heart', 'meta.json')));
const metaT = JSON.parse(fs.readFileSync(path.join(WORK, 'tenzing', 'meta.json')));

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script><script>
const D = Math.PI / 180, R = ${R}, EX = ${EX};
const P = (lat, lon) => new THREE.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
const SUN = P(${metaH.sun[0]}, ${metaH.sun[1]});
// inverse azimuthal equidistant round (lat0, lon0): metres east/north -> unit vector
function aeqd(lat0, lon0, x, y) {
  const rho = Math.hypot(x, y), c = rho / (R * 1000), p0 = lat0 * D, l0 = lon0 * D;
  if (rho < 1e-6) return P(lat0, lon0);
  const lat = Math.asin(Math.cos(c) * Math.sin(p0) + y * Math.sin(c) * Math.cos(p0) / rho);
  const lon = l0 + Math.atan2(x * Math.sin(c), rho * Math.cos(p0) * Math.cos(c) - y * Math.sin(p0) * Math.sin(c));
  return new THREE.Vector3(Math.cos(lat) * Math.cos(lon), Math.sin(lat), -Math.cos(lat) * Math.sin(lon));
}
// GLSL: shared lighting and the patch-footprint test (x, y in km east/north of the patch centre)
const GL_COMMON = \`
uniform vec3 sun; uniform float expo, atmo, uaK; uniform sampler2D ov;
vec3 overlay(vec3 col, vec3 u) {
  float lat = asin(clamp(u.y, -1.0, 1.0)), lon = atan(-u.z, u.x);
  vec4 o = texture2D(ov, vec2(fract(lon / 6.2831853), 0.5 + lat / 3.14159265));
  return mix(col, o.rgb * (0.45 + 0.8 * smoothstep(-0.1, 0.3, dot(u, sun))), o.a * uaK);
}
vec3 shadeIt(vec3 c, vec3 n, vec3 vW, float s) {
  float mu0 = max(dot(n, sun), 0.0);
  vec3 v = normalize(cameraPosition - vW);
  float mu = max(dot(n, v), 0.05);
  float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.4);
  vec3 col = c * (vec3(1.0, 0.98, 0.95) * 2.3 * expo * lit * s + vec3(0.010, 0.016, 0.03) * expo);
  // aerial perspective inside the haze (only when the camera is low)
  float dist = length(cameraPosition - vW);
  col = mix(col, vec3(0.10, 0.20, 0.42) * expo * max(dot(normalize(vW), sun) + 0.25, 0.0), (1.0 - exp(-dist / 700.0)) * 0.55 * atmo);
  return col;
}
float hash3(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash3(i), hash3(i + vec3(1,0,0)), f.x), mix(hash3(i + vec3(0,1,0)), hash3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash3(i + vec3(0,0,1)), hash3(i + vec3(1,0,1)), f.x), mix(hash3(i + vec3(0,1,1)), hash3(i + vec3(1,1,1)), f.x), f.y), f.z);
}
// rock-scale roughness: bends the normal and speckles the albedo near the camera (it fades out by ~40 km)
vec3 micro(vec3 n, vec3 vW, inout vec3 c) {
  float dist = length(cameraPosition - vW);
  float k = 1.0 - smoothstep(6.0, 40.0, dist);
  if (k <= 0.0) return n;
  vec3 p = vW * 2.2, e = vec3(0.07, 0.0, 0.0);
  float a = vnoise(p) * 0.6 + vnoise(p * 2.7) * 0.4;
  vec3 g = vec3(vnoise(p + e.xyy) - vnoise(p - e.xyy), vnoise(p + e.yxy) - vnoise(p - e.yxy), vnoise(p + e.yyx) - vnoise(p - e.yyx)) / 0.14;
  c *= 1.0 + (a - 0.5) * 0.35 * k;
  return normalize(n - (g - n * dot(g, n)) * 0.22 * k);
}
vec2 fp(vec3 u, float lat0, float lon0) {
  float p0 = radians(lat0), l0 = radians(lon0);
  float lat = asin(clamp(u.y, -1.0, 1.0)), lon = atan(-u.z, u.x);
  float dl = lon - l0; dl = mod(dl + 3.14159265, 6.2831853) - 3.14159265;
  float cc = acos(clamp(sin(p0) * sin(lat) + cos(p0) * cos(lat) * cos(dl), -1.0, 1.0));
  float k = cc > 1e-6 ? cc / sin(cc) : 1.0;
  return ${R} * k * vec2(cos(lat) * sin(dl), cos(p0) * sin(lat) - sin(p0) * cos(lat) * cos(dl));
}\`;
async function setup() {
  const load = f => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }, undefined, () => r(null)));
  const [gmap, hc, hn, hs, tc, tn, ts, moonMap, ovMap] = await Promise.all(['/w/globe.jpg', '/w/heart/colour.jpg', '/w/heart/normal.png', '/w/heart/shadow.png',
    '/w/tenzing/colour.jpg', '/w/tenzing/normal.png', '/w/tenzing/shadow.png', '/tex/moon.jpg', '/w/overlay.png'].map(load));
  gmap.wrapS = THREE.RepeatWrapping;
  const common = { sun: { value: SUN }, expo: { value: 1 }, atmo: { value: 0 }, uaK: { value: 0 }, ov: { value: ovMap } };
  const scene = new THREE.Scene();
  // the globe
  const globeMat = new THREE.ShaderMaterial({ uniforms: Object.assign({ map: { value: gmap } }, common),
    vertexShader: 'varying vec3 vN; varying vec3 vW; void main() { vN = normalize(position); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: GL_COMMON + \`uniform sampler2D map; varying vec3 vN; varying vec3 vW;
      void main() {
        vec3 n = normalize(vN);
        vec2 q = fp(n, ${metaH.lat.toFixed(3)}, ${metaH.lon.toFixed(3)});
        if (abs(q.x) < ${(metaH.half - 1).toFixed(3)} && abs(q.y) < ${(metaH.half - 1).toFixed(3)}) discard;
        float lat = asin(clamp(n.y, -1.0, 1.0)), lon = atan(-n.z, n.x);
        float uA = lon / 6.2831853, uB = fract(uA + 0.5) - 0.5;
        float u = fwidth(uA) <= fwidth(uB) + 1e-6 ? uA : uB;
        vec3 c = pow(texture2D(map, vec2(u, 0.5 + lat / 3.14159265)).rgb, vec3(2.2));
        gl_FragColor = vec4(pow(overlay(shadeIt(c, n, vW, smoothstep(-0.02, 0.05, dot(n, sun))), n), vec3(1.0 / 2.2)), 1.0);
      }\` });
  scene.add(new THREE.Mesh(new THREE.SphereGeometry(R, 512, 256), globeMat));
  // a relief patch on the sphere
  async function patch(name, meta, cMap, nMap, sMap, S, hole) {
    const hb = new Float32Array(await (await fetch('/w/' + name + '/height.bin')).arrayBuffer());
    const N = meta.n, st = (N - 1) / (S - 1), half = meta.half * 1000;
    const pos = new Float32Array(S * S * 3), uv = new Float32Array(S * S * 2);
    for (let j = 0; j < S; j++) for (let i = 0; i < S; i++) {
      const gi = Math.round(i * st), gj = Math.round(j * st), k = j * S + i;
      const x = -half + 2 * half * gi / (N - 1), y = half - 2 * half * gj / (N - 1);
      const u = aeqd(meta.lat, meta.lon, x, y), r = R + hb[gj * N + gi] / 1000 * EX;
      pos[k * 3] = u.x * r; pos[k * 3 + 1] = u.y * r; pos[k * 3 + 2] = u.z * r;
      uv[k * 2] = gi / (N - 1); uv[k * 2 + 1] = 1 - gj / (N - 1);
    }
    const idx = new Uint32Array((S - 1) * (S - 1) * 6); let n = 0;
    for (let j = 0; j < S - 1; j++) for (let i = 0; i < S - 1; i++) { const a = j * S + i; idx.set([a, a + S, a + 1, a + 1, a + S, a + S + 1], n); n += 6; }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); g.setIndex(new THREE.BufferAttribute(idx, 1));
    const holeTest = hole ? \`if (useHole > 0.5) { vec2 q = fp(normalize(vW), \${hole.lat}, \${hole.lon}); if (abs(q.x) < \${hole.half} && abs(q.y) < \${hole.half}) discard; }\` : '';
    const m = new THREE.ShaderMaterial({ uniforms: Object.assign({ cm: { value: cMap }, nm: { value: nMap }, sm: { value: sMap }, useHole: { value: 1 } }, common),
      vertexShader: 'varying vec2 vUv; varying vec3 vW; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: GL_COMMON + \`uniform sampler2D cm, nm, sm; uniform float useHole; varying vec2 vUv; varying vec3 vW;
        void main() {
          \${holeTest}
          vec3 c = pow(texture2D(cm, vUv).rgb, vec3(2.2));
          vec3 n = normalize(texture2D(nm, vUv).rgb * 2.0 - 1.0);
          n = micro(n, vW, c);
          float s = texture2D(sm, vUv).r * smoothstep(-0.02, 0.05, dot(normalize(vW), sun));
          s *= smoothstep(-0.01, 0.03, dot(n, sun));
          gl_FragColor = vec4(pow(overlay(shadeIt(c, n, vW, s), normalize(vW)), vec3(1.0 / 2.2)), 1.0);
        }\` });
    const mesh = new THREE.Mesh(g, m); scene.add(mesh); return mesh;
  }
  const holeT = { lat: '${metaT.lat.toFixed(3)}', lon: '${metaT.lon.toFixed(3)}', half: '${(metaT.half - 0.5).toFixed(3)}' };
  // levels of detail: the close-up and the fine heart only when the camera is near them
  const heartHi = await patch('heart', ${JSON.stringify(metaH)}, hc, hn, hs, 1536, holeT);
  const heartLo = await patch('heart', ${JSON.stringify(metaH)}, hc, hn, hs, 384, holeT);
  const tenz = await patch('tenzing', ${JSON.stringify(metaT)}, tc, tn, ts, 2048, null);
  const tenC = P(${metaT.lat}, ${metaT.lon}).multiplyScalar(R), heartC = P(${metaH.lat}, ${metaH.lon}).multiplyScalar(R);
  // haze shell
  const hazeMat = new THREE.ShaderMaterial({ side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { sun: { value: SUN }, hz: { value: 1 }, sunK: { value: 1 } },
    vertexShader: 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform vec3 sun; uniform float hz, sunK; varying vec3 vW;
      void main() {
        vec3 c0 = cameraPosition, d = normalize(vW - c0);
        float tca = -dot(c0, d);                                   // closest approach along the ray
        float rc = length(c0), Hs = 10.0;
        float hc = rc - ${R};
        // the haze column the ray crosses (Chapman-style): grazing through its lowest point, or rising out of it
        float cm = 0.0;
        if (tca > 0.0) {
          float hmin = length(c0 + d * tca) - ${R};
          cm = exp(-max(hmin, 0.0) / Hs) * sqrt(6.2831853 * ${R} * Hs);
          if (hc < 260.0) cm *= 0.5 + 0.5 * smoothstep(0.0, 1.0, tca / sqrt(2.0 * ${R} * max(hc, 0.5)));
        } else {
          float cz = max(dot(d, c0 / rc), 0.04);
          cm = exp(-max(hc, 0.0) / Hs) * Hs / cz;
          cm = min(cm, exp(-max(hc, 0.0) / Hs) * sqrt(6.2831853 * ${R} * Hs) * 0.5);
        }
        float glow = 1.0 - exp(-cm / 650.0);
        float fw = 0.55 + 2.2 * pow(max(dot(d, sun), 0.0), 24.0);                   // forward scattering
        float day = smoothstep(-0.3, 0.25, dot(normalize(c0 + d * max(tca, 0.0)), sun));
        vec3 col3 = vec3(0.20, 0.42, 0.95) * glow * fw * day * hz;
        vec3 col = col3;
        float a = acos(clamp(dot(d, sun), -1.0, 1.0));
        col += vec3(1.0, 0.98, 0.94) * (exp(-pow(a / 0.0011, 2.0)) * 30.0 + exp(-a / 0.005) * 1.0 + exp(-a / 0.04) * 0.05) * sunK;
        gl_FragColor = vec4(col, 1.0);
      }\` });
  const haze = new THREE.Mesh(new THREE.SphereGeometry(R + 260, 256, 128), hazeMat); scene.add(haze);
  // the Moon at true size (R 1737.4 km), lit by the same Sun
  const moonMat = new THREE.ShaderMaterial({ transparent: true, uniforms: Object.assign({ map: { value: moonMap }, op: { value: 0 } }, common),
    vertexShader: 'varying vec3 vN; varying vec3 vW; void main() { vN = normalize(position); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: GL_COMMON + \`uniform sampler2D map; uniform float op; varying vec3 vN; varying vec3 vW;
      void main() {
        vec3 n = normalize(vN); float lat = asin(n.y), lon = atan(-n.z, n.x);
        vec3 c = pow(texture2D(map, vec2(fract(0.5 + (lon - radians(205.0)) / 6.2831853), 0.5 + lat / 3.14159265)).rgb, vec3(2.2)) * 0.9;   // its near side toward us
        gl_FragColor = vec4(pow(shadeIt(c, n, vW, smoothstep(-0.02, 0.05, dot(n, sun))), vec3(1.0 / 2.2)), op);
      }\` });
  const moon = new THREE.Mesh(new THREE.SphereGeometry(1737.4, 256, 128), moonMat); scene.add(moon);
  // stars
  const sg = new THREE.BufferGeometry(), sp = [], sc = [];
  let seed = 5; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 3500; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.12 + 0.55 * Math.pow(rnd(), 3);
    sp.push(r * Math.cos(a) * 5e5, u * 5e5, r * Math.sin(a) * 5e5); sc.push(b, b, b * 1.06);
  }
  sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.Float32BufferAttribute(sc, 3));
  const stars = new THREE.Points(sg, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);
  const camera = new THREE.PerspectiveCamera(50, ${W} / ${H}, 0.02, 2e6);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  window.__render = s => {
    camera.position.set(...s.pos); camera.up.set(...s.up); camera.lookAt(...s.look);
    if (Math.abs(camera.fov - s.fov) > 1e-4) { camera.fov = s.fov; camera.updateProjectionMatrix(); }
    stars.position.copy(camera.position);
    const alt = camera.position.length() - R;
    tenz.visible = camera.position.distanceTo(tenC) < 900;
    heartHi.visible = alt < 2500 && camera.position.distanceTo(heartC) < 3200; heartLo.visible = !heartHi.visible;
    heartHi.material.uniforms.useHole.value = heartLo.material.uniforms.useHole.value = tenz.visible ? 1 : 0;
    common.expo.value = s.expo; common.atmo.value = s.atmo;
    hazeMat.uniforms.hz.value = s.haze;
    moon.position.set(...s.moonPos); moonMat.uniforms.op.value = s.moon; moon.visible = s.moon > 0.002;
    common.uaK.value = s.ua;
    renderer.render(scene, camera); return renderer.domElement.toDataURL('image/jpeg', 0.94);
  };
  window.ready = 1;
}
setup().catch(e => console.error('setup failed', e.message));
</script></body></html>`;

(async () => {
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u.startsWith('/w/') ? path.join(WORK, u.slice(3)) : u.startsWith('/tex/') ? path.join(TEX, u.slice(5)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--js-flags=--max-old-space-size=6000'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error') console.log(m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 1000 });
  const save = async (t, file) => {
    const url = await p.evaluate(s => window.__render(s), PATH.state(t));
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) { const t0 = Date.now(); await save(t, path.join(WORK, `still_${t}.jpg`)); console.log('still', t, ((Date.now() - t0) / 1000).toFixed(1), 's'); }
  } else {
    const dir = path.join(WORK, 'w3d'); fs.mkdirSync(dir, { recursive: true });
    const n0 = Number(list) || 0, n1 = upto ? Number(upto) : Math.round(PATH.DURATION * FPS);
    for (let i = n0; i < n1; i++) {
      const f = path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`);
      if (fs.existsSync(f)) continue;
      await save(i / FPS, f); if (i % 30 === 0) console.log('frame', i, '/', n1);
    }
  }
  await br.close(); srv.close();
})();
