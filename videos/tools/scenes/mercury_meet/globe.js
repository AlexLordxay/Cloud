// The whole planet for "Знайомся: Меркурій": a sphere with the MESSENGER mosaic (the site's mercury.jpg), lit by the
// Sun, in black space with faint stars. On top, per shot (globe_shots in shots.js):
//   * overlay (work/mercury_meet/overlay.png from overlay.py): Ukraine's outline laid on the Caloris basin at true size,
//     and the basin's rim — faded in and out with `over`;
//   * the Caloris shock: a glowing ring running from the basin across the globe and closing in on the opposite side
//     (`shock`: 0 → 1 as it travels 0° → 180°), and the spot there flashing;
//   * BepiColombo: a bright point on its capture orbit, with its track (`bepi`: where along it, 0 → 1).
// Camera keys: { t, lat, lon (of the point under the camera), dist (in planet radii), lookLat?, lookLon?, fov? }.
//
//   node scenes/mercury_meet/globe.js <shot> video        -> work/mercury_meet/globe_<shot>/f_00000.jpg …
//   node scenes/mercury_meet/globe.js <shot> stills 0,2,4 -> work/mercury_meet/globe_<shot>_<t>.jpg
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'mercury_meet');
const TEX = path.resolve(TOOLS, '../../planetarium/textures');
const { globe_shots: SHOTS } = require('./shots');
const [name, mode = 'stills', list = '0'] = process.argv.slice(2);
const shot = SHOTS[name];
if (!shot) { console.log('globe shots:', Object.keys(SHOTS).join(', ')); process.exit(1); }
const W = 720, H = 1280, FPS = 30;

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script><script>
const D = Math.PI / 180;
// (lat, lon) on the unit sphere: x toward lon 0, y north, z toward lon -90 (so lon grows anticlockwise seen from north)
const P = (lat, lon) => new THREE.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
async function setup() {
  const load = f => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }, undefined, () => r(null)));
  const [map, over] = await Promise.all([load('/tex/mercury.jpg'), load('/data/overlay.png')]);
  const sunDir = P(...${JSON.stringify(shot.sun || [0, 120])});
  const U = { map: { value: map }, over: { value: over }, overK: { value: 0 }, sun: { value: sunDir }, shock: { value: -1 },
    cal: { value: P(31.5, 162.7) } };
  const planet = new THREE.Mesh(new THREE.SphereGeometry(1, 256, 128), new THREE.ShaderMaterial({ uniforms: U,
    vertexShader: 'varying vec3 vN; varying vec3 vW; void main() { vN = normalize(position); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D map, over; uniform float overK, shock; uniform vec3 sun, cal; varying vec3 vN; varying vec3 vW;
      void main() {
        vec3 n = normalize(vN);
        float lat = asin(clamp(n.y, -1.0, 1.0)), lon = atan(-n.z, n.x);
        vec2 uv = vec2((lon + 3.14159265) / 6.2831853, (lat + 1.5707963) / 3.14159265);
        vec3 c = pow(texture2D(map, uv).rgb, vec3(2.2)) * 0.85;
        float mu0 = dot(n, sun);
        vec3 v = normalize(cameraPosition - vW);
        float mu = max(dot(n, v), 0.05);
        float lit = mix(max(mu0, 0.0), 2.0 * max(mu0, 0.0) / (max(mu0, 0.0) + mu), 0.45);
        vec3 col = c * 2.6 * lit * smoothstep(-0.02, 0.06, mu0) + c * 0.004;
        vec4 o = texture2D(over, uv);
        col = mix(col, pow(o.rgb, vec3(2.2)) * (0.35 + 0.9 * smoothstep(-0.1, 0.3, mu0)), o.a * overK);
        // the Caloris shock: a ring at angular distance shock·π from the basin
        if (shock >= 0.0) {
          float d = acos(clamp(dot(n, cal), -1.0, 1.0)) / 3.14159265;
          float w = 0.012 + 0.02 * (1.0 - abs(shock * 2.0 - 1.0));
          float ring = exp(-pow((d - shock) / w, 2.0)) * (1.0 - 0.6 * shock);
          float focus = smoothstep(0.88, 1.0, shock) * exp(-pow((1.0 - d) / 0.035, 2.0)) * 2.5;
          col += vec3(1.0, 0.55, 0.18) * (ring + focus) * 0.9;
        }
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }\` }));
  const scene = new THREE.Scene(); scene.add(planet);
  const sg = new THREE.BufferGeometry(), sp = [], sc = [];
  let seed = 5; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 3000; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.15 + 0.6 * Math.pow(rnd(), 3);
    sp.push(r * Math.cos(a) * 900, u * 900, r * Math.sin(a) * 900); sc.push(b, b, b * 1.05);
  }
  sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.Float32BufferAttribute(sc, 3));
  const stars = new THREE.Points(sg, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);
  // BepiColombo: its capture orbit (an ellipse, periapsis ~1.3 R, apoapsis ~6 R, tilted near-polar) and the craft
  const BEPI = ${JSON.stringify(shot.bepiOrbit || null)};
  let bepiDot = null, bepiLine = null, bepiAt = null;
  if (BEPI) {
    const [rp, ra, inc, node] = BEPI, a = (rp + ra) / 2, e = (ra - rp) / (ra + rp);
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(inc * D, node * D, 0, 'YXZ'));
    bepiAt = k => {                                         // k: 0 → 1 along the incoming leg and one turn
      const nu = (-150 + 330 * k) * D, r = a * (1 - e * e) / (1 + e * Math.cos(nu));
      return new THREE.Vector3(r * Math.cos(nu), 0, r * Math.sin(nu)).applyQuaternion(q);
    };
    const pts = []; for (let i = 0; i <= 400; i++) pts.push(bepiAt(i / 400));
    bepiLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.0 }));
    scene.add(bepiLine);
    const cv = document.createElement('canvas'); cv.width = cv.height = 64;
    const gx = cv.getContext('2d'), gr = gx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.2, 'rgba(255,224,150,1)'); gr.addColorStop(0.5, 'rgba(255,200,110,0.3)'); gr.addColorStop(1, 'rgba(255,200,110,0)');
    gx.fillStyle = gr; gx.fillRect(0, 0, 64, 64);
    bepiDot = new THREE.Points(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3()]),
      new THREE.PointsMaterial({ size: 30, sizeAttenuation: false, map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false }));
    scene.add(bepiDot);
  }
  const camera = new THREE.PerspectiveCamera(${shot.fov || 30}, ${W} / ${H}, 0.01, 5000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  window.__render = s => {
    camera.position.copy(P(s.lat, s.lon).multiplyScalar(s.dist));
    camera.up.set(0, 1, 0);
    const look = s.lookLat !== undefined ? P(s.lookLat, s.lookLon).multiplyScalar(s.lookR || 0) : new THREE.Vector3();
    camera.lookAt(look);
    if (s.fov && Math.abs(camera.fov - s.fov) > 1e-4) { camera.fov = s.fov; camera.updateProjectionMatrix(); }
    stars.position.copy(camera.position);
    U.overK.value = s.over || 0; U.shock.value = s.shock === undefined ? -1 : s.shock;
    if (bepiDot) {
      const p = bepiAt(s.bepi || 0); bepiDot.geometry.attributes.position.setXYZ(0, p.x, p.y, p.z); bepiDot.geometry.attributes.position.needsUpdate = true;
      bepiLine.material.opacity = 0.45 * (s.bepiLine || 0); bepiDot.material.opacity = s.bepiShow === undefined ? 1 : s.bepiShow;
    }
    renderer.render(scene, camera); return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  window.ready = 1;
}
setup();
</script></body></html>`;

// the state at time t: every numeric key eased between keyframes (longitudes along the short way round)
function state(t) {
  const K = shot.keys; let i = 0; while (i < K.length - 2 && t > K[i + 1].t) i++;
  const a = K[i], b = K[Math.min(i + 1, K.length - 1)];
  let u = b.t > a.t ? Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t))) : 1;
  const ue = u * u * (3 - 2 * u), out = {};
  for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
    if (k === 't') continue;
    const x = a[k] === undefined ? b[k] : a[k], y = b[k] === undefined ? a[k] : b[k];
    const lin = shot.linear && shot.linear.includes(k);
    let d = y - x; if (k.toLowerCase().endsWith('lon')) d = ((d + 540) % 360) - 180;
    out[k] = x + d * (lin ? u : ue);
  }
  return out;
}

(async () => {
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = req.url.split('?')[0];
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u.startsWith('/data/') ? path.join(WORK, u.slice(6)) : u.startsWith('/tex/') ? path.join(TEX, u.slice(5)) : null;
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
    const url = await p.evaluate(s => window.__render(s), state(t));
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) await save(t, path.join(WORK, `globe_${name}_${t}.jpg`));
  } else {
    const dir = path.join(WORK, 'globe_' + name); fs.mkdirSync(dir, { recursive: true });
    const n = Math.round(shot.dur * FPS);
    for (let i = 0; i < n; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', n); }
  }
  await br.close(); srv.close();
})();
