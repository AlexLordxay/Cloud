// «Знайомся: Нептун» — the astronaut alone, on a transparent background, to lay over the clouds (clouds.py renders the
// world on the CPU; the figure is the same three.js character as in every video, unchanged).
//
//   node scenes/neptune_meet/astro.js <spec.json> <outdir> [n k]   -> <outdir>/a_<frame>.png (RGBA), every n-th from k
//
// spec.json (written by clouds.py): { W, H, frames: [{ f, cam: [px,py,pz, tx,ty,tz, ux,uy,uz], fov, pos: [x,y,z],
//   rot: [x,y,z] (euler, rad), pt (pose time), sun: [x,y,z], sunC: [r,g,b], sky: [r,g,b], gnd: [r,g,b], rim: [r,g,b],
//   spread (arms out, 0–1) }] } — three.js coordinates (y up), metres; the figure ~1.9 m.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..');
const [specF, outDir, nw = '1', kw = '0'] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specF));
const { W, H } = spec;

const page = `<!doctype html><html><body style="margin:0;background:transparent">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script>
<script>
(async () => {
  const T = THREE, W = ${W}, H = ${H};
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true, premultipliedAlpha: false });
  renderer.setSize(W, H); renderer.setClearColor(0x000000, 0);
  renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  document.body.appendChild(renderer.domElement);
  const sc = new T.Scene(), cam = new T.PerspectiveCamera(60, W / H, 0.05, 5000);
  const a = window.__makeAstronaut(T); await a.ready;
  sc.add(a.group);
  // reflections: a cloudscape — blue sky above, bright cloud tops below the horizon, darker blue deeper down
  const envU = { up: { value: new T.Vector3() }, sun: { value: new T.Vector3(0, 1, 0) } };
  const esc = new T.Scene();
  esc.add(new T.Mesh(new T.SphereGeometry(10, 64, 32), new T.ShaderMaterial({ side: T.BackSide, uniforms: envU,
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform vec3 sun; varying vec3 vD; void main(){ float y = vD.y; vec3 c = mix(vec3(0.25, 0.45, 0.75), vec3(0.03, 0.08, 0.25), smoothstep(0.0, 0.8, y));' +
      'c = mix(c, vec3(0.55, 0.68, 0.85), smoothstep(0.02, -0.08, y)); c = mix(c, vec3(0.06, 0.14, 0.35), smoothstep(-0.2, -0.9, y));' +
      'c += vec3(1.0, 0.97, 0.9) * pow(max(dot(vD, sun), 0.0), 400.0) * 30.0; gl_FragColor = vec4(c, 1.0); }' })));
  let envSun = null;
  const sunL = new T.DirectionalLight(0xffffff, 1); sc.add(sunL); sc.add(sunL.target);
  const hemi = new T.HemisphereLight(0x8899ff, 0x223355, 1); sc.add(hemi);
  window.__frame = (o) => {
    const sd = new T.Vector3(...o.sun).normalize();
    if (!envSun || envSun.distanceTo(sd) > 0.05) {
      envU.sun.value.copy(sd);
      const pm = new T.PMREMGenerator(renderer); const tex = pm.fromScene(esc, 0.02).texture; pm.dispose();
      sc.environment = tex; envSun = sd.clone();
    }
    a.pose(o.pt);
    const J = a.joints, sp = o.spread || 0;
    // free fall, belly to the wind: arms out and up, knees bent
    for (const s of [-1, 1]) { const L = s < 0 ? 'L' : 'R';
      J['shoulder' + L].rotation.z += s * 0.75 * sp; J['shoulder' + L].rotation.x -= 0.35 * sp;
      J['elbow' + L].rotation.x += 0.25 * sp; J['hip' + L].rotation.z += s * 0.18 * sp; J['knee' + L].rotation.x -= 0.5 * sp; }
    J.head.rotation.x -= 0.35 * sp;
    a.group.position.set(...o.pos); if (o.quat) a.group.quaternion.set(...o.quat); else a.group.rotation.set(o.rot[0], o.rot[1], o.rot[2], o.order || 'XYZ');
    sunL.position.copy(a.group.position).addScaledVector(sd, 10); sunL.target.position.copy(a.group.position);
    sunL.color.setRGB(...o.sunC); sunL.intensity = 1;
    hemi.color.setRGB(...o.sky); hemi.groundColor.setRGB(...o.gnd); hemi.intensity = 1;
    a.rim.color.value.setRGB(...(o.rim || [0, 0, 0])); a.rim.power.value = 2.5;
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
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js') };
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
    const fn = path.join(outDir, `a_${String(o.f).padStart(5, '0')}.png`);
    if (fs.existsSync(fn)) continue;
    const url = await p.evaluate(o => window.__frame(o), o);
    fs.writeFileSync(fn, Buffer.from(url.split(',')[1], 'base64'));
  }
  await br.close(); srv.close();
})();
