// A turnaround sheet of a character, to look at it before it goes into a video:
//
//   node characters/preview.js [out.jpg] [t] [pose.json] [views]
//     -> four views (back, back three-quarter, side, front three-quarter) of the idle at time t;
//        pose.json (optional): { "elbowL": [x, y, z], "kneeR": [...], … } joint rotations set after the idle, or
//        { "call": "methodName", "args": [...] } to call a pose method of the character (e.g. a gesture);
//        views: "full" (default), "hands" (close-ups of both hands, front and back), "limbs" (elbows and knees close)
//
// Lit as in the black hole video: a warm key and rim from ahead of the figure (the disc), faint cool light from behind.
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(TOOLS, 'work', 'astronaut_sheet.jpg'));
const t = +(process.argv[3] || 0);
const poseArg = process.argv[4] && process.argv[4] !== '-' ? JSON.parse(fs.readFileSync(process.argv[4], 'utf8')) : null;
const viewsMode = process.argv[5] || 'full';

const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(__dirname, 'emblem.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(__dirname, 'astronaut.js'), 'utf8')}</script>
<script>
  const W = 1600, H = 760, ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  ren.setSize(W, H); ren.outputEncoding = THREE.sRGBEncoding; ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
  ren.toneMapping = THREE.ACESFilmicToneMapping; ren.toneMappingExposure = 1.15;
  document.body.appendChild(ren.domElement);
  const scene = new THREE.Scene(), a = window.__makeAstronaut(THREE);
  scene.background = new THREE.Color(0x05070c);
  scene.environment = window.__astronautEnv(THREE, ren);
  scene.add(a.group);
  // the disc ahead (warm, from the front, up and to the right) and cold starlight from behind on the left; both cast shadows
  const key = a.light(0xffd2a0, 1.7, new THREE.Vector3(0.6, 0.7, -0.6)), back = a.light(0xa9bde2, 1.15, new THREE.Vector3(-0.75, 0.55, 0.6));
  scene.add(key, key.target, back, back.target); a.aim();
  const under = new THREE.DirectionalLight(0xffb070, 0.45); under.position.set(-0.3, -0.8, -0.8); scene.add(under);
  scene.add(new THREE.HemisphereLight(0x6070a0, 0x2a1a10, 0.1));
  a.rim.color.value.setRGB(0.9, 0.6, 0.32);
  a.pose(${t});
  const P = ${JSON.stringify(poseArg)};
  if (P && P.call) a[P.call](...(P.args || []));
  else if (P) for (const k in P) if (a.joints[k]) a.joints[k].rotation.set(...P[k]);
  a.group.updateMatrixWorld(true);
  const mode = ${JSON.stringify(viewsMode)};
  const cam = new THREE.PerspectiveCamera(mode === 'full' ? 30 : 18, (W / 4) / H, 0.02, 100);
  // full: the whole figure from four sides; hands/limbs: close-ups aimed at the joints, from front and back
  const wp = n => a.joints[n].getWorldPosition(new THREE.Vector3());
  const hand = n => wp(n).lerp(a.joints[n].localToWorld(new THREE.Vector3(0, -0.075, 0)), 1);   // the middle of the hand
  const focus = mode === 'hands' ? [hand('wristL'), hand('wristL'), hand('wristR'), hand('wristR')]
              : mode === 'limbs' ? [wp('elbowL'), wp('elbowR'), wp('kneeL'), wp('kneeR')] : null;
  const close = mode === 'hands' ? [[-0.45, 0.1, -1.3], [-0.55, 0.15, 1.2], [0.45, 0.1, -1.3], [0.55, 0.15, 1.2]]
              : [[-1.8, 0.2, -1.6], [1.8, 0.2, -1.6], [-2.4, 0.1, -0.6], [2.4, 0.1, -0.6]];
  const views = focus ? focus.map((f, i) => [f.x + close[i][0], f.y + close[i][1], f.z + close[i][2], f]) : [[0, 0.9, 5.2], [3.6, 1.0, 3.6], [5.2, 0.3, 0], [-2.0, 0.5, -4.8]];
  a.ready.then(() => {
  ren.setScissorTest(true);
  views.forEach(([x, y, z, f], i) => {
    ren.setViewport(i * W / 4, 0, W / 4, H); ren.setScissor(i * W / 4, 0, W / 4, H);
    cam.position.set(x, y, z); if (f) cam.lookAt(f); else cam.lookAt(0, 0.05, 0); ren.render(scene, cam);
  });
  window.done = true;
  });
</script></body></html>`;

(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 1600, height: 760 } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error') console.log(m.text().slice(0, 400)); });
  await p.setContent(page);
  await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  const url = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/jpeg', 0.92));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  await br.close();
  console.log('written', out);
})();
