// harness: like characters/preview.js but runs an extra JS file (inject) in the page after a.pose(t).
//   node harness.js out.jpg t inject.js|- full|hands|limbs|none [stats]
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = '/home/user/cloud/videos/tools', CH = TOOLS + '/characters';
const out = path.resolve(process.argv[2]);
const t = +(process.argv[3] || 0);
const inject = process.argv[4] && process.argv[4] !== '-' ? fs.readFileSync(process.argv[4], 'utf8') : '';
const viewsMode = process.argv[5] || 'full';
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(CH, 'emblem.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(CH, 'astronaut.js'), 'utf8')}</script>
<script>
  const W = 1600, H = 760, ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  ren.setSize(W, H); ren.outputEncoding = THREE.sRGBEncoding; ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
  ren.toneMapping = THREE.ACESFilmicToneMapping; ren.toneMappingExposure = 1.15;
  document.body.appendChild(ren.domElement);
  const scene = new THREE.Scene(), a = window.__makeAstronaut(THREE);
  scene.background = new THREE.Color(0x05070c);
  scene.environment = window.__astronautEnv(THREE, ren);
  scene.add(a.group);
  const key = a.light(0xffd2a0, 1.7, new THREE.Vector3(0.6, 0.7, -0.6)), back = a.light(0xa9bde2, 1.15, new THREE.Vector3(-0.75, 0.55, 0.6));
  scene.add(key, key.target, back, back.target); a.aim();
  const under = new THREE.DirectionalLight(0xffb070, 0.45); under.position.set(-0.3, -0.8, -0.8); scene.add(under);
  scene.add(new THREE.HemisphereLight(0x6070a0, 0x2a1a10, 0.1));
  a.rim.color.value.setRGB(0.9, 0.6, 0.32);
  const T0 = ${t};
  window.__stats = null;
  a.pose(T0);
  ${inject}
  a.group.updateMatrixWorld(true);
  const mode = ${JSON.stringify(viewsMode)};
  if (mode === 'none') { window.done = true; } else {
  const cam = new THREE.PerspectiveCamera(mode === 'full' ? 30 : 18, (W / 4) / H, 0.02, 100);
  const wp = n => a.joints[n].getWorldPosition(new THREE.Vector3());
  const hand = n => a.joints[n].localToWorld(new THREE.Vector3(0, -0.15, 0));
  const focus = mode === 'hands' ? [hand('wristL'), hand('wristL'), hand('wristR'), hand('wristR')]
              : mode === 'limbs' ? [wp('elbowL'), wp('elbowR'), wp('kneeL'), wp('kneeR')] : null;
  const close = mode === 'hands' ? [[-0.45, 0.1, -1.3], [-0.55, 0.15, 1.2], [0.45, 0.1, -1.3], [0.55, 0.15, 1.2]]
              : [[-1.8, 0.2, -1.6], [1.8, 0.2, -1.6], [-2.4, 0.1, -0.6], [2.4, 0.1, -0.6]];
  const views = focus ? focus.map((f, i) => [f.x + close[i][0], f.y + close[i][1], f.z + close[i][2], f]) : (window.__views || [[0, 0.9, 5.2], [3.6, 1.0, 3.6], [5.2, 0.3, 0], [-2.0, 0.5, -4.8]]);
  a.ready.then(() => {
  ren.setScissorTest(true);
  views.forEach(([x, y, z, f], i) => {
    ren.setViewport(i * W / 4, 0, W / 4, H); ren.setScissor(i * W / 4, 0, W / 4, H);
    cam.position.set(x, y, z); if (f) cam.lookAt(f); else cam.lookAt(0, 0.05, 0); ren.render(scene, cam);
  });
  window.done = true;
  });
  }
</script></body></html>`;
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 1600, height: 760 } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (!m.text().includes('GL Driver')) console.log(m.text().slice(0, 4000)); });
  await p.setContent(page);
  await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  if (viewsMode !== 'none') {
    const url = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/jpeg', 0.92));
    fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
    console.log('written', out);
  }
  await br.close();
})();
