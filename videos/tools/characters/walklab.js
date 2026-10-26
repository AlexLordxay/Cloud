// Walk lab: checks the astronaut's walk (a.walk) without a whole scene, in ~1 minute. It walks 6 steps up a gentle
// slope with small bumps, records every joint at 30 fps (data.json: angles, pelvis, toe/heel height and z — a toe or
// heel whose z changes while it touches the ground is sliding) and renders a side filmstrip of one stride (0.05 s
// apart, a grid on the ground) and a few front views (frames/*.jpg).
//
//   node characters/walklab.js <out dir>
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '..'), OUT = path.resolve(process.argv[2]);
fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/emblem.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/astronaut.js'), 'utf8')}</script>
<script>
  const W = 480, H = 720, ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  ren.setSize(W, H); ren.outputEncoding = THREE.sRGBEncoding; ren.shadowMap.enabled = true; ren.toneMapping = THREE.ACESFilmicToneMapping;
  document.body.appendChild(ren.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x202634);
  const a = window.__makeAstronaut(THREE); scene.add(a.group);
  scene.environment = window.__astronautEnv(THREE, ren);
  const ground = (x, z) => 0.07 * -z + 0.015 * Math.sin(1.3 * x + 0.7 * z);   // uphill ahead (-z), small bumps
  const g = new THREE.PlaneGeometry(12, 30, 120, 300).rotateX(-Math.PI / 2), P = g.attributes.position;
  for (let i = 0; i < P.count; i++) P.setY(i, ground(P.getX(i), P.getZ(i)));
  g.computeVertexNormals();
  const gm = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x9a6a4a, roughness: 1 })); gm.receiveShadow = true; scene.add(gm);
  // a grid on the ground, to judge sliding feet
  const lines = []; for (let z = -15; z <= 15; z += 0.25) for (let x = -1; x < 1; x += 0.1) lines.push(x, ground(x, z) + 0.002, z, x + 0.1, ground(x + 0.1, z) + 0.002, z);
  const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(lines, 3)); scene.add(new THREE.LineSegments(lg, new THREE.LineBasicMaterial({ color: 0x3a2a20 })));
  const key = a.light(0xfff0e0, 2.2, new THREE.Vector3(0.6, 0.8, 0.3)); scene.add(key, key.target, new THREE.HemisphereLight(0x8090b0, 0x403020, 0.6));
  const w = a.walk({ ground, from: [0, 4], heading: 0, steps: 6, step: 0.8, period: 0.76, start: 0, stop: true });
  const cam = new THREE.PerspectiveCamera(30, W / H, 0.05, 100);
  const J = a.joints, V = () => new THREE.Vector3();
  window.record = () => {
    const rows = [];
    for (let f = -15; f <= 210; f++) {
      const t = f / 30; w.update(t); a.group.updateMatrixWorld(true);
      const r = { t, px: a.group.position.x, py: a.group.position.y, pz: a.group.position.z, bodyX: J.body.rotation.x, bodyY: J.body.rotation.y, bodyZ: J.body.rotation.z, headX: J.head.rotation.x };
      for (const n of ['hip', 'knee', 'ankle', 'shoulder', 'elbow']) for (const s of ['L', 'R']) r[n + s] = J[n + s].rotation.x;
      for (const s of ['L', 'R']) {
        const an = J['ankle' + s], toe = an.localToWorld(new THREE.Vector3(0, -0.103, -0.16)), heel = an.localToWorld(new THREE.Vector3(0, -0.103, 0.09));
        r['toeY' + s] = toe.y - ground(toe.x, toe.z); r['heelY' + s] = heel.y - ground(heel.x, heel.z); r['toeZ' + s] = toe.z; r['heelZ' + s] = heel.z;
      }
      rows.push(r);
    }
    return rows;
  };
  window.shot = (t, view) => {
    w.update(t); a.aim();
    const p = a.group.position;
    if (view === 'side') { cam.position.set(p.x + 5.6, p.y - 0.1, p.z); cam.lookAt(p.x, p.y - 0.25, p.z); }
    else { cam.position.set(p.x + 0.3, p.y - 0.1, p.z - 5.8); cam.lookAt(p.x, p.y - 0.25, p.z); }
    ren.render(scene, cam); return ren.domElement.toDataURL('image/jpeg', 0.9);
  };
  a.ready.then(() => { window.done = true; });
</script></body></html>`;
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 480, height: 720 } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.setContent(page);
  await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  fs.writeFileSync(path.join(OUT, 'data.json'), JSON.stringify(await p.evaluate(() => window.record())));
  const save = (name, url) => fs.writeFileSync(path.join(OUT, 'frames', name), Buffer.from(url.split(',')[1], 'base64'));
  for (let i = 0; i < 16; i++) { const t = 2.28 + i * 0.05; save(`side_${String(i).padStart(2, '0')}_t${t.toFixed(2)}.jpg`, await p.evaluate(([t]) => window.shot(t, 'side'), [t])); }
  for (const t of [2.28, 2.47, 2.66, 2.85, 5.6]) save(`front_t${t.toFixed(2)}.jpg`, await p.evaluate(([t]) => window.shot(t, 'front'), [t]));
  for (const t of [4.9, 5.2, 5.6]) save(`side_end_t${t.toFixed(2)}.jpg`, await p.evaluate(([t]) => window.shot(t, 'side'), [t]));
  await br.close(); console.log('ok');
})();
