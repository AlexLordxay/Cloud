// "The Nebozvid astronaut dances": the character (characters/astronaut.js) in orbit over the Earth, dancing at
// 120 beats a minute in four parts — a groove (bounce, nodding head, pumping arms), disco (arms swinging up on the
// diagonal in turn), a slow spin with arms spread, and a wave to the camera. Its own scene, rendered in place of the site's.
(() => {
  const D = Math.PI / 180, smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  let S = null;

  window.__sceneSetup = async (r) => {
    const T = r.THREE, scene = new T.Scene(), a = window.__makeAstronaut(T);
    await a.ready;
    scene.add(a.group);
    const sunDir = new T.Vector3(0.7, 0.45, -0.55);
    scene.environment = window.__astronautEnv(T, r.renderer, { warm: sunDir });
    const key = a.light(0xfff1dc, 2.0, sunDir), fill = a.light(0x7fa6e0, 0.7, new T.Vector3(-0.4, -0.7, -0.5));   // the Sun; the blue Earth below
    scene.add(key, key.target, fill, fill.target, new T.HemisphereLight(0x8aa4d8, 0x203048, 0.25));
    a.rim.color.value.setRGB(0.35, 0.45, 0.6);
    // stars
    const n = 4000, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * 6.283, s = Math.sqrt(1 - u * u), R = 400;
      pos.set([R * s * Math.cos(th), R * u, R * s * Math.sin(th)], i * 3);
      const b = 0.35 + Math.pow(Math.random(), 3) * 0.65; col.set([b, b * 0.95, b], i * 3);
    }
    const sg = new T.BufferGeometry(); sg.setAttribute('position', new T.BufferAttribute(pos, 3)); sg.setAttribute('color', new T.BufferAttribute(col, 3));
    scene.add(new T.Points(sg, new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true })));
    // the Earth far below and behind, lit by the same Sun, with its blue rim of air
    const tex = await new Promise(ok => new T.TextureLoader().load('textures/earth_day_2k.jpg', t => { t.encoding = T.sRGBEncoding; ok(t); }));
    const earth = new T.Mesh(new T.SphereGeometry(60, 128, 96), new T.MeshStandardMaterial({ map: tex, roughness: 1, metalness: 0 }));
    earth.position.set(10, -78, 55); earth.rotation.set(0.3, 2.2, 0); scene.add(earth);
    const sun = new T.DirectionalLight(0xffffff, 2.2); sun.position.copy(sunDir).multiplyScalar(100); scene.add(sun);   // lights the Earth (no shadows)
    const atm = new T.Mesh(new T.SphereGeometry(62.2, 96, 64), new T.ShaderMaterial({
      uniforms: { c: { value: new T.Color(0.35, 0.6, 1.0) } }, transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.BackSide,
      vertexShader: 'varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.0); vP = mv.xyz; gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'uniform vec3 c; varying vec3 vN; varying vec3 vP; void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(-vP))), 1.5); gl_FragColor = vec4(c, f * 0.9); }',
    }));
    atm.position.copy(earth.position); scene.add(atm);
    const cam = new T.PerspectiveCamera(32, 720 / 1280, 0.05, 1000);
    S = { T, scene, a, cam, earth };
  };

  // ---- the dance: each part gives the joint angles at time t; parts cross-fade over 0.3 s ----
  const beatOf = t => t * 2;                                 // 120 bpm
  const bounce = t => 0.5 - 0.5 * Math.cos(2 * Math.PI * beatOf(t));   // a soft, round bounce each beat (no kink)
  function groove(t) {
    const bo = bounce(t), sw = Math.sin(Math.PI * beatOf(t) / 2);
    return { bodyY: -0.035 * bo, body: [0.05, 0, 0.1 * sw], head: [0.18 * bo - 0.08, 0.15 * sw, 0],
      shL: [0.55, 0, -0.55], shR: [0.55, 0, 0.55], elL: [1.25 + 0.35 * bo, 0, 0], elR: [1.25 + 0.35 * (1 - bo), 0, 0],
      hipL: [0.25 + 0.15 * bo, 0, -0.12], hipR: [0.25 + 0.15 * bo, 0, 0.12], knL: [-0.4 - 0.35 * bo, 0, 0], knR: [-0.4 - 0.35 * bo, 0, 0] };
  }
  function disco(t) {
    const up = 0.5 - 0.5 * Math.cos(Math.PI * beatOf(t));   // a smooth swing: right arm up, then left, over two beats
    const bo = bounce(t);
    return { bodyY: -0.025 * bo, body: [0.02, 0.15 * (up - 0.5), 0.12 * (0.5 - up)], head: [0.1 * bo - 0.1, 0.3 * (up - 0.5), 0],
      shR: [0.2 + 0.4 * (1 - up), 0, 0.35 + 2.15 * up], elR: [0.25 + 0.6 * (1 - up), 0, 0],
      shL: [0.2 + 0.4 * up, 0, -0.35 - 2.15 * (1 - up)], elL: [0.25 + 0.6 * up, 0, 0],
      hipL: [0.15 + 0.2 * up, 0, -0.1], hipR: [0.15 + 0.2 * (1 - up), 0, 0.1], knL: [-0.25 - 0.5 * up, 0, 0], knR: [-0.25 - 0.5 * (1 - up), 0, 0] };
  }
  function spin(t) {
    const bo = bounce(t);
    return { bodyY: -0.02 * bo, body: [0.05, 0, 0.06 * Math.sin(Math.PI * beatOf(t) / 2)], head: [-0.1, 0, 0],
      shL: [0.1, 0, -1.45 - 0.1 * bo], shR: [0.1, 0, 1.45 + 0.1 * bo], elL: [0.2, 0, 0], elR: [0.2, 0, 0],
      hipL: [0.2, 0, -0.06], hipR: [0.45, 0, 0.06], knL: [-0.35, 0, 0], knR: [-0.9, 0, 0] };
  }
  function wave(t) {
    const w = Math.sin(2 * Math.PI * 1.6 * t);
    return { bodyY: 0, body: [0.0, 0.0, -0.08], head: [-0.05, 0, 0.12],
      shR: [0.5, 0, 1.95], elR: [0.55 + 0.45 * w, 0, 0], shL: [0.35, 0, -0.55], elL: [1.7, 0, 0],
      hipL: [0.15, 0, -0.08], hipR: [0.3, 0, 0.1], knL: [-0.3, 0, 0], knR: [-0.55, 0, 0] };
  }
  const PARTS = [[0, groove], [2.0, disco], [4.0, spin], [6.0, wave]];
  function poseAt(t) {
    let i = 0; while (i < PARTS.length - 1 && t >= PARTS[i + 1][0]) i++;
    const cur = PARTS[i][1](t), nxt = i < PARTS.length - 1 ? PARTS[i + 1][1](t) : null, k = nxt ? smooth((t - PARTS[i + 1][0] + 0.7) / 0.7) : 0;
    if (!nxt || k <= 0) return cur;
    const out = {};
    for (const key in cur) out[key] = Array.isArray(cur[key]) ? cur[key].map((v, j) => v + (nxt[key][j] - v) * k) : cur[key] + (nxt[key] - cur[key]) * k;
    return out;
  }

  window.__recCam = () => {};
  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer;
    if (!S) { ren.render(r.scene, r.camera); return; }
    const { T, scene, a, cam, earth } = S, t = window.__vt() - (window.__t0 || 0), J = a.joints;
    a.pose(t * 0.5);                                         // the idle under it (wrists, ankles drift)
    const p = poseAt(t);
    J.body.position.y = p.bodyY; J.body.rotation.set(...p.body); J.head.rotation.set(...p.head);
    J.shoulderL.rotation.set(...p.shL); J.shoulderR.rotation.set(...p.shR); J.elbowL.rotation.set(...p.elL); J.elbowR.rotation.set(...p.elR);
    J.hipL.rotation.set(...p.hipL); J.hipR.rotation.set(...p.hipR); J.kneeL.rotation.set(...p.knL); J.kneeR.rotation.set(...p.knR);
    // the whole figure: faces the camera, floats a little, turns once round during the spin
    a.group.rotation.set(0, 0.25 * Math.sin(t * 0.6) + 2 * Math.PI * smooth((t - 4.0) / 2.0), 0);
    a.group.position.set(0.04 * Math.sin(t * 0.9), 0.03 * Math.sin(t * 1.3), 0);
    a.aim();
    earth.rotation.y = 2.2 + t * 0.01;
    cam.position.set(0.55 - 0.15 * t / 7.5, 0.3, -5.6 + 0.25 * t / 7.5); cam.lookAt(0, 0.12, 0);
    const tm = ren.toneMapping, te = ren.toneMappingExposure, sm = ren.shadowMap.enabled, st = ren.shadowMap.type;
    ren.toneMapping = T.ACESFilmicToneMapping; ren.toneMappingExposure = 0.95; ren.shadowMap.enabled = true; ren.shadowMap.type = T.PCFSoftShadowMap;
    ren.setRenderTarget(null); ren.render(scene, cam);
    ren.toneMapping = tm; ren.toneMappingExposure = te; ren.shadowMap.enabled = sm; ren.shadowMap.type = st;
  };
})();
