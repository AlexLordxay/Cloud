// Critic tool: close-ups of both gloves in the hand's own frame, with optional finger poses.
//   node handview.js out.jpg t pose.js
// pose.js: JS body run in the page with (a, F, THREE) where F.L / F.R = { hand, fingers:[{base,tip}], thumb:{base,tip} }
// Layout 1600x760: row 0 = left glove, row 1 = right glove; columns = palm side, back side, thumb side, fingertip/side.
const fs = require('fs'), path = require('path');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = '/home/user/cloud/videos/tools';
const out = path.resolve(process.argv[2]);
const t = +(process.argv[3] || 0);
const poseJs = process.argv[4] && process.argv[4] !== '-' ? fs.readFileSync(process.argv[4], 'utf8') : '';
const dist = +(process.argv[5] || 0.55);
const page = `<!doctype html><html><body style="margin:0;background:#000">
<script>${fs.readFileSync(path.join(TOOLS, 'node_modules/three/build/three.min.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/emblem.js'), 'utf8')}</script>
<script>${fs.readFileSync(path.join(TOOLS, 'characters/astronaut.js'), 'utf8')}</script>
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
  scene.add(new THREE.HemisphereLight(0x6070a0, 0x2a1a10, 0.35));
  a.rim.color.value.setRGB(0.9, 0.6, 0.32);
  a.pose(${t});
  const F = {};
  for (const L of ['L', 'R']) {
    const wr = a.joints['wrist' + L];
    const hand = wr.children.find(c => c.isGroup);
    const gs = hand.children.filter(c => c.isGroup);
    const fingers = gs.slice(0, 4).map(b => ({ base: b, tip: b.children.find(c => c.isGroup) }));
    const thumb = { base: gs[4], tip: gs[4].children.find(c => c.isGroup) };
    F[L] = { wr, hand, fingers, thumb, s: L === 'L' ? -1 : 1 };
  }
  window.F = F;
  ${poseJs}
  a.group.updateMatrixWorld(true);
  const cam = new THREE.PerspectiveCamera(16, (W / 4) / (H / 2), 0.02, 100);
  ren.setScissorTest(true);
  const D = ${dist};
  a.ready.then(() => {
    ['L', 'R'].forEach((L, row) => {
      const hand = F[L].hand, s = F[L].s;
      const c = hand.localToWorld(new THREE.Vector3(0, -0.075, 0));
      // palm side (-z local), back (+z), thumb side (s*x), and from the fingertips looking up (-y) slightly from palm
      const dirs = [[0, 0, -1], [0, 0, 1], [s, 0, -0.25], [-s * 0.3, -1, -0.6]];
      dirs.forEach((d, i) => {
        const p = hand.localToWorld(new THREE.Vector3(d[0], d[1], d[2]).normalize().multiplyScalar(D).add(new THREE.Vector3(0, -0.075, 0)));
        const up = hand.localToWorld(new THREE.Vector3(0, 1, 0)).sub(hand.getWorldPosition(new THREE.Vector3())).normalize();
        if (i === 3) up.copy(hand.localToWorld(new THREE.Vector3(0, 0, 1)).sub(hand.getWorldPosition(new THREE.Vector3())).normalize());
        cam.position.copy(p); cam.up.copy(up); cam.lookAt(c);
        const y = (1 - row) * H / 2;
        ren.setViewport(i * W / 4, y, W / 4, H / 2); ren.setScissor(i * W / 4, y, W / 4, H / 2);
        ren.render(scene, cam);
      });
    });
    window.done = true;
  });
</script></body></html>`;
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 1600, height: 760 } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'log') console.log(m.text().slice(0, 600)); });
  await p.setContent(page);
  await p.waitForFunction(() => window.done, null, { timeout: 120000 });
  const url = await p.evaluate(() => document.querySelector('canvas').toDataURL('image/jpeg', 0.92));
  fs.writeFileSync(out, Buffer.from(url.split(',')[1], 'base64'));
  await br.close();
  console.log('written', out);
})();
