// A turnaround sheet of a character, to look at it before it goes into a video:
//
//   node characters/preview.js [out.jpg] [t]     -> four views (back, back three-quarter, side, front three-quarter)
//
// Lit as in the black hole video: a warm key and rim from ahead of the figure (the disc), faint cool light from behind.
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(TOOLS, 'work', 'astronaut_sheet.jpg'));
const t = +(process.argv[3] || 0);

const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
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
  const key = a.keyLight(0xffd2a0, 1.8); scene.add(key, key.target); a.aimKey(new THREE.Vector3(0.6, 0.7, -0.6));
  const fill = new THREE.DirectionalLight(0x8fa4d0, 0.45); fill.position.set(-0.5, 0.5, 1); scene.add(fill);
  const under = new THREE.DirectionalLight(0xffb070, 0.7); under.position.set(-0.3, -0.8, -0.8); scene.add(under);
  scene.add(new THREE.HemisphereLight(0x6070a0, 0x3a2414, 0.18));
  a.rim.color.value.setRGB(0.9, 0.6, 0.32);
  a.pose(${t});
  const cam = new THREE.PerspectiveCamera(30, (W / 4) / H, 0.05, 100);
  const views = [[0, 0.9, 5.2], [3.6, 1.0, 3.6], [5.2, 0.3, 0], [-2.0, 0.5, -4.8]];
  ren.setScissorTest(true);
  views.forEach(([x, y, z], i) => {
    ren.setViewport(i * W / 4, 0, W / 4, H); ren.setScissor(i * W / 4, 0, W / 4, H);
    cam.position.set(x, y, z); cam.lookAt(0, 0.05, 0); ren.render(scene, cam);
  });
  window.done = true;
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
