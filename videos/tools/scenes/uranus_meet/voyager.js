// «Знайомся: Уран» — Voyager 2 alone, on a transparent background, to lay over uranus.py's planet (three.js; the real
// layout and sizes: the 3.66 m dish, the ten-sided bus under it with its gold and black blankets, the boom with the
// three RTGs, the science boom with the scan platform, the 13 m magnetometer mast).
//
//   node scenes/uranus_meet/voyager.js <spec.json> <outdir> [n k]   -> <outdir>/v_<frame>.png (RGBA)
//
// spec.json: { W, H, frames: [{ f, cam: [px,py,pz, tx,ty,tz, ux,uy,uz] (metres, the craft at the origin), fov,
//   quat: [x,y,z,w] (the craft's attitude), sun: [x,y,z], fill: [x,y,z] (towards Uranus), fillC: [r,g,b], expo }] }
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..');
const [specF, outDir, nw = '1', kw = '0'] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specF));
const { W, H } = spec;

const page = `<!doctype html><html><body style="margin:0;background:transparent">
<script src="/three.min.js"></script>
<script>
(async () => {
  const T = THREE, W = ${W}, H = ${H};
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true, premultipliedAlpha: false });
  renderer.setSize(W, H); renderer.setClearColor(0x000000, 0);
  renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);
  const sc = new T.Scene(), cam = new T.PerspectiveCamera(40, W / H, 0.05, 2000);
  // reflections: black space with a soft cyan glow on one side (Uranus)
  const envU = { fill: { value: new T.Vector3(1, 0, 0) } };
  const esc = new T.Scene();
  esc.add(new T.Mesh(new T.SphereGeometry(10, 64, 32), new T.ShaderMaterial({ side: T.BackSide, uniforms: envU,
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform vec3 fill; varying vec3 vD; void main(){ float k = smoothstep(0.75, 0.95, dot(vD, fill)); gl_FragColor = vec4(vec3(0.004,0.005,0.008) + vec3(0.25,0.55,0.6) * k, 1.0); }' })));
  const craft = new T.Group(); sc.add(craft);
  const white = new T.MeshStandardMaterial({ color: 0xe8e6e0, roughness: 0.55, metalness: 0.05 });
  const dishIn = new T.MeshStandardMaterial({ color: 0xf2f0ea, roughness: 0.35, metalness: 0.0, side: T.DoubleSide });
  const gold = new T.MeshStandardMaterial({ color: 0xc9962e, roughness: 0.32, metalness: 0.85 });
  const black = new T.MeshStandardMaterial({ color: 0x141414, roughness: 0.7, metalness: 0.1 });
  const metal = new T.MeshStandardMaterial({ color: 0x9a9a9a, roughness: 0.4, metalness: 0.8 });
  const rtgM = new T.MeshStandardMaterial({ color: 0x2b2b2b, roughness: 0.6, metalness: 0.5 });
  const add = (g, m, p, r, parent = craft) => { const o = new T.Mesh(g, m); o.position.set(...p); if (r) o.rotation.set(...r); o.castShadow = o.receiveShadow = true; parent.add(o); return o; };
  // the high-gain antenna: a shallow paraboloid, 3.66 m across, facing +y (to the Earth)
  const prof = []; for (let i = 0; i <= 24; i++) { const r = 1.83 * i / 24; prof.push(new T.Vector2(r, 0.28 * (r / 1.83) ** 2)); }
  add(new T.LatheGeometry(prof, 96), dishIn, [0, 0.55, 0]);
  add(new T.TorusGeometry(1.83, 0.025, 8, 96), white, [0, 0.83, 0], [Math.PI / 2, 0, 0]);
  // the feed and its struts
  add(new T.CylinderGeometry(0.09, 0.12, 0.35, 16), white, [0, 1.35, 0]);
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + 0.4; const s = add(new T.CylinderGeometry(0.012, 0.012, 1.25, 6), metal, [Math.cos(a) * 0.55, 1.0, Math.sin(a) * 0.55]); s.lookAt(0, 1.6, 0); s.rotateX(Math.PI / 2); }
  // the bus: ten-sided, 1.78 m across, 0.47 m tall, under the dish; gold and black blankets
  add(new T.CylinderGeometry(0.89, 0.89, 0.47, 10), black, [0, 0.2, 0]);
  for (let k = 0; k < 10; k += 2) { const a = (k + 0.5) * Math.PI / 5; add(new T.BoxGeometry(0.5, 0.42, 0.02), gold, [Math.cos(a) * 0.86, 0.2, Math.sin(a) * 0.86], [0, -a + Math.PI / 2, 0]); }
  add(new T.CylinderGeometry(0.42, 0.55, 0.4, 16), gold, [0, -0.25, 0]);           // the propellant tank's blanket
  // the RTG boom (to -x): a truss and three cylinders with their fins
  add(new T.CylinderGeometry(0.03, 0.03, 2.4, 8), metal, [-1.9, 0.0, 0.2], [0, 0, Math.PI / 2]);
  for (let k = 0; k < 3; k++) {
    const x = -2.15 - k * 0.55;
    add(new T.CylinderGeometry(0.2, 0.2, 0.5, 12), rtgM, [x, -0.12, 0.2], [0, 0, Math.PI / 2]);
    for (let q = 0; q < 6; q++) { const a = q * Math.PI / 3; add(new T.BoxGeometry(0.46, 0.02, 0.14), rtgM, [x, -0.12 + Math.cos(a) * 0.26, 0.2 + Math.sin(a) * 0.26], [a, 0, 0]); }
  }
  // the science boom (to +x) and the scan platform with its cameras
  add(new T.CylinderGeometry(0.035, 0.035, 2.2, 8), metal, [1.95, 0.05, -0.1], [0, 0, Math.PI / 2]);
  const plat = new T.Group(); plat.position.set(3.1, 0.05, -0.1); craft.add(plat);
  add(new T.BoxGeometry(0.42, 0.42, 0.42), black, [0, 0, 0], null, plat);
  add(new T.CylinderGeometry(0.09, 0.09, 0.6, 16), white, [0.1, 0.32, 0.05], [0.4, 0, 0], plat);
  add(new T.CylinderGeometry(0.06, 0.06, 0.45, 16), white, [-0.12, 0.3, -0.05], [0.4, 0, 0], plat);
  add(new T.BoxGeometry(0.2, 0.25, 0.3), gold, [0, -0.3, 0.05], null, plat);
  // the magnetometer mast: a thin triangular truss, 13 m (to +z, up and back)
  const mast = new T.Group(); mast.position.set(-0.6, 0.1, -0.5); mast.rotation.set(-0.35, 0, 0.55); craft.add(mast);
  for (let k = 0; k < 3; k++) { const a = k * 2 * Math.PI / 3; add(new T.CylinderGeometry(0.008, 0.008, 13, 4), white, [Math.cos(a) * 0.1, 6.5, Math.sin(a) * 0.1], null, mast); }
  add(new T.BoxGeometry(0.15, 0.15, 0.15), white, [0, 13, 0], null, mast);
  // the two whip antennas (10 m, thin)
  for (const s of [-1, 1]) add(new T.CylinderGeometry(0.004, 0.004, 10, 3), metal, [s * 0.4, -0.4, 0.6], [Math.PI / 2 - 0.2, 0, s * 0.6]);

  const sunL = new T.DirectionalLight(0xffffff, 3.2); sunL.castShadow = true; sunL.shadow.mapSize.set(2048, 2048);
  Object.assign(sunL.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 0.1, far: 40 }); sc.add(sunL); sc.add(sunL.target);
  const fillL = new T.DirectionalLight(0x66c8d0, 0.6); sc.add(fillL); sc.add(fillL.target);
  sc.add(new T.AmbientLight(0x101418, 0.4));
  let envSet = null;
  window.__frame = (o) => {
    const fd = new T.Vector3(...o.fill).normalize();
    if (!envSet || envSet.distanceTo(fd) > 0.05) { envU.fill.value.copy(fd); const pm = new T.PMREMGenerator(renderer); sc.environment = pm.fromScene(esc, 0.02).texture; pm.dispose(); envSet = fd.clone(); }
    craft.quaternion.set(...o.quat);
    sunL.position.set(...o.sun).normalize().multiplyScalar(20); sunL.target.position.set(0, 0, 0);
    fillL.position.copy(fd).multiplyScalar(20); fillL.color.setRGB(...(o.fillC || [0.4, 0.78, 0.82])); fillL.intensity = o.fillK || 0.6;
    renderer.toneMappingExposure = o.expo || 1;
    cam.fov = o.fov; cam.aspect = W / H; cam.updateProjectionMatrix();
    cam.position.set(o.cam[0], o.cam[1], o.cam[2]); cam.up.set(o.cam[6], o.cam[7], o.cam[8]); cam.lookAt(o.cam[3], o.cam[4], o.cam[5]);
    renderer.render(sc, cam);
    return renderer.domElement.toDataURL('image/png');
  };
  window.ready = true;
})();
</script></body></html>`;

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u]; if (!f) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 300 });
  for (const o of spec.frames) {
    if (o.f % +nw !== +kw) continue;
    const fn = path.join(outDir, `v_${String(o.f).padStart(5, '0')}.png`);
    if (fs.existsSync(fn)) continue;
    const url = await p.evaluate(o => window.__frame(o), o);
    fs.writeFileSync(fn, Buffer.from(url.split(',')[1], 'base64'));
  }
  await br.close(); srv.close();
})();
