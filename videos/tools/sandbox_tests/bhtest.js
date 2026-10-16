// Standalone render of the sandbox black-hole shader: node bhtest.js out.png camX camY camZ
const fs = require('fs'), path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const src = fs.readFileSync('/home/user/cloud/planetarium/js/sandbox.js', 'utf8');
const a = src.indexOf('const mat = new THREE.ShaderMaterial({'), b = src.indexOf('const quad = new THREE.Mesh', a);
const matCode = src.slice(a, b);
const rotLine = src.match(/mat\.uniforms\.rot\.value\.setFromMatrix4\([^\n]*/)[0];
const cam = process.argv.slice(3, 6).map(Number);
const html = `<html><body style="margin:0;background:#000"><script src="three.js"></script><script>
const HOLE_S = ${src.match(/const HOLE_S = ([\d.]+)/)[1]};
const renderer = new THREE.WebGLRenderer({ preserveDrawingBuffer: true }); renderer.setSize(390, 844); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(45, 390/844, 0.1, 1e5);
camera.position.set(${cam}); camera.lookAt(0,0,0);
${matCode}
${rotLine}
mat.uniforms.R.value = 1; mat.uniforms.time.value = 3;
const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat); quad.frustumCulled = false; scene.add(quad);
const ball = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 8), new THREE.MeshBasicMaterial({ color: 0x3355ff })); ball.position.set(20, 0, 0); scene.add(ball);
renderer.render(scene, camera); window.done = 1;
</script></body></html>`;
fs.writeFileSync(path.join(__dirname, 'bhtest.html'), html);
(async () => {
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: 390, height: 844 } });
  p.on('console', m => console.log(m.text())); p.on('pageerror', e => console.log('ERR', e.message));
  await p.route('**/three.js', r => r.fulfill({ path: path.join(process.env.THREE_DIR || path.join(__dirname, 'three/package'), 'build/three.min.js'), contentType: 'application/javascript' }));
  await p.goto('file://' + path.join(__dirname, 'bhtest.html'));
  await p.waitForFunction(() => window.done, null, { timeout: 60000 });
  await p.screenshot({ path: process.argv[2] }); await br.close();
})();
