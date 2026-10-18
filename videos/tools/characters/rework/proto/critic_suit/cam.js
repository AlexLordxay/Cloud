// custom-camera render of the astronaut (same lighting as characters/preview.js)
// node cam.js out.jpg W H t views.json   views: [{pos:[x,y,z], at:[x,y,z] | joint name, fov}]
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = '/home/user/cloud/videos/tools', CH = TOOLS + '/characters';
const [out, W, H, t, vf] = [process.argv[2], +process.argv[3], +process.argv[4], +process.argv[5], process.argv[6]];
const views = JSON.parse(fs.readFileSync(vf, 'utf8'));
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(TOOLS + '/node_modules/three/build/three.min.js', 'utf8')}</script>
<script>${fs.readFileSync(CH + '/emblem.js', 'utf8')}</script>
<script>${fs.readFileSync(process.env.ASTRO || (CH + '/astronaut.js'), 'utf8')}</script>
<script>
  const W = ${W}, H = ${H}, V = ${JSON.stringify(views)}, ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
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
  a.pose(${t}); a.group.updateMatrixWorld(true);
  const n = V.length, cam = new THREE.PerspectiveCamera(30, (W / n) / H, 0.02, 100);
  a.ready.then(() => {
    ren.setScissorTest(true);
    V.forEach((v, i) => {
      ren.setViewport(i * W / n, 0, W / n, H); ren.setScissor(i * W / n, 0, W / n, H);
      const at = typeof v.at === 'string' ? a.joints[v.at].getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(...v.at);
      cam.fov = v.fov || 30; cam.updateProjectionMatrix();
      cam.position.set(at.x + v.pos[0], at.y + v.pos[1], at.z + v.pos[2]); cam.lookAt(at); ren.render(scene, cam);
    });
    window.done = true;
  });
</script></body></html>`;
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  await p.setContent(page);
  await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  const url = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/jpeg', 0.92));
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  await br.close(); console.log('written', out);
})();
