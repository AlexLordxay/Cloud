// «Знайомся: Нептун» — the three.js layer: the astronaut (the same character as in every video, his look unchanged),
// and around him what the clouds don't draw: Neptune from space (with Triton, the Earth for scale, the stars), and the
// rain of diamonds in the dark (lit by his helmet lamp). Transparent where nothing is drawn, so clouds.py's frames go
// underneath (shots.py lays them together).
//
//   node scenes/neptune_meet/layer.js <spec.json> <outdir> [n k]   -> <outdir>/a_<frame>.png (RGBA), every n-th from k
//
// spec.json (shots.py): { W, H, frames: [{ f, cam: [px,py,pz, tx,ty,tz, ux,uy,uz], fov (vertical, °), expo,
//   astro: { on, pos, quat, pt, flow: {…} (see below), frost, lamp },
//   light: { sun: [x,y,z], sunC, sky, gnd, rim },
//   space: { on, cam: [same as cam, in km, Neptune at the origin], nepRot, pale (0 = the Voyager blue, 1 = the real
//            pale colour), triton: [x,y,z km], earth: { on, pos: [x,y,z km], k (0–1, fades in) }, stars },
//   gems: { on, t, n, box: [cx,cy,cz, rx,ry,rz], fall, k } }]}   — three.js coordinates (y up); the figure ~1.9 m.
//
// The figure moves softly: every joint follows a few slow sines on top of the free-fall idle, the poses ease into
// each other over a second or more, the limbs lag the body a little (flow.*: spread, wind, hug, reach, look).
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [specF, outDir, nw = '1', kw = '0'] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specF));
const { W, H } = spec;

const page = `<!doctype html><html><body style="margin:0;background:transparent">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script><script src="/fx.js"></script>
<script>
(async () => {
  const T = THREE, W = ${W}, H = ${H};
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true, premultipliedAlpha: false });
  renderer.setSize(W, H); renderer.setClearColor(0x000000, 0); renderer.autoClear = false;
  renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping;
  document.body.appendChild(renderer.domElement);
  const load = f => new Promise(r => new T.TextureLoader().load(f, t => { t.encoding = T.sRGBEncoding; t.anisotropy = 8; r(t); }));
  const [nepTex, triTex, earthTex] = await Promise.all(['/site/neptune.jpg', '/site/triton.jpg', '/site/earth_day.jpg'].map(load));

  // ------------------------------------------------ space (km): Neptune, Triton, the Earth, the stars
  const far = new T.Scene(), farCam = new T.PerspectiveCamera(40, W / H, 100, 5e7);
  const NU = { tex: { value: nepTex }, sun: { value: new T.Vector3(1, 0, 0) }, pale: { value: 1 }, rot: { value: 0 } };
  const nep = new T.Mesh(new T.SphereGeometry(24764, 128, 64), new T.ShaderMaterial({ uniforms: NU,
    vertexShader: 'varying vec3 vN, vW; varying vec2 vUv; void main(){ vUv = uv; vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D tex; uniform vec3 sun; uniform float pale, rot; varying vec3 vN, vW; varying vec2 vUv;
      void main(){ vec3 n = normalize(vN), V = normalize(cameraPosition - vW);
        vec3 c = texture2D(tex, vUv + vec2(rot, 0.0)).rgb;          // sRGB-decoded: linear
        // the real colour (Irwin et al. 2024): a pale greenish blue, like Uranus but a touch deeper — the same
        // pattern of light and dark, much less saturated
        float l = dot(c, vec3(0.3, 0.45, 0.25));
        // keep the bands and spots: stretch the brightness about its mean
        l = 0.16 + (l - 0.16) * 2.2;
        vec3 pc = vec3(0.27, 0.45, 0.68) * (0.5 + 1.9 * max(l, 0.0)) + vec3(0.02, 0.025, 0.02);
        c = mix(c, pc, pale);
        float mu = dot(n, sun), d = max(mu, 0.0);
        float limb = pow(max(dot(n, V), 0.0), 0.35);                  // limb darkening of a gas giant
        vec3 col = c * (d * 1.9 * (0.55 + 0.45 * limb) + 0.012);
        // the haze at the limb, lit where the Sun is
        float fr = pow(1.0 - max(dot(n, V), 0.0), 3.0);
        col += mix(vec3(0.12, 0.35, 0.8), vec3(0.35, 0.55, 0.75), pale) * fr * smoothstep(-0.25, 0.4, mu) * 0.9;
        gl_FragColor = vec4(col, 1.0); }\` }));
  far.add(nep);
  // the atmosphere's glow just outside the disc
  const glow = new T.Mesh(new T.SphereGeometry(24764 * 1.035, 96, 48), new T.ShaderMaterial({ uniforms: NU, transparent: true, depthWrite: false, side: T.BackSide, blending: T.AdditiveBlending,
    vertexShader: 'varying vec3 vN, vW; void main(){ vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform vec3 sun; uniform float pale; varying vec3 vN, vW;
      void main(){ vec3 n = normalize(vN), V = normalize(cameraPosition - vW); float r = 1.0 - abs(dot(n, V));
        float a = pow(smoothstep(0.0, 1.0, 1.0 - r * 1.0), 5.0) * smoothstep(-0.3, 0.5, dot(n, sun));
        gl_FragColor = vec4(mix(vec3(0.15, 0.4, 1.0), vec3(0.4, 0.65, 0.85), pale) * a * 0.6, 1.0); }\` }));
  far.add(glow);
  // the rings: faint, dusty (Adams, Le Verrier, Galle; Adams' arcs are too fine to show)
  const ringU = { sun: NU.sun };
  const ring = new T.Mesh(new T.RingGeometry(41900, 63000, 256, 1), new T.ShaderMaterial({ uniforms: ringU, transparent: true, depthWrite: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    vertexShader: 'varying vec3 vL; void main(){ vL = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: \`varying vec3 vL; float bump(float r, float c, float w){ return exp(-pow((r - c) / w, 2.0)); }
      void main(){ float r = length(vL.xy);
        float a = 0.5 * bump(r, 41900.0 + 1000.0, 700.0) + 0.55 * bump(r, 53200.0, 400.0) + 0.9 * bump(r, 62932.0, 300.0) + 0.12 * bump(r, 57000.0, 3500.0);
        gl_FragColor = vec4(vec3(0.55, 0.6, 0.7) * a * 0.22, 1.0); }\` }));
  ring.rotation.x = -Math.PI / 2; far.add(ring);
  // Neptune's shadow on the rings is left out (they are barely there anyway)
  const sunLfar = new T.DirectionalLight(0xffffff, 1.9); far.add(sunLfar); far.add(new T.AmbientLight(0x101820, 0.15));
  const tri = new T.Mesh(new T.SphereGeometry(1353, 64, 32), new T.MeshStandardMaterial({ map: triTex, roughness: 1 })); far.add(tri);
  const earth = new T.Mesh(new T.SphereGeometry(6371, 96, 48), new T.MeshStandardMaterial({ map: earthTex, roughness: 0.9, transparent: true })); far.add(earth);
  // the stars: a sphere of points (dimmer and fewer near Neptune's glare is left to the exposure)
  const NS = 4000, sp = new Float32Array(NS * 3), sc = new Float32Array(NS * 3);
  let seed = 7; const rr = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < NS; i++) { const u = rr() * 2 - 1, ph = rr() * 6.283, s = Math.sqrt(1 - u * u);
    sp.set([s * Math.cos(ph) * 4e7, u * 4e7, s * Math.sin(ph) * 4e7], i * 3);
    const b = Math.pow(rr(), 6) * 0.9 + 0.05, tint = rr(); sc.set([b * (0.85 + 0.15 * tint), b * 0.9, b * (1.05 - 0.2 * tint)], i * 3); }
  const sg = new T.BufferGeometry(); sg.setAttribute('position', new T.BufferAttribute(sp, 3)); sg.setAttribute('color', new T.BufferAttribute(sc, 3));
  const stars = new T.Points(sg, new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false })); far.add(stars);

  // ------------------------------------------------ near (m): the astronaut and the diamonds
  const near = new T.Scene(), cam = new T.PerspectiveCamera(60, W / H, 0.05, 5000);
  const a = window.__makeAstronaut(T); await a.ready;
  a.group.traverse(o => { o.castShadow = false; o.receiveShadow = false; });
  a.group.traverse(o => { const m = o.material; if (m && m.isMeshPhysicalMaterial && m.metalness === 1 && m.clearcoat === 1 && m.envMapIntensity === 1.4) m.userData.visor = true; });
  const fx = window.__astroFX(T, a);
  a.group.traverse(o => { const m = o.material; if (m && m.userData && m.userData.visor) { const p = m.onBeforeCompile; m.onBeforeCompile = (sh, r) => { p(sh, r); sh.fragmentShader = sh.fragmentShader.replace('fxFrostK = smoothstep', 'fxFrostK = 0.0 * smoothstep'); }; m.needsUpdate = true; } });
  near.add(a.group);
  // reflections: a cloudscape — a blue sky above, cloud tops below the horizon, darker blue deeper down
  const envU = { sun: { value: new T.Vector3(0, 1, 0) }, deep: { value: 0 } };
  const esc = new T.Scene();
  esc.add(new T.Mesh(new T.SphereGeometry(10, 64, 32), new T.ShaderMaterial({ side: T.BackSide, uniforms: envU,
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform vec3 sun; uniform float deep; varying vec3 vD; void main(){ float y = vD.y; vec3 c = mix(vec3(0.25, 0.45, 0.75), vec3(0.03, 0.08, 0.25), smoothstep(0.0, 0.8, y));' +
      'c = mix(c, vec3(0.55, 0.68, 0.85), smoothstep(0.02, -0.08, y)); c = mix(c, vec3(0.06, 0.14, 0.35), smoothstep(-0.2, -0.9, y));' +
      'c = mix(c, vec3(0.01, 0.025, 0.06) * (1.0 + y), deep);' +
      'c += vec3(1.0, 0.97, 0.9) * pow(max(dot(vD, sun), 0.0), 400.0) * 30.0 * (1.0 - deep); gl_FragColor = vec4(c, 1.0); }' })));
  let envKey = '';
  const sunL = new T.DirectionalLight(0xffffff, 1); near.add(sunL); near.add(sunL.target);
  const hemi = new T.HemisphereLight(0x8899ff, 0x223355, 1); near.add(hemi);
  // the helmet lamp: a spot from the lamp on the left of the helmet, along the head's gaze
  const lamp = new T.SpotLight(0xfff2dd, 0, 60, 0.42, 0.6, 1.2); near.add(lamp); near.add(lamp.target);
  // the diamonds: octahedra stretched like cut stones, mirror-bright, catching the lamp and the dim blue around;
  // each also gets a glint (an additive star) that flares when its facet turns to the light
  const NG = 900;
  const gGeo = new T.OctahedronGeometry(1, 0); gGeo.scale(0.8, 1.1, 0.8);
  // the stones: a shader of their own — a dark, clear body (the deep blue seen through it), a bright rim where the face
  // turns away (fresnel), and the flash: a facet's mirror direction meeting the helmet lamp or one of the hidden lights
  // around flares white, edged with the rainbow of dispersion. As they spin, facets flash on and off.
  const gU = { lampP: { value: new T.Vector3() }, lampI: { value: 0 }, tt: { value: 0 } };
  const gMat = new T.ShaderMaterial({ uniforms: gU,
    vertexShader: 'varying vec3 vW; varying float vId; void main(){ vec4 w = modelMatrix * instanceMatrix * vec4(position, 1.0); vW = w.xyz; vId = float(gl_InstanceID); gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform vec3 lampP; uniform float lampI, tt; varying vec3 vW; varying float vId;
      float h(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
      vec3 hue(float x){ return clamp(abs(fract(x + vec3(0.0, 0.667, 0.333)) * 6.0 - 3.0) - 1.0, 0.0, 1.0); }
      void main(){
        vec3 n = normalize(cross(dFdx(vW), dFdy(vW)));
        vec3 V = normalize(cameraPosition - vW); if (dot(n, V) < 0.0) n = -n;
        vec3 R = reflect(-V, n);
        float fr = pow(1.0 - max(dot(n, V), 0.0), 3.0);
        vec3 c = vec3(0.012, 0.03, 0.075) + vec3(0.12, 0.2, 0.32) * fr;
        // the lamp
        vec3 L = normalize(lampP - vW); float dl = length(lampP - vW);
        float sp = pow(max(dot(R, L), 0.0), 40.0) * lampI * 1.6 / (1.0 + 0.04 * dl * dl);
        c += vec3(1.0, 0.97, 0.9) * sp;
        // hidden lights all round: a grid of directions, some lit
        vec3 g = floor(R * 5.0 + 0.5); float k = h(g + floor(vId));
        float d = length(normalize(g + 1e-3) - R);
        float on = step(0.72, k) * smoothstep(0.16, 0.03, d);
        c += (vec3(0.8) + 0.9 * hue(d * 9.0 + k * 3.0)) * on * 2.2;
        // a soft sheen from above (the faint light of the depths)
        c += vec3(0.1, 0.18, 0.3) * pow(max(R.y, 0.0), 6.0);
        gl_FragColor = vec4(c, 1.0);
        #include <tonemapping_fragment>
        #include <encodings_fragment>
      }\` });
  const gems = new T.InstancedMesh(gGeo, gMat, NG); gems.instanceMatrix.setUsage(T.DynamicDrawUsage); near.add(gems);
  const gl = new Float32Array(NG * 3), gcol = new Float32Array(NG * 3), gsz = new Float32Array(NG);
  const glG = new T.BufferGeometry(); glG.setAttribute('position', new T.BufferAttribute(gl, 3)); glG.setAttribute('col', new T.BufferAttribute(gcol, 3)); glG.setAttribute('size', new T.BufferAttribute(gsz, 1));
  // added light: the colour adds up, and the alpha grows with the brightness (so laid over the clouds later, a glint
  // still shows; where it is dark nothing covers what is behind)
  const glints = new T.Points(glG, new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.CustomBlending,
    blendSrc: T.OneFactor, blendDst: T.OneFactor, blendSrcAlpha: T.OneFactor, blendDstAlpha: T.OneFactor, uniforms: { vh: { value: H } },
    vertexShader: 'attribute vec3 col; attribute float size; uniform float vh; varying vec3 vC; void main(){ vC = col; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv; gl_PointSize = size > 0.0 ? max(2.0, size * projectionMatrix[1][1] * vh * 0.5 / -mv.z) : 0.0; }',
    fragmentShader: 'varying vec3 vC; void main(){ vec2 q = gl_PointCoord * 2.0 - 1.0; float r = length(q); float a = exp(-r * r * 30.0) * 1.4 + 0.5 * exp(-abs(q.x) * 40.0) * exp(-abs(q.y) * 3.0) + 0.5 * exp(-abs(q.y) * 40.0) * exp(-abs(q.x) * 3.0); vec3 c = vC * a; gl_FragColor = vec4(c, clamp(max(c.r, max(c.g, c.b)), 0.0, 1.0)); }' }));
  glints.frustumCulled = false; near.add(glints);
  const G = []; seed = 11;
  for (let i = 0; i < NG; i++) G.push({ x: rr(), y: rr(), z: rr(), s: 0.022 + 0.06 * Math.pow(rr(), 2.4), v: 0.7 + 0.6 * rr(), ax: new T.Vector3(rr() - 0.5, rr() - 0.5, rr() - 0.5).normalize(), w: 1 + 3 * rr(), ph: rr() * 6.28, sw: rr() * 6.28 });
  const M4 = new T.Matrix4(), Q = new T.Quaternion(), V3 = new T.Vector3(), S3 = new T.Vector3();

  // ------------------------------------------------ the soft motion
  const sm = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const n1 = (t, f, p) => Math.sin(t * f + p) * 0.6 + Math.sin(t * f * 1.73 + p * 2.1) * 0.3 + Math.sin(t * f * 2.91 + p * 0.7) * 0.1;   // smooth, never repeating quickly
  function flow(t, o) {
    // the free-fall idle first (breath, drift, glances), then layers on top
    a.pose(t, { glance: !o.look });
    const J = a.joints, sp = o.spread || 0, wd = o.wind || 0, hug = o.hug || 0, reach = o.reach || 0;
    for (const s of [-1, 1]) { const L = s < 0 ? 'L' : 'R', ph = s < 0 ? 0 : 1.7;
      const sh = J['shoulder' + L].rotation, el = J['elbow' + L].rotation, wr = J['wrist' + L].rotation;
      // arms out to the sides and a little up, as a skydiver balances: they float, each on its own slow phase,
      // the elbow and the wrist following the shoulder a beat later (so the arm bends like a soft thing, not a hinge)
      sh.z += s * sp * (0.85 + 0.12 * n1(t, 0.9, ph)); sh.x -= sp * (0.3 + 0.1 * n1(t, 0.7, ph + 1));
      el.x += sp * (0.15 + 0.12 * n1(t - 0.25, 0.9, ph)); wr.z += s * sp * 0.15 * n1(t - 0.45, 0.9, ph);
      // the wind: faster, smaller flutter on the forearms and the hands, the whole arm pushed back
      sh.x -= wd * (0.25 + 0.08 * n1(t, 3.1, ph)); sh.z += s * wd * 0.1 * n1(t, 2.3, ph + 2);
      el.x += wd * 0.1 * n1(t - 0.12, 4.2, ph); wr.x += wd * 0.18 * n1(t - 0.2, 5.0, ph + 1);
      // cold: the arms come in and fold over the chest, slowly (the shoulders forward, the elbows bent)
      sh.z = sh.z * (1 - hug) + s * 0.25 * hug; sh.x = sh.x * (1 - hug) + 0.9 * hug; sh.y = sh.y * (1 - hug) - s * 0.55 * hug;
      el.x = el.x * (1 - hug) + 1.9 * hug;
      // legs: knees bent, feet drifting apart and together
      J['hip' + L].rotation.z += s * (sp * 0.2 + 0.05 * n1(t, 0.6, ph + 3) + wd * 0.08 * n1(t, 2.2, ph));
      J['knee' + L].rotation.x -= sp * (0.45 + 0.12 * n1(t - 0.3, 0.8, ph)) + wd * 0.12 * n1(t, 2.7, ph) + hug * 0.4;
      J['ankle' + L].rotation.x += 0.08 * n1(t - 0.5, 0.8, ph);
    }
    // reaching out with the right hand (toward a diamond): the shoulder leads, the elbow opens after it, the fingers last
    if (reach > 0) { const sh = J.shoulderR.rotation, el = J.elbowR.rotation;
      const r1 = sm(reach * 1.25), r2 = sm(reach * 1.25 - 0.2);
      sh.x = sh.x * (1 - r1) + (1.25 + 0.05 * n1(t, 0.8, 0)) * r1; sh.z = sh.z * (1 - r1) + 0.25 * r1; sh.y = sh.y * (1 - r1) - 0.15 * r1;
      el.x = el.x * (1 - r2) + 0.25 * r2; a.hand && a.hand('R', 'relaxed'); }
    // the head: where he looks (yaw, pitch), eased; else the idle's own glances
    if (o.look) { J.head.rotation.x = o.look[1]; J.head.rotation.y = o.look[0]; }
    J.head.rotation.x -= sp * 0.25;
    J.body.rotation.x += 0.06 * n1(t, 0.5, 4); J.body.rotation.z += 0.05 * n1(t, 0.4, 5) + wd * 0.06 * n1(t, 1.9, 1);
  }

  window.__frame = (o) => {
    // the reflections first (a PMREM render leaves the canvas and the clear colour in its own state)
    { const L = o.light, sd = new T.Vector3(...L.sun).normalize();
      const key = sd.toArray().map(v => v.toFixed(2)).join() + (L.deep || 0).toFixed(2);
      if (key !== envKey) { envU.sun.value.copy(sd); envU.deep.value = L.deep || 0;
        const pm = new T.PMREMGenerator(renderer); near.environment = pm.fromScene(esc, 0.02).texture; pm.dispose(); envKey = key; } }
    renderer.setRenderTarget(null); renderer.setClearColor(0x000000, 0); renderer.clear();
    if (o.space && o.space.on) {
      const s = o.space, sd = new T.Vector3(...o.light.sun).normalize();
      NU.sun.value.copy(sd); NU.pale.value = s.pale; NU.rot.value = s.nepRot || 0;
      sunLfar.position.copy(sd).multiplyScalar(1e6);
      tri.position.set(...s.triton); tri.rotation.y = 2.0;
      earth.visible = !!(s.earth && s.earth.on); if (earth.visible) { earth.position.set(...s.earth.pos); earth.material.opacity = s.earth.k; earth.rotation.y = 1.2 + 0.05 * (o.t || 0); }
      stars.visible = s.stars !== false;
      farCam.fov = o.fov; farCam.aspect = W / H; farCam.updateProjectionMatrix();
      farCam.position.set(s.cam[0], s.cam[1], s.cam[2]); farCam.up.set(s.cam[6], s.cam[7], s.cam[8]); farCam.lookAt(s.cam[3], s.cam[4], s.cam[5]);
      renderer.toneMappingExposure = s.expo || 1;
      renderer.render(far, farCam);
      renderer.clearDepth();
    }
    const L = o.light, sd = new T.Vector3(...L.sun).normalize();
    cam.fov = o.fov; cam.aspect = W / H; cam.updateProjectionMatrix();
    cam.position.set(o.cam[0], o.cam[1], o.cam[2]); cam.up.set(o.cam[6], o.cam[7], o.cam[8]); cam.lookAt(o.cam[3], o.cam[4], o.cam[5]);
    sunL.color.setRGB(...L.sunC); sunL.intensity = 1;
    hemi.color.setRGB(...L.sky); hemi.groundColor.setRGB(...L.gnd);
    a.rim.color.value.setRGB(...(L.rim || [0, 0, 0])); a.rim.power.value = 2.5;
    renderer.toneMappingExposure = o.expo || 1;
    const A = o.astro || {};
    a.group.visible = !!A.on;
    if (A.on) {
      flow(A.pt, A.flow || {});
      a.group.position.set(...A.pos); a.group.quaternion.set(...A.quat);
      a.group.updateMatrixWorld(true);
      fx.U.uFrost.value = A.frost || 0; fx.U.uTime.value = A.pt; fx.update();
      sunL.position.copy(a.group.position).addScaledVector(sd, 10); sunL.target.position.copy(a.group.position);
      // the lamp on the helmet, pointing where the head looks
      const hp = new T.Vector3(-0.214, 0.2, -0.1).applyMatrix4(a.joints.head.matrixWorld);
      const hd = new T.Vector3(0, -0.05, -1).transformDirection(a.joints.head.matrixWorld);
      lamp.position.copy(hp); lamp.target.position.copy(hp).addScaledVector(hd, 10); lamp.intensity = A.lamp || 0;
    } else lamp.intensity = 0;
    const g = o.gems;
    gems.visible = glints.visible = !!(g && g.on);
    if (g && g.on) {
      const [cx, cy, cz, rx, ry, rz] = g.box, camP = cam.position, lampP = lamp.position, lampD = lamp.target.position.clone().sub(lampP).normalize();
      for (let i = 0; i < NG; i++) { const q = G[i];
        if (i >= g.n) { M4.makeScale(0, 0, 0); gems.setMatrixAt(i, M4); gsz[i] = 0; continue; }
        // falling (wrapping round in the box), swaying a little, spinning slowly
        let y = ((q.y - g.t * g.fall * q.v / (2 * ry)) % 1 + 1) % 1;
        const p = V3.set(cx + (q.x - 0.5) * 2 * rx + 0.3 * Math.sin(g.t * 0.5 + q.sw), cy + (y - 0.5) * 2 * ry, cz + (q.z - 0.5) * 2 * rz + 0.3 * Math.cos(g.t * 0.4 + q.sw));
        Q.setFromAxisAngle(q.ax, q.ph + g.t * q.w * 0.6);
        const s = q.s * (g.k == null ? 1 : g.k) * Math.min(1, Math.min(y, 1 - y) * 12);   // shrink at the ends of the box (no pop)
        M4.compose(p, Q, S3.set(s, s, s)); gems.setMatrixAt(i, M4);
        // a glint: when the stone's spin turns a facet to the light (a sharp peak), brighter in the lamp's beam
        const fl = Math.pow(Math.max(0, Math.sin(q.ph * 3 + g.t * q.w * 2.2)), 24);
        const toL = p.clone().sub(lampP), dl = toL.length(), inBeam = lamp.intensity > 0 ? Math.pow(Math.max(0, toL.normalize().dot(lampD) - 0.8) / 0.2, 1.5) * Math.min(1, 25 / (dl * dl + 1)) : 0;
        const e = fl * (0.7 + 3.0 * inBeam) * (g.glint || 1) * Math.min(1, Math.min(y, 1 - y) * 12);
        gl.set([p.x, p.y, p.z], i * 3); gcol.set([0.8 * e, 0.92 * e, 1.0 * e], i * 3); gsz[i] = s * 14;
      }
      gU.lampP.value.copy(lampP); gU.lampI.value = lamp.intensity; gU.tt.value = g.t;
      gems.instanceMatrix.needsUpdate = true; ['position', 'col', 'size'].forEach(k => glG.attributes[k].needsUpdate = true);
    }
    renderer.render(near, cam);
    return renderer.domElement.toDataURL('image/png');
  };
  window.ready = true;
})();
</script></body></html>`;

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'), '/emblem.js': path.join(TOOLS, 'characters/emblem.js'),
    '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js'), '/fx.js': path.join(TOOLS, 'scenes/survive2/fx.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u] || (u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null);
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error') console.log('console:', m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 300 });
  for (const o of spec.frames) {
    if (o.f % +nw !== +kw) continue;
    const fn = path.join(outDir, `a_${String(o.f).padStart(5, '0')}.png`);
    if (fs.existsSync(fn) && !process.env.FORCE) continue;
    const url = await p.evaluate(o => window.__frame(o), o);
    fs.writeFileSync(fn, Buffer.from(url.split(',')[1], 'base64'));
  }
  await br.close(); srv.close();
})();
