// custom close-up previewer: node pv.js out.jpg cfg.json
// cfg: { t, pose:{joint:[x,y,z]}, views:[{focus:'shoulderL'|[x,y,z], local:[x,y,z]?, off:[x,y,z], fov}], probe:true }
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = '/home/user/cloud/videos/tools';
const out = path.resolve(process.argv[2]); const cfg = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const NV = (cfg.frames || cfg.views).length, W = 400 * NV, H = 600;
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/emblem.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/astronaut.js'), 'utf8')}</script>
<script>
  const CFG = ${JSON.stringify(cfg)};
  const W = ${W}, H = ${H}, ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  ren.setSize(W, H); ren.outputEncoding = THREE.sRGBEncoding; ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
  ren.toneMapping = THREE.ACESFilmicToneMapping; ren.toneMappingExposure = 1.15;
  document.body.appendChild(ren.domElement);
  const scene = new THREE.Scene(), a = window.__makeAstronaut(THREE);
  scene.background = new THREE.Color(0x10141c);
  scene.environment = window.__astronautEnv(THREE, ren);
  scene.add(a.group);
  const key = a.light(0xffd2a0, 1.7, new THREE.Vector3(0.6, 0.7, -0.6)), back = a.light(0xa9bde2, 1.15, new THREE.Vector3(-0.75, 0.55, 0.6));
  scene.add(key, key.target, back, back.target);
  scene.add(new THREE.HemisphereLight(0x8090c0, 0x3a2a20, 0.5));
  a.rim.color.value.setRGB(0.9, 0.6, 0.32);
  const setPose = P => { a.pose(CFG.t || 0); if (P) for (const k in P) if (a.joints[k]) a.joints[k].rotation.set(...P[k]); a.aim(); a.group.updateMatrixWorld(true); };
  setPose(CFG.pose);
  if (CFG.isolate) { const keep = new Set(); for (const n of CFG.isolate) a.joints[n].traverse(o => keep.add(o)); a.group.traverse(o => { if (o.isMesh || o.isSprite) o.visible = keep.has(o); }); }
  if (CFG.hide) for (const n of CFG.hide) a.joints[n].traverse(o => { if (o.isMesh || o.isSprite) o.visible = false; });
  if (CFG.wire) a.group.traverse(o => { if (o.isMesh) { o.material = o.material.clone(); o.material.wireframe = true; } });
  window.probe = {};
  for (const k in a.joints) window.probe[k] = a.joints[k].getWorldPosition(new THREE.Vector3()).toArray().map(v => +v.toFixed(3));
  const box = new THREE.Box3().setFromObject(a.group); window.probe.box = [box.min.toArray(), box.max.toArray()].map(v => v.map(x => +x.toFixed(3)));
  const cam = new THREE.PerspectiveCamera(20, (W / ${NV}) / H, 0.02, 100);
  a.ready.then(() => {
    ren.setScissorTest(true);
    (CFG.frames || CFG.views.map(v => ({ view: v }))).forEach((fr, i) => {
      if (fr.pose) setPose(fr.pose); const v = fr.view;
      let f;
      if (typeof v.focus === 'string') f = a.joints[v.focus].localToWorld(new THREE.Vector3(...(v.local || [0, 0, 0])));
      else f = new THREE.Vector3(...v.focus);
      cam.fov = v.fov || 20; cam.updateProjectionMatrix();
      ren.setViewport(i * W / ${NV}, 0, W / ${NV}, H); ren.setScissor(i * W / ${NV}, 0, W / ${NV}, H);
      cam.position.set(f.x + v.off[0], f.y + v.off[1], f.z + v.off[2]); cam.lookAt(f); ren.render(scene, cam);
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
  if (cfg.printProbe) console.log(JSON.stringify(await p.evaluate(() => window.probe)));
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  await br.close();
})();
