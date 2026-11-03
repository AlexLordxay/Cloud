// «На якій я планеті?» — головоломка №1 (Венера). The in-page half of render.js: survive2's Venus (ground.js, the same
// HDR chain: bloom, ACES) with the astronaut unchanged (characters/astronaut.js), acting the clues: he walks in and looks
// round, looks up and points at the orange sky, looks down at the ground, turns to us and shields his visor from the
// heat, points down to the comments, nods on the countdown, gives a thumbs-up at the answer and waves goodbye.
// Every frame is a pure function of time: window.__frame(t) draws it and returns a JPEG.
(() => {
  const T = THREE, CFG = window.__CFG, W = CFG.W, H = CFG.H;
  const clamp = x => Math.min(1, Math.max(0, x)), smooth = x => { x = clamp(x); return x * x * (3 - 2 * x); };
  const lerp = (a, b, u) => a + (b - a) * u, ramp = (t, a, b) => smooth((t - a) / (b - a));
  const D = Math.PI / 180;
  let seed = 1; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const rs = s => { seed = s; };

  // ---------------- renderer and the post chain ----------------
  const renderer = new T.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  renderer.setSize(W, H); document.body.appendChild(renderer.domElement);
  renderer.outputEncoding = T.LinearEncoding; renderer.toneMapping = T.NoToneMapping; renderer.autoClear = false;
  const RT = (w, h, s = 0) => new T.WebGLRenderTarget(w, h, { type: T.HalfFloatType, samples: s, depthBuffer: s > 0 });
  const rtMain = RT(W, H, 4);
  const LV = 5, mips = [];
  for (let i = 0; i < LV; i++) { const w = Math.max(4, W >> (i + 1)), h = Math.max(4, H >> (i + 1)); mips.push([RT(w, h), RT(w, h)]); }
  const quadCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1), quad = new T.Mesh(new T.PlaneGeometry(2, 2)), quadScene = new T.Scene();
  quad.frustumCulled = false; quadScene.add(quad);
  const VQ = 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';
  const passMat = (frag, uniforms) => new T.ShaderMaterial({ vertexShader: VQ, fragmentShader: frag, uniforms, depthTest: false, depthWrite: false });
  const brightMat = passMat(`uniform sampler2D src; uniform float thr; varying vec2 vUv;
    void main() { vec3 c = texture2D(src, vUv).rgb; float l = max(max(c.r, c.g), c.b); float k = max(l - thr, 0.0); k = k * k / (k + 0.5 * thr + 1e-4);
      gl_FragColor = vec4(c * k / max(l, 1e-4), 1.0); }`, { src: { value: null }, thr: { value: 1.0 } });
  const blurMat = passMat(`uniform sampler2D src; uniform vec2 dir; varying vec2 vUv;
    void main() { vec3 s = texture2D(src, vUv).rgb * 0.2270;
      s += (texture2D(src, vUv + dir * 1.3846).rgb + texture2D(src, vUv - dir * 1.3846).rgb) * 0.3162;
      s += (texture2D(src, vUv + dir * 3.2308).rgb + texture2D(src, vUv - dir * 3.2308).rgb) * 0.0703;
      gl_FragColor = vec4(s, 1.0); }`, { src: { value: null }, dir: { value: new T.Vector2() } });
  const copyMat = passMat('uniform sampler2D src; varying vec2 vUv; void main() { gl_FragColor = vec4(texture2D(src, vUv).rgb, 1.0); }', { src: { value: null } });
  const compU = { src: { value: null }, b0: { value: null }, b1: { value: null }, b2: { value: null }, b3: { value: null }, b4: { value: null },
    bloom: { value: 0.6 }, expo: { value: 1 }, shimmer: { value: 0 }, tt: { value: 0 }, vig: { value: 0.35 }, flash: { value: 0 }, grade: { value: new T.Vector3(1, 1, 1) } };
  const compMat = passMat(`uniform sampler2D src, b0, b1, b2, b3, b4; uniform float bloom, expo, shimmer, tt, vig, flash; uniform vec3 grade; varying vec2 vUv;
    float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    vec3 RRT(vec3 v) { vec3 a = v * (v + 0.0245786) - 0.000090537; vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081; return a / b; }
    vec3 aces(vec3 c) {
      const mat3 I = mat3(vec3(0.59719, 0.07600, 0.02840), vec3(0.35458, 0.90834, 0.13383), vec3(0.04823, 0.01566, 0.83777));
      const mat3 O = mat3(vec3(1.60475, -0.10208, -0.00327), vec3(-0.53108, 1.10813, -0.07276), vec3(-0.07367, -0.00605, 1.07602));
      return clamp(O * RRT(I * c), 0.0, 1.0); }
    void main() {
      vec2 uv = vUv;
      if (shimmer > 0.0) uv += shimmer * vec2(sin(uv.y * 90.0 + tt * 11.0) + 0.5 * sin(uv.y * 210.0 - tt * 17.0 + uv.x * 40.0), cos(uv.x * 70.0 + tt * 9.0)) * 0.0012;
      vec3 c = texture2D(src, uv).rgb;
      vec3 b = texture2D(b0, uv).rgb * 0.30 + texture2D(b1, uv).rgb * 0.26 + texture2D(b2, uv).rgb * 0.2 + texture2D(b3, uv).rgb * 0.14 + texture2D(b4, uv).rgb * 0.10;
      c = (c + b * bloom) * grade * expo;
      c = aces(c / 0.6);
      c = mix(c, vec3(1.0), flash);
      vec2 q = vUv - 0.5; c *= 1.0 - vig * dot(q * vec2(1.0, 0.7), q * vec2(1.0, 0.7)) * 2.0;
      c = pow(c, vec3(1.0 / 2.2));
      c += (h(vUv * 1000.0 + tt) - 0.5) * 0.012;
      gl_FragColor = vec4(c, 1.0); }`, compU);
  function pass(mat, target) { quad.material = mat; renderer.setRenderTarget(target); renderer.render(quadScene, quadCam); }
  function post(o) {
    brightMat.uniforms.src.value = rtMain.texture; brightMat.uniforms.thr.value = o.thr;
    pass(brightMat, mips[0][0]);
    for (let i = 0; i < LV; i++) {
      const [a, b] = mips[i], w = a.width, h = a.height;
      if (i > 0) { copyMat.uniforms.src.value = mips[i - 1][0].texture; pass(copyMat, a); }
      for (let k = 0; k < 2; k++) {
        blurMat.uniforms.src.value = a.texture; blurMat.uniforms.dir.value.set(1 / w, 0); pass(blurMat, b);
        blurMat.uniforms.src.value = b.texture; blurMat.uniforms.dir.value.set(0, 1 / h); pass(blurMat, a);
      }
    }
    compU.src.value = rtMain.texture; for (let i = 0; i < LV; i++) compU['b' + i].value = mips[i][0].texture;
    compU.bloom.value = o.bloom; compU.expo.value = o.expo; compU.shimmer.value = o.shimmer || 0; compU.tt.value = o.t; compU.vig.value = o.vig == null ? 0.35 : o.vig;
    compU.flash.value = o.flash || 0; compU.grade.value.set(...(o.grade || [1, 1, 1]));
    pass(compMat, null);
  }

  // ---------------- the astronaut and his effects ----------------
  const cam = new T.PerspectiveCamera(36, W / H, 0.05, 30000);
  const a = window.__makeAstronaut(T);
  a.group.traverse(o => { o.castShadow = false; o.receiveShadow = false; });
  const holder = new T.Group(); holder.add(a.group);
  const GW = window.__groundWorlds(T, renderer, a, CFG);
  const skyCam = new T.PerspectiveCamera(36, W / H, 1, 5000);

  // ---------------- the beats (seconds; scene.json "beats", the voice is laid on them) ----------------
  const B = CFG.beats;
  // the camera round where he ends up: keys [t, azimuth° from his front, distance, height over the ground, fov, look height]
  function camKeys(K, t) {
    let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++;
    const k0 = K[i], k1 = K[Math.min(i + 1, K.length - 1)];
    let u = k1[0] > k0[0] ? clamp((t - k0[0]) / (k1[0] - k0[0])) : 0; u = u * u * (3 - 2 * u);
    return k0.slice(1).map((v, j) => lerp(v, k1[j + 1], u));
  }
  const CAM = CFG.cam;
  // a gesture's weight: eased in at t0, out at t1
  const env = (t, t0, t1, f = 0.5) => ramp(t, t0, t0 + f) * (1 - ramp(t, t1 - f, t1));

  let Wd = null, walker = null, skyPt = null, sunDir = null;
  async function build() {
    Wd = await GW.build('venus');
    Wd.fog = new T.FogExp2(new T.Color(...Wd.wd.fog[0].map(x => Math.pow(x, 2.2))), Wd.wd.fog[1]); Wd.near.fog = Wd.fog;
    // he walks in toward the camera and stops at the origin: a walk from (0,0), then shifted so it ends there
    const o = { ground: Wd.feet, heading: 0, steps: B.steps, step: 0.7, period: 0.8, start: B.walk, glance: false };
    const w0 = a.walk(Object.assign({}, o, { from: [0, 0] })), e = w0.track(1000);
    walker = a.walk(Object.assign({}, o, { from: [-e[0], -e[1]] }));
    Wd.near.add(holder);
    // where the Sun is: no disc through the clouds, only a dim, wide glow in the haze (a soft sprite far off, unfogged)
    sunDir = Wd.sun.clone().normalize();
    const cv = document.createElement('canvas'); cv.width = cv.height = 256; const g = cv.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(255,236,200,0.75)'); gr.addColorStop(0.25, 'rgba(255,222,165,0.32)'); gr.addColorStop(0.6, 'rgba(255,200,130,0.09)'); gr.addColorStop(1, 'rgba(255,190,120,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    const sp = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(cv), blending: T.AdditiveBlending, depthWrite: false, fog: false, transparent: true, opacity: 0.38 }));
    sp.position.copy(sunDir).multiplyScalar(800); sp.scale.set(620, 620, 1); sp.renderOrder = -1; Wd.near.add(sp);
  }
  const V = (x, y, z) => new T.Vector3(x, y, z);
  function frame(t) {
    const J = a.joints;
    holder.position.set(0, 0, 0); holder.quaternion.identity();
    // --- the figure ---
    let crouch = 0.07 * env(t, B.c2 + 0.6, B.c3 - 0.2, 0.7);            // clue 2: he bends a little to look at the ground
    walker.update(t, { crouch, lean: -0.08 * env(t, B.c2 + 0.6, B.c3 - 0.2, 0.7) });
    a.group.updateMatrixWorld(true);
    const bp = new T.Vector3(); J.body.getWorldPosition(bp);
    // the camera (first: he looks at it)
    const [az, d, h, fov, ly] = camKeys(CAM, t), ang = az * D;
    const cx = -Math.sin(ang) * d, cz = -Math.cos(ang) * d;
    cam.fov = fov; cam.updateProjectionMatrix(); cam.position.set(cx, Wd.G(cx, cz) + h, cz);
    // the hook: walking in, he looks round (left, right) — where am I?
    const lk = env(t, B.hook - 0.2, B.c1 + 0.4, 0.5);
    J.head.rotation.y += lk * 0.6 * Math.sin((t - B.hook) * 2.3); J.head.rotation.x -= lk * 0.08;
    // clue 1: he looks up and points at the orange sky
    if (!skyPt) skyPt = V(0, Wd.G(0, 0) + 1.6, 0).addScaledVector(sunDir, 12);    // he points at the glow
    const k1 = env(t, B.c1 + 0.3, B.c2 + 0.1, 0.7);
    if (k1 > 0) { a.lookAt(skyPt, k1); J.head.rotation.x -= 0.25 * k1; }
    a.gestureAt(t, 'point', { start: B.c1 + 0.6, end: B.c2 - 0.1, fade: 0.6, target: skyPt });
    // clue 2: he looks down at the ground in front of his boots (the pressure: 900 m of water over him)
    const k2 = env(t, B.c2 + 0.2, B.c3 - 0.1, 0.7);
    if (k2 > 0) { J.head.rotation.x += (0.45 - J.head.rotation.x) * k2; J.head.rotation.y += 0.25 * Math.sin((t - B.c2) * 0.9) * k2; }
    // clue 3: the heat — he turns to us, lifts a hand against the glare
    const k3 = env(t, B.c3 + 0.2, B.opts + 0.2, 0.6);
    if (k3 > 0) a.lookAt(cam.position, k3);
    const kh = env(t, B.c3 + 1.4, B.opts, 0.8);
    if (kh > 0) { J.shoulderR.rotation.x += 1.15 * kh; J.shoulderR.rotation.z += 0.15 * kh; J.elbowR.rotation.x += 1.5 * kh; J.wristR.rotation.x += 0.3 * kh; J.head.rotation.x -= 0.1 * kh; J.body.rotation.z += 0.03 * Math.sin(t * 3.1) * kh; }
    // the options, the countdown: he faces us, waits (a small sway); «write in the comments» — he points down
    const kw = env(t, B.opts, B.end + 1, 0.6);
    if (kw > 0) a.lookAt(cam.position, kw * 0.9);
    a.gestureAt(t, 'point', { start: B.write, end: B.n3 + 0.6, fade: 0.5, dir: [0.55, -0.7, -0.45], side: 'R' });
    // the countdown: he stands still and waits, looking at us
    // «Підпишись»: he points up at the subscribe button over him, then lowers his arm
    a.gestureAt(t, 'point', { start: B.sub + 0.1, end: B.sub + 2.3, fade: 0.6, target: V(0.9, Wd.G(0, 0) + 3.3, -2.2) });
    a.group.updateMatrixWorld(true);
    GW.place(Wd, bp.x, bp.z, 1);
    // the camera looks at him (while he walks in, it follows); clue 1 — it goes round behind him, low, and tilts up past
    // his raised hand to the sky and the glow of the Sun
    const tgt = V(bp.x * 0.85, Wd.G(0, 0) + ly, bp.z * 0.85);
    const SK = CFG.sky, ks = SK && t >= SK.t0 && t < SK.t1 ? 1 : 0;        // cuts in and out (a swoop showed empty sky)
    if (ks > 0) {
      // behind him as seen from the Sun, a little to the side of his pointing hand, low; aimed between the hand and the glow
      const sh = V(sunDir.x, 0, sunDir.z).normalize(), sideV = V(-sh.z, 0, sh.x);
      const wl = J.wristL.getWorldPosition(V(0, 0, 0)), wr = J.wristR.getWorldPosition(V(0, 0, 0)), hand = wl.y > wr.y ? wl : wr;
      const sgn = Math.sign(hand.clone().sub(bp).dot(sideV)) || 1;
      const p1 = bp.clone().addScaledVector(sh, -SK.back).addScaledVector(sideV, sgn * SK.side); p1.y = Wd.G(p1.x, p1.z) + SK.h;
      const mx = SK.mix + 0.1 * ramp(t, SK.t0, SK.t1);       // a slow tilt up toward the glow through the shot
      const dir = hand.clone().sub(p1).normalize().multiplyScalar(1 - mx).addScaledVector(sunDir, mx).normalize();
      cam.position.lerp(p1, ks); tgt.lerp(p1.clone().addScaledVector(dir, 10), ks); cam.fov = lerp(cam.fov, SK.fov, ks); cam.updateProjectionMatrix();
    }
    cam.lookAt(tgt);
    Wd.U.glowK.value = 1;
    a.rim.color.value.setRGB(...(Wd.wd.rim || [0.2, 0.25, 0.35])); a.rim.power.value = 4.0;
    // the heat haze: a shimmer over everything, stronger while the heat is the clue
    const shimmer = 0.12 + 0.45 * env(t, B.c3, B.opts + 0.3, 0.8);
    return { thr: 1.6, bloom: 0.45, expo: Wd.wd.expo || 1.0, vig: 0.4, grade: Wd.wd.grade || [1, 1, 1], shimmer };
  }
  window.__frame = async (t) => {
    if (!Wd) await build();
    const o = frame(t);
    renderer.setRenderTarget(rtMain); renderer.setClearColor(0x000000, 1); renderer.clear();
    GW.skyPass(Wd, cam, skyCam, t); renderer.clearDepth();
    renderer.render(Wd.near, cam);
    post(Object.assign({ t }, o));
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  a.ready.then(() => { window.ready = 1; });
})();
