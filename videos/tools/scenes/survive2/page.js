// «Скільки ти протримаєшся на кожній планеті?» v2 — the in-page half of render.js: the worlds where he does not make it,
// and how he goes. The figure is characters/astronaut.js, unchanged; fx.js lays the heat, char, melt and frost over it.
// Every frame is a pure function of time: window.__frame(t) draws it and returns a JPEG.
//
// The picture is rendered in linear light into a float target (4× MSAA), then bloomed (a mip chain of blurred highlights)
// and tone-mapped (ACES) here, so fire and plasma glow like light rather than paint.
//
// Worlds so far (the test shots, 2.11.2026):
//   sun     — falling toward the photosphere (granulation, a prominence behind): the suit heats from the boots up, chars
//             black with glowing cracks, flames lick up the burning band, and it comes apart into sparks carried up.
//   neptune — falling through the cloud tops in a 2 000 km/h wind (streaks of ice, wisps rushing past): frost grows from
//             his fingers and boots, he curls up and stops moving, the ice crust on his visor cracks and bursts off, and a
//             gust tumbles him away into the clouds.
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
  // the visor keeps its gold under the frost (the ice there is the crust of shards, below), so mark it to skip the frost
  a.group.traverse(o => { const m = o.material; if (m && m.isMeshPhysicalMaterial && m.metalness === 1 && m.clearcoat === 1 && m.envMapIntensity === 1.4) m.userData.visor = true; });
  const fx = window.__astroFX(T, a);
  a.group.traverse(o => { const m = o.material; if (m && m.userData && m.userData.visor) { const p = m.onBeforeCompile; m.onBeforeCompile = (sh, r) => { p(sh, r); sh.fragmentShader = sh.fragmentShader.replace('fxFrostK = smoothstep', 'fxFrostK = 0.0 * smoothstep'); }; m.customProgramCacheKey = () => 'astroFX-visor'; } });

  // points drawn with a shader: per point position, colour (linear, may exceed 1), size (m) and a kind/seed
  function pointCloud(n, frag, blending = T.AdditiveBlending) {
    const g = new T.BufferGeometry();
    const P = new Float32Array(n * 3), C = new Float32Array(n * 3), S = new Float32Array(n), K = new Float32Array(n);
    g.setAttribute('position', new T.BufferAttribute(P, 3)); g.setAttribute('col', new T.BufferAttribute(C, 3));
    g.setAttribute('size', new T.BufferAttribute(S, 1)); g.setAttribute('seed', new T.BufferAttribute(K, 1));
    const m = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending, uniforms: { vh: { value: H }, tt: { value: 0 } },
      vertexShader: `attribute vec3 col; attribute float size, seed; uniform float vh; varying vec3 vC; varying float vS;
        void main() { vC = col; vS = seed; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
          gl_PointSize = size > 0.0 ? max(1.5, size * projectionMatrix[1][1] * vh * 0.5 / -mv.z) : 0.0; }`,
      fragmentShader: `uniform float tt; varying vec3 vC; varying float vS;
        float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
        ${frag}` });
    const pts = new T.Points(g, m); pts.frustumCulled = false; pts.renderOrder = 5;
    return { pts, P, C, S, K, g, n, set(i, x, y, z, r, gg, b, s) { P[i * 3] = x; P[i * 3 + 1] = y; P[i * 3 + 2] = z; C[i * 3] = r; C[i * 3 + 1] = gg; C[i * 3 + 2] = b; S[i] = s; },
      done() { for (const k of ['position', 'col', 'size']) g.attributes[k].needsUpdate = true; } };
  }
  const SPARK_FRAG = `void main() { vec2 q = gl_PointCoord * 2.0 - 1.0; float r = dot(q, q); if (r > 1.0) discard;
    float a = exp(-r * 4.5) + 0.35 * exp(-r * 40.0); gl_FragColor = vec4(vC * a, 1.0); }`;
  // a flame tongue: narrow at the top, licking, a hot core
  const FLAME_FRAG = `void main() { vec2 q = gl_PointCoord * 2.0 - 1.0; q.y = -q.y;
    float y = q.y * 0.5 + 0.5;
    float n = n2(vec2(q.x * 3.0 + vS * 17.0, q.y * 2.5 - tt * 5.0 - vS * 9.0)), n1 = n2(vec2(q.x * 7.0 - vS * 5.0, q.y * 6.0 - tt * 9.0));
    float x = q.x + 0.35 * (n - 0.5) * y + 0.12 * (n1 - 0.5);
    float w = 0.55 * pow(1.0 - y, 0.8) * (0.75 + 0.5 * n) + 0.02;
    float d = smoothstep(w, w * 0.25, abs(x)) * smoothstep(0.0, 0.18, y) * (1.0 - smoothstep(0.55, 1.0, y + 0.25 * (n1 - 0.5)));
    float core = smoothstep(w * 0.55, 0.0, abs(x)) * (1.0 - smoothstep(0.1, 0.55, y));
    vec3 c = vC * d * (0.55 + 1.3 * core);
    gl_FragColor = vec4(c, 1.0); }`;
  const FLAKE_FRAG = `void main() { vec2 q = gl_PointCoord * 2.0 - 1.0; float r = max(abs(q.x * 1.3 + q.y * 0.4), abs(q.y)); if (r > 1.0 - 0.3 * n2(q * 3.0 + vS * 20.0)) discard;
    gl_FragColor = vec4(vC, 1.0); }`;

  // ---------------- skies, grounds of light ----------------
  const skyMat = (frag, U) => new T.ShaderMaterial({ side: T.BackSide, depthWrite: false, uniforms: U,
    vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `varying vec3 vD;
      float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
      float fb(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * n2(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return s; }
      ${frag}` });
  const NOISE2 = `float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
      float fb(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 6; i++) { s += a * n2(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return s; }`;
  const planeMat = (frag, U, opts = {}) => new T.ShaderMaterial(Object.assign({ uniforms: U, depthWrite: false,
    vertexShader: 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: `varying vec3 vW; ${NOISE2} ${frag}` }, opts));
  function envFrom(mat) {        // a PMREM of a sky material, for the reflections in the visor and the metal
    const sc = new T.Scene(); sc.add(new T.Mesh(new T.SphereGeometry(10, 64, 32), mat));
    const pm = new T.PMREMGenerator(renderer); const e = pm.fromScene(sc, 0.02).texture; pm.dispose(); return e;
  }

  // ======================= THE SUN =======================
  function buildSun() {
    const sc = new T.Scene(), U = { tt: { value: 0 }, fall: { value: 0 } };
    // the sky: the glow of the chromosphere along the horizon, dark red overhead with faint streamers of the corona
    const sky = new T.Mesh(new T.SphereGeometry(20000, 64, 32), skyMat(`uniform float tt;
      void main() { vec3 d = normalize(vD); float up = max(d.y, 0.0);
        float az = atan(d.x, -d.z);
        vec3 c = mix(vec3(1.35, 0.42, 0.06), vec3(0.07, 0.008, 0.002), pow(smoothstep(0.0, 0.42, up), 0.55));
        c = mix(c, vec3(0.012, 0.003, 0.002), smoothstep(0.2, 0.8, up));
        float ray = fb(vec2(az * 9.0, up * 2.0 - tt * 0.02)); c += vec3(0.5, 0.12, 0.03) * pow(ray, 3.0) * (1.0 - up) * 0.8;
        if (d.y < 0.0) c = vec3(1.35, 0.42, 0.06);
        gl_FragColor = vec4(c, 1.0); }`, U));
    sc.add(sky);
    // the photosphere: boiling granules (bright cells, dark lanes), seen to the haze of the horizon
    const ph = new T.Mesh(new T.PlaneGeometry(120000, 120000), planeMat(`uniform float tt, fall;
      vec3 cell(vec2 q, float t) { vec2 g = floor(q), f = fract(q); float d1 = 9.0, d2 = 9.0, id = 0.0;
        for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) { vec2 o = vec2(float(i), float(j));
          vec2 r = o + vec2(h(g + o), h(g + o + 7.3)) * 0.8 + 0.1 + 0.12 * sin(t * 0.6 + 6.0 * h(g + o + 3.1)) - f; float dd = dot(r, r);
          if (dd < d1) { d2 = d1; d1 = dd; id = h(g + o + 1.9); } else if (dd < d2) d2 = dd; }
        return vec3(sqrt(d1), sqrt(d2), id); }
      void main() {
        vec2 p = vW.xz;
        float w = fb(p / 400.0), w2 = fb(p / 90.0 + 3.0);
        vec3 c1 = cell(p / 30.0 + vec2(w * 2.0, w2), tt);
        float dist = length(cameraPosition.xz - vW.xz), blur = smoothstep(300.0, 2500.0, dist);
        float lane = smoothstep(0.0, 0.22 + 0.4 * blur, c1.y - c1.x);         // the dark lanes between granules (soft, softer far off)
        float dome = 1.0 - smoothstep(0.0, 1.1, c1.x);                       // each granule brightest in its middle
        float I = mix(lane * (0.45 + 0.55 * dome) * (0.65 + 0.5 * c1.z), 0.62, blur * 0.7) * (0.7 + 0.6 * w) * (0.88 + 0.24 * fb(p / 8.0 + tt * 0.2));
        vec3 col = mix(vec3(0.45, 0.04, 0.0), vec3(1.0, 0.3, 0.03), smoothstep(0.1, 0.55, I));
        col = mix(col, vec3(1.0, 0.6, 0.18), smoothstep(0.6, 1.05, I));
        col *= 0.35 + 1.35 * I;
        col = mix(col, vec3(1.35, 0.42, 0.06), 1.0 - exp(-dist / 3500.0));
        gl_FragColor = vec4(col, 1.0); }`, U));
    ph.rotation.x = -Math.PI / 2; ph.position.y = -320; sc.add(ph);
    // a prominence: a looped arch of glowing filaments rising from the horizon behind him, and a smaller one
    const promMat = new T.ShaderMaterial({ uniforms: U, transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
      vertexShader: 'varying vec2 vUv; varying vec3 vN, vV; void main() { vUv = uv; vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = -mv.xyz; gl_Position = projectionMatrix * mv; }',
      fragmentShader: `uniform float tt; varying vec2 vUv; varying vec3 vN, vV; ${NOISE2}
        void main() { float rim = abs(dot(normalize(vN), normalize(vV)));
          float f = fb(vec2(vUv.x * 60.0 - tt * 0.15, vUv.y * 4.0 + vUv.x * 9.0)), g = fb(vec2(vUv.x * 160.0 + tt * 0.3, vUv.y * 9.0));
          float strands = pow(smoothstep(0.35, 0.85, f), 2.0) * 2.0 + pow(smoothstep(0.45, 0.9, g), 2.0) * 1.5;
          float a = strands * (0.35 + 0.65 * (1.0 - rim)) * smoothstep(0.0, 0.08, vUv.x) * smoothstep(1.0, 0.92, vUv.x);
          gl_FragColor = vec4(mix(vec3(1.0, 0.12, 0.02), vec3(1.0, 0.45, 0.08), strands * 0.3) * a * 1.3, 1.0); }` });
    const prom = new T.Mesh(new T.TorusGeometry(170, 26, 24, 200, Math.PI), promMat); prom.position.set(-170, -60, -1500); prom.rotation.y = 0.35; sc.add(prom);
    const prom2 = new T.Mesh(new T.TorusGeometry(90, 12, 16, 120, Math.PI), promMat); prom2.position.set(420, -60, -1900); prom2.rotation.y = -0.6; sc.add(prom2);
    // light on him: the photosphere below (strong, warm), the glow of the sky, a little from our side for the shapes
    const below = new T.DirectionalLight(new T.Color(1, 0.55, 0.22), 3.2); below.position.set(0.25, -1, -0.35); sc.add(below, below.target);
    const front = new T.DirectionalLight(new T.Color(1, 0.75, 0.5), 0.9); front.position.set(1, 0.6, 1.6); sc.add(front, front.target);
    sc.add(new T.HemisphereLight(new T.Color(0.5, 0.12, 0.03), new T.Color(0.9, 0.4, 0.12), 0.7));
    sc.environment = envFrom(skyMat(`void main() { vec3 d = normalize(vD); vec3 c = mix(vec3(1.6, 0.6, 0.14), vec3(0.12, 0.025, 0.006), smoothstep(-0.2, 0.6, d.y)); gl_FragColor = vec4(c, 1.0); }`, {}));
    sc.add(a.group);

    // the sparks: points on his surface (at the pose of the burn), each let go when the melt front passes it; a share
    // leaves earlier, when the char passes, as dark flakes with glowing edges
    poseSun(2.6);
    const NS = 3800, src = fx.samplePoints(NS, 3);
    rs(77);
    const sparks = src.map(p => ({ p, b: fx.burnCoord(p), j: (rnd() - 0.5) * 0.06, flake: rnd() < 0.28, life: 0.9 + 2.4 * rnd(), ph: rnd() * 6.28, sw: 0.4 + 1.2 * rnd(), out: 0.1 + 0.9 * rnd(), up: 0.2 + 1.2 * rnd() * rnd(), acc: 0.1 + 0.7 * rnd() }));
    const cloud = pointCloud(NS, SPARK_FRAG), flakes = pointCloud(NS, FLAKE_FRAG, T.NormalBlending);
    sc.add(cloud.pts, flakes.pts);
    // the flames: emitters on the surface, each puffing a tongue every ~0.6 s while its spot is in the burning band
    const NF = 1600, fsrc = fx.samplePoints(NF, 9);
    rs(5);
    const flames = fsrc.map(p => ({ p, b: fx.burnCoord(p), per: 0.3 + 0.35 * rnd(), ph: rnd(), s: 0.05 + 0.09 * rnd(), k: rnd() }));
    const fl = pointCloud(NF, FLAME_FRAG); sc.add(fl.pts);
    // plasma motes rising past him all the time (the updraft)
    const NM = 900; rs(31);
    const motes = Array.from({ length: NM }, () => ({ x: (rnd() - 0.5) * 14, y: rnd() * 20, z: (rnd() - 0.5) * 14 - 2, v: 1.5 + 3 * rnd(), s: 0.01 + 0.03 * rnd() }));
    const mo = pointCloud(NM, SPARK_FRAG); sc.add(mo.pts);
    return { sc, U, sparks, cloud, flakes, flames, fl, motes, mo };
  }
  // the Sun's timeline (s from the start of the shot)
  const SUN = {
    heat: t => ramp(t, 0.1, 1.3),
    char: t => -0.35 + 1.75 * Math.pow(clamp((t - 0.5) / 2.1), 1.2),
    melt: t => t < 1.45 ? -1 : -0.35 + 1.75 * Math.pow(clamp((t - 1.45) / 2.0), 1.1),
  };
  function poseSun(t) {
    a.group.position.set(0, 0, 0); a.group.rotation.set(0, Math.PI + 0.45, 0);
    a.pose(t);
    const J = a.joints, k = ramp(t, 0.6, 1.5);
    for (const sd of ['L', 'R']) { const s = sd === 'L' ? -1 : 1;
      const sh = J['shoulder' + sd].rotation, el = J['elbow' + sd].rotation;
      sh.x = lerp(sh.x, 1.25, k); sh.y = lerp(sh.y, 0.75 * s, k); sh.z = lerp(sh.z, s * 0.12, k); el.x = lerp(el.x, 2.05, k);
      J['hip' + sd].rotation.x += 0.35 * k; J['knee' + sd].rotation.x -= 0.4 * k; }
    J.head.rotation.x -= 0.25 * k; J.body.rotation.x += 0.12 * k;
    a.group.updateMatrixWorld(true);
  }
  const firstT = (f, b, t0, t1) => { if (f(t1) < b) return Infinity; let lo = t0, hi = t1; for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; if (f(m) >= b) hi = m; else lo = m; } return hi; };
  function frameSun(S, t) {
    S.U.tt.value = t;
    const heat = SUN.heat(t), ch = SUN.char(t), me = SUN.melt(t);
    fx.U.uHeat.value = heat; fx.U.uChar.value = ch; fx.U.uMelt.value = me; fx.U.uFrost.value = 0; fx.U.uTime.value = t;
    // the figure: the free-fall idle, then the arms come up to shield the visor and he curls a little
    poseSun(t); fx.update();
    // sparks
    const melt = SUN.melt, charF = SUN.char;
    S.sparks.forEach((q, i) => {
      if (q.tr === undefined) q.tr = q.flake ? firstT(charF, q.b + q.j + 0.06, 0.5, 2.7) : firstT(melt, q.b + q.j, 1.45, 3.5);
      const dt = t - q.tr;
      if (!(dt >= 0) || dt > q.life) { S.cloud.set(i, 0, 0, 0, 0, 0, 0, 0); S.flakes.set(i, 0, 0, 0, 0, 0, 0, 0); return; }
      const p = q.p, r = Math.hypot(p.x, p.z) + 1e-3, u = dt / q.life;
      const x = p.x + (p.x / r) * q.out * dt + 0.45 * q.sw * Math.sin(q.ph + dt * 2.1) * dt;
      const y = p.y + q.up * dt + q.acc * dt * dt + 0.08 * Math.sin(q.ph * 3 + dt * 5);
      const z = p.z + (p.z / r) * q.out * dt + 0.45 * q.sw * Math.cos(q.ph + dt * 1.7) * dt;
      const wv = new T.Vector3(x, y, z).applyMatrix4(a.group.matrixWorld);
      if (q.flake) {
        const e = (1 - u) * (0.5 + 0.5 * Math.sin(q.ph * 7 + t * 14));
        S.flakes.set(i, wv.x, wv.y, wv.z, 0.02 + 2.5 * e, 0.012 + 0.6 * e, 0.01 + 0.08 * e, 0.016 * (1 - 0.5 * u));
        S.cloud.set(i, 0, 0, 0, 0, 0, 0, 0);
      } else {
        const T0 = 1 - u, c = Math.pow(T0, 1.5);
        const fl2 = 0.75 + 0.25 * Math.sin(q.ph * 11 + t * 23); S.cloud.set(i, wv.x, wv.y, wv.z, (3.0 * c + 0.45 * T0) * fl2, (0.85 * c * c + 0.04 * T0) * fl2, 0.1 * c * c * c, 0.02 * (0.45 + 0.55 * T0));
        S.flakes.set(i, 0, 0, 0, 0, 0, 0, 0);
      }
    });
    S.cloud.done(); S.flakes.done();
    // flames in the burning band (between the melt and a little above the char front)
    const lo = me > -0.9 ? me : -1, hi = ch + 0.05;
    S.flames.forEach((f, i) => {
      const life = ((t / f.per + f.ph) % 1 + 1) % 1, born = t - life * f.per;
      const inBand = b => b > (melt(born) > -0.9 ? melt(born) : -1) && b < charF(born) + 0.05;
      if (!inBand(f.b) || f.b < lo) { S.fl.set(i, 0, 0, 0, 0, 0, 0, 0); return; }
      const p = f.p, rise = 0.22 * life + 0.12 * life * life;
      const wv = new T.Vector3(p.x + 0.04 * Math.sin(f.k * 20 + t * 6), p.y + rise, p.z).applyMatrix4(a.group.matrixWorld);
      const env = Math.sin(Math.PI * Math.pow(life, 0.7)), I = env * (0.9 + 0.6 * heat) * (hi > f.b ? 1 : 0);
      S.fl.set(i, wv.x, wv.y, wv.z, 1.15 * I, 0.32 * I, 0.045 * I, f.s * (0.6 + 0.8 * life));
      S.fl.K[i] = f.k;
    });
    S.fl.g.attributes.seed.needsUpdate = true; S.fl.done(); S.fl.pts.material.uniforms.tt.value = t;
    // motes
    S.motes.forEach((m, i) => { const y = ((m.y + m.v * t) % 20) - 8; S.mo.set(i, m.x + 0.3 * Math.sin(t + i), y, m.z, 1.2, 0.35, 0.06, m.s); });
    S.mo.done();
    // the camera: close, a little above and to the side, pushing in; at the end it tilts up after the sparks
    const push = ramp(t, 0, 3.6), up = ramp(t, 2.8, 5.0);
    cam.fov = 38; cam.updateProjectionMatrix();
    cam.position.set(lerp(1.1, 0.9, push), lerp(0.1, 0.0, push) + 0.3 * up, lerp(4.6, 3.9, push));
    cam.lookAt(0, lerp(0.15, 0.1, push) + 0.9 * up, 0);
    a.rim.color.value.setRGB(1.0, 0.45, 0.12); a.rim.power.value = 3.0;
    return { thr: 1.5, bloom: 0.8, expo: 0.8, shimmer: 0.6 + 0.8 * heat, grade: [1.0, 0.96, 0.9], vig: 0.6 };
  }

  // ======================= NEPTUNE =======================
  const WIND = new T.Vector3(1, 0.04, -0.25).normalize();
  function buildNeptune() {
    const sc = new T.Scene(), U = { tt: { value: 0 }, gust: { value: 0 } };
    const sunD = new T.Vector3(-0.55, 0.4, 0.73).normalize();
    // the sky: pale cyan haze at the horizon, deep blue overhead, the Sun a hard little star
    const sky = new T.Mesh(new T.SphereGeometry(20000, 64, 32), skyMat(`uniform float tt; uniform vec3 sd;
      void main() { vec3 d = normalize(vD); float up = max(d.y, 0.0), m = max(dot(d, sd), 0.0);
        vec3 c = mix(vec3(0.2, 0.42, 0.85), vec3(0.015, 0.035, 0.16), pow(smoothstep(0.0, 0.5, up), 0.6));
        c = mix(c, vec3(0.005, 0.012, 0.05), smoothstep(0.45, 1.0, up));
        c += vec3(1.0, 0.97, 0.9) * (pow(m, 40000.0) * 60.0 + pow(m, 2000.0) * 2.0 + pow(m, 80.0) * 0.08);
        if (d.y < 0.0) c = vec3(0.12, 0.28, 0.7);
        gl_FragColor = vec4(c, 1.0); }`, Object.assign({ sd: { value: sunD } }, U)));
    sc.add(sky);
    // the cloud deck far below: blue with white bands and bright methane-ice streaks, all racing with the wind
    const deck = new T.Mesh(new T.PlaneGeometry(60000, 60000), planeMat(`uniform float tt;
      void main() { vec2 p = vW.xz; vec2 q = vec2(p.x / 900.0 - tt * 0.05, p.y / 160.0);
        float w = fb(q + vec2(fb(q * 0.5) * 1.5, 0.0)), band = 0.5 + 0.5 * sin(p.y / 420.0 + 2.5 * fb(q * 0.3));
        float streak = smoothstep(0.6, 0.85, fb(vec2(p.x / 2600.0 - tt * 0.09, p.y / 60.0)));
        vec3 col = mix(vec3(0.02, 0.07, 0.3), vec3(0.12, 0.3, 0.75), w) * (0.7 + 0.4 * band) + vec3(0.75, 0.85, 1.0) * streak * 0.8;
        float dist = length(cameraPosition.xz - vW.xz);
        col = mix(col, vec3(0.2, 0.42, 0.85), 1.0 - exp(-dist / 5000.0));
        gl_FragColor = vec4(col, 1.0); }`, U));
    deck.rotation.x = -Math.PI / 2; deck.position.y = -140; sc.add(deck);
    // wisps near him: thin streaky layers rushing past (one below, one above), transparent
    const wispMat = (k, sp) => planeMat(`uniform float tt, gust;
      void main() { vec2 p = vW.xz; vec2 q = vec2(p.x / 70.0 - tt * ${sp.toFixed(3)} * (1.0 + 0.6 * gust), p.y / 6.0);
        float w = fb(q + vec2(0.0, fb(q * 0.7) * 0.6)); float a = smoothstep(0.58, 0.85, w) * ${k.toFixed(3)};
        float dist = length(cameraPosition - vW); a *= exp(-dist / 600.0) * smoothstep(2.0, 12.0, dist);
        gl_FragColor = vec4(vec3(0.7, 0.82, 1.0) * 0.9, a); }`, U, { transparent: true, side: T.DoubleSide });
    const w1 = new T.Mesh(new T.PlaneGeometry(4000, 4000), wispMat(0.45, 0.55)); w1.rotation.x = -Math.PI / 2; w1.position.y = -9; sc.add(w1);
    const w2 = new T.Mesh(new T.PlaneGeometry(4000, 4000), wispMat(0.25, 0.7)); w2.rotation.x = -Math.PI / 2; w2.position.y = 16; sc.add(w2);
    // light: the far Sun (dim at 30 AU — lifted for the eye), the blue of the sky and the clouds
    const key = new T.DirectionalLight(new T.Color(1, 0.97, 0.92), 1.8); key.position.copy(sunD).multiplyScalar(10); sc.add(key, key.target);
    sc.add(new T.HemisphereLight(new T.Color(0.25, 0.42, 0.9), new T.Color(0.15, 0.35, 0.85), 0.9));
    sc.environment = envFrom(skyMat(`void main() { vec3 d = normalize(vD); vec3 c = mix(vec3(0.15, 0.32, 0.8), vec3(0.02, 0.05, 0.2), smoothstep(-0.3, 0.8, d.y)); gl_FragColor = vec4(c, 1.0); }`, {}));
    sc.add(a.group);

    // the ice crust on the visor: a shell of shards over the glass, frosted by a drawn texture (crystals growing in
    // from the rim), cracked along the shard edges, then bursting off with the wind
    const V = a.visor, R = V.r + 0.0045, NP = 7, NT = 6; rs(13);
    const grid = []; for (let i = 0; i <= NP; i++) { grid.push([]); for (let j = 0; j <= NT; j++) {
      const edge = i === 0 || i === NP || j === 0 || j === NT, ju = edge ? 0 : (rnd() - 0.5) * 0.6, jv = edge ? 0 : (rnd() - 0.5) * 0.6;
      grid[i].push([(i + ju) / NP, (j + jv) / NT]); } }
    const sp = (u, v) => { const ph = V.P0 - 0.03 + (V.PL + 0.06) * u, th = V.T0 - 0.03 + (V.TL + 0.06) * v;
      return new T.Vector3(-R * Math.cos(ph) * Math.sin(th), R * Math.cos(th), R * Math.sin(ph) * Math.sin(th)).multiply(V.scale).add(V.center); };
    const fcv = document.createElement('canvas'); fcv.width = fcv.height = 512; const fg = fcv.getContext('2d');
    const frostTex = new T.CanvasTexture(fcv); frostTex.encoding = T.sRGBEncoding;
    const shardMat = new T.MeshStandardMaterial({ map: frostTex, transparent: true, roughness: 0.35, metalness: 0, side: T.DoubleSide, depthWrite: false, color: 0xffffff });
    const shards = [];
    for (let i = 0; i < NP; i++) for (let j = 0; j < NT; j++) {
      const c = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]];
      for (const tri of [[0, 1, 2], [0, 2, 3]]) {
        const uvs = tri.map(k => c[k]), pts = uvs.map(([u, v]) => sp(u, v));
        const cen = pts[0].clone().add(pts[1]).add(pts[2]).divideScalar(3);
        const g = new T.BufferGeometry(), pos = [], uv = [];
        // a thin wedge: the outer face and a slightly smaller inner face (so it reads as a chunk when it tumbles)
        const outN = cen.clone().sub(V.center).normalize();
        pts.forEach((p, k) => { const q = p.clone().sub(cen); pos.push(q.x, q.y, q.z); uv.push(uvs[k][0], 1 - uvs[k][1]); });
        pts.forEach((p, k) => { const q = p.clone().sub(cen).multiplyScalar(0.85).addScaledVector(outN, -0.006); pos.push(q.x, q.y, q.z); uv.push(uvs[k][0], 1 - uvs[k][1]); });
        g.setAttribute('position', new T.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
        g.setIndex([0, 1, 2, 3, 5, 4, 0, 3, 4, 0, 4, 1, 1, 4, 5, 1, 5, 2, 2, 5, 3, 2, 3, 0]); g.computeVertexNormals();
        const m = new T.Mesh(g, shardMat); m.matrixAutoUpdate = false; m.renderOrder = 4; sc.add(m);
        shards.push({ m, local: new T.Matrix4().makeTranslation(cen.x, cen.y, cen.z), out: outN, uvs, spin: new T.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize(), w: 6 + 14 * rnd(), v: 0.6 + 0.8 * rnd(), d: rnd() });
      }
    }
    // the frost drawing: feathery dendrites growing inward from the rim, then a white crust; cracks along the shard
    // edges (drawn over it as they spread)
    rs(21); const dend = Array.from({ length: 140 }, () => { const e = Math.floor(rnd() * 4), s = rnd();
      const [x0, y0, ang] = e === 0 ? [s, 0, Math.PI / 2] : e === 1 ? [1, s, Math.PI] : e === 2 ? [s, 1, -Math.PI / 2] : [0, s, 0];
      return { x0: x0 * 512, y0: y0 * 512, a: ang + (rnd() - 0.5) * 1.1, L: 90 + 230 * rnd(), w: 0.8 + 1.8 * rnd(), seed: Math.floor(rnd() * 1e6) }; });
    const edges = []; for (let i = 0; i < NP; i++) for (let j = 0; j < NT; j++) {
      const c = [grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]];
      edges.push([c[0], c[2]]); if (i < NP - 1) edges.push([c[1], c[2]]); if (j < NT - 1) edges.push([c[2], c[3]]); }
    edges.forEach(e => { const mx = (e[0][0] + e[1][0]) / 2 - 0.55, my = (e[0][1] + e[1][1]) / 2 - 0.45; e.d = Math.hypot(mx, my); });
    let lastKey = '';
    function drawFrost(k, ck) {
      const key = Math.round(k * 60) + ':' + Math.round(ck * 60); if (key === lastKey) return; lastKey = key;
      fg.clearRect(0, 0, 512, 512); if (k <= 0) { frostTex.needsUpdate = true; return; }
      const gr = fg.createRadialGradient(270, 240, 30, 256, 256, 380);
      gr.addColorStop(0, `rgba(205,225,245,${0.55 * smooth((k - 0.45) / 0.55)})`); gr.addColorStop(0.6, `rgba(215,232,250,${0.75 * smooth((k - 0.2) / 0.6)})`); gr.addColorStop(1, `rgba(230,240,255,${0.95 * smooth(k / 0.5)})`);
      fg.fillStyle = gr; fg.fillRect(0, 0, 512, 512);
      fg.lineCap = 'round';
      for (const d of dend) {
        let s = d.seed; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
        const grow = (x, y, a, L, w, depth) => {
          let l = 0; fg.beginPath(); fg.moveTo(x, y);
          const pts = [];
          while (l < L) { const st = 6 + 6 * r(); a += (r() - 0.5) * 0.25; x += Math.cos(a) * st; y += Math.sin(a) * st; l += st; fg.lineTo(x, y); pts.push([x, y, a, l]); }
          fg.strokeStyle = `rgba(245,250,255,${0.55 + 0.35 * r()})`; fg.lineWidth = w; fg.stroke();
          if (depth < 2) for (const [px, py, pa, pl] of pts) if (r() < 0.35) { const side = r() < 0.5 ? 1 : -1; grow(px, py, pa + side * (0.9 + 0.3 * r()), (L - pl) * 0.35 * (0.5 + r()), w * 0.6, depth + 1); }
        };
        grow(d.x0, d.y0, d.a, d.L * k, d.w, 0);
      }
      if (ck > 0) {                // cracks: branching from a point near the middle, the rings round it last
        let s2 = 4242; const r = () => (s2 = (s2 * 16807) % 2147483647) / 2147483647;
        const cx = 0.56 * 512, cy = 0.44 * 512;
        const branch = (x, y, an, len, w, depth) => {
          let l = 0; const pts = [[x, y]];
          while (l < len) { const st = 7 + 9 * r(); an += (r() - 0.5) * 0.55; x += Math.cos(an) * st; y += Math.sin(an) * st; l += st; pts.push([x, y]); }
          const n = Math.max(1, Math.round(pts.length * clamp(ck * 1.6 - depth * 0.3)));
          for (const [col, lw] of [['rgba(40,60,90,0.85)', w + 1.6], ['rgba(255,255,255,0.95)', w * 0.6]]) {
            fg.beginPath(); fg.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < n; i++) fg.lineTo(pts[i][0], pts[i][1]); fg.strokeStyle = col; fg.lineWidth = lw; fg.stroke(); }
          if (depth < 2) for (let i = 2; i < pts.length - 2; i++) if (r() < 0.16) branch(pts[i][0], pts[i][1], an + (r() < 0.5 ? 0.9 : -0.9), len * 0.45, w * 0.65, depth + 1);
        };
        const NB = 13; for (let i = 0; i < NB; i++) branch(cx, cy, i / NB * 6.283 + r() * 0.4, 330 * (0.5 + 0.6 * r()), 2.4, 0);
        for (let i = 1; i <= 3; i++) if (ck > 0.3 + i * 0.18) { fg.beginPath();
          for (let j = 0; j <= 30; j++) { const an = j / 30 * 6.283, rr = i * 38 * (0.85 + 0.3 * r()); j ? fg.lineTo(cx + Math.cos(an) * rr, cy + Math.sin(an) * rr) : fg.moveTo(cx + Math.cos(an) * rr, cy + Math.sin(an) * rr); }
          fg.strokeStyle = 'rgba(255,255,255,0.75)'; fg.lineWidth = 1.6; fg.stroke(); }
        const gl = fg.createRadialGradient(cx, cy, 0, cx, cy, 34); gl.addColorStop(0, 'rgba(255,255,255,0.9)'); gl.addColorStop(1, 'rgba(255,255,255,0)'); fg.fillStyle = gl; fg.fillRect(cx - 40, cy - 40, 80, 80);
      }
      frostTex.needsUpdate = true;
    }
    // frost flakes bursting off the suit at the shatter, and the ice streaks of the wind everywhere
    poseNeptune(2.6);
    const NK = 2600, ksrc = fx.samplePoints(NK, 4); rs(55);
    const kflakes = ksrc.map(p => ({ p, v: 2 + 6 * rnd(), up: (rnd() - 0.5) * 1.5, side: (rnd() - 0.5) * 2, d: 0.15 * rnd(), s: 0.006 + 0.014 * rnd() }));
    const kf = pointCloud(NK, FLAKE_FRAG, T.NormalBlending); sc.add(kf.pts);
    const NL = 1100; rs(91);
    const streaks = Array.from({ length: NL }, () => ({ x: rnd() * 60 - 30, y: (rnd() - 0.5) * 14, z: -rnd() * 40 + 4, v: 30 + 30 * rnd(), b: 0.3 + 0.7 * rnd() }));
    const lg = new T.BufferGeometry(), LP = new Float32Array(NL * 6), LC = new Float32Array(NL * 6);
    lg.setAttribute('position', new T.BufferAttribute(LP, 3)); lg.setAttribute('color', new T.BufferAttribute(LC, 3));
    const lines = new T.LineSegments(lg, new T.LineBasicMaterial({ vertexColors: true, transparent: true, blending: T.AdditiveBlending, depthWrite: false }));
    lines.frustumCulled = false; sc.add(lines);
    return { sc, U, shards, drawFrost, kflakes, kf, streaks, LP, LC, lg };
  }
  const NEP = { frost: t => ramp(t, 0.25, 3.0), crust: t => ramp(t, 0.5, 2.9), crack: t => ramp(t, 3.05, 3.65), shatter: 3.72, gust: 3.6,
    // the pose clock slows to a stop as he freezes
    tau: t => { const a0 = 1.2, a1 = 3.0; if (t < a0) return t; const u = Math.min(t, a1) - a0, L = a1 - a0; return a0 + u - u * u / (2 * L) + 0; } };
  function poseNeptune(t) {
    const tau = NEP.tau(t), huddle = ramp(t, 0.6, 2.6), J = a.joints;
    a.pose(tau);
    for (const sd of ['L', 'R']) { const s = sd === 'L' ? -1 : 1;
      const sh = J['shoulder' + sd].rotation, el = J['elbow' + sd].rotation;
      sh.x = lerp(sh.x, 0.75, huddle); sh.y = lerp(sh.y, 0.95 * s, huddle); sh.z = lerp(sh.z, s * 0.05, huddle); el.x = lerp(el.x, 2.2, huddle);
      J['hip' + sd].rotation.x += 0.45 * huddle; J['knee' + sd].rotation.x -= 0.55 * huddle; }
    J.head.rotation.x -= 0.18 * huddle; J.body.rotation.x += 0.18 * huddle;
    // buffeted by the wind (the whole figure; stiff once frozen), then the gust takes him: away with the wind, tumbling
    const buf = 0.05 + 0.03 * (1 - huddle), n = (f, p) => Math.sin(t * f + p) + 0.5 * Math.sin(t * f * 2.3 + p * 1.7);
    a.group.position.set(0.04 * n(7, 1), 0.03 * n(6, 2), 0.03 * n(5, 3));
    a.group.rotation.set(-0.08 + buf * 0.6 * n(5.5, 4), Math.PI - 0.5 + buf * 0.4 * n(4.3, 5), buf * n(6.1, 6));
    const g = t - NEP.gust;
    if (g > 0) {
      const d = 1.2 * g + 7 * g * g;
      a.group.position.addScaledVector(WIND, d); a.group.position.y -= 1.2 * g * g;
      a.group.rotation.z -= 1.6 * g + 1.2 * g * g; a.group.rotation.x += 0.9 * g; a.group.rotation.y += 0.6 * g;
    }
    a.group.updateMatrixWorld(true);
  }
  function frameNeptune(S, t) {
    S.U.tt.value = t; S.U.gust.value = ramp(t, NEP.gust - 0.2, NEP.gust + 0.6);
    fx.U.uHeat.value = 0; fx.U.uChar.value = -1; fx.U.uMelt.value = -1; fx.U.uFrost.value = NEP.frost(t); fx.U.uTime.value = t;
    // where the head is at the shatter (the shards leave from there)
    if (!S.groupAt) { poseNeptune(NEP.shatter); S.headAt = a.joints.head.matrixWorld.clone(); S.groupAt = a.group.matrixWorld.clone(); }
    const headAt = S.headAt;
    poseNeptune(t); fx.update();
    // the crust
    S.drawFrost(NEP.crust(t), NEP.crack(t));
    const ds = t - NEP.shatter, tmp = new T.Matrix4(), q = new T.Quaternion(), pv = new T.Vector3(), sc1 = new T.Vector3(1, 1, 1);
    for (const s of S.shards) {
      if (ds < s.d * 0.06) { s.m.matrix.multiplyMatrices(a.joints.head.matrixWorld, s.local); continue; }
      const dt = Math.max(0, ds - s.d * 0.06);
      tmp.multiplyMatrices(headAt, s.local); pv.setFromMatrixPosition(tmp);
      const outW = s.out.clone().transformDirection(headAt);
      pv.addScaledVector(outW, s.v * dt).addScaledVector(WIND, 3 * dt + 9 * dt * dt); pv.y += -0.4 * dt * dt;
      q.setFromRotationMatrix(tmp).multiply(new T.Quaternion().setFromAxisAngle(s.spin, s.w * dt));
      s.m.matrix.compose(pv, q, sc1);
    }
    // the flakes off the suit
    S.kflakes.forEach((f, i) => {
      const dt = ds - f.d;
      if (dt < 0 || dt > 2.5) { S.kf.set(i, 0, 0, 0, 0, 0, 0, 0); return; }
      const p0 = f.p.clone().applyMatrix4(S.groupAt);
      p0.addScaledVector(WIND, f.v * dt + 6 * dt * dt); p0.y += f.up * dt; p0.z += f.side * 0.3 * dt;
      const fade = 1 - dt / 2.5;
      S.kf.set(i, p0.x, p0.y, p0.z, 0.75 * fade + 0.1, 0.85 * fade + 0.1, 1.0 * fade + 0.12, f.s);
    });
    S.kf.done();
    // the ice streaks: each a short line along the wind, its length the distance it covers in ~1/40 s
    const gk = 1 + 1.4 * S.U.gust.value;
    S.streaks.forEach((s, i) => {
      const x = ((s.x + s.v * gk * t + 30) % 60 + 60) % 60 - 30, L = s.v * gk / 40;
      const o = i * 6; S.LP[o] = x; S.LP[o + 1] = s.y; S.LP[o + 2] = s.z; S.LP[o + 3] = x - L; S.LP[o + 4] = s.y - L * 0.04; S.LP[o + 5] = s.z + L * 0.25;
      const b = s.b * 0.35 * Math.exp(-Math.max(0, -s.z) / 18) * (0.6 + 0.8 * S.U.gust.value);
      S.LC[o] = 0.8 * b; S.LC[o + 1] = 0.9 * b; S.LC[o + 2] = 1.0 * b; S.LC[o + 3] = 0; S.LC[o + 4] = 0; S.LC[o + 5] = 0;
    });
    S.lg.attributes.position.needsUpdate = true; S.lg.attributes.color.needsUpdate = true;
    // the camera: holds on him, a little shake in the wind; after the gust it lets him go
    const sh = 0.012 * (1 + 2 * S.U.gust.value), n = f => Math.sin(t * f) + 0.5 * Math.sin(t * f * 2.7 + 1);
    cam.fov = 36; cam.updateProjectionMatrix();
    const push = ramp(t, 0, 3.4);
    cam.position.set(lerp(-1.1, -0.75, push) + sh * n(9), lerp(0.35, 0.3, push) + sh * n(11), lerp(5.4, 4.2, push));
    const follow = ramp(t, NEP.gust, NEP.gust + 1.2);
    const tgt = new T.Vector3(0, 0.15, 0).lerp(a.group.position.clone().multiplyScalar(0.35), follow);
    cam.lookAt(tgt.x + sh * n(7), tgt.y + sh * n(8), tgt.z);
    const fr0 = NEP.frost(t); a.rim.color.value.setRGB(0.35 * (1 - 0.6 * fr0), 0.6 * (1 - 0.6 * fr0), 1.0 * (1 - 0.6 * fr0)); a.rim.power.value = 3.0;
    return { thr: 1.2, bloom: 0.5, expo: 0.95, vig: 0.55, grade: [0.95, 1.0, 1.06], flash: 0.35 * Math.exp(-Math.max(0, ds) * 9) * (ds > 0 ? 1 : 0) };
  }

  // ---------------- a frame ----------------
  const worlds = {}, builders = { sun: buildSun, neptune: buildNeptune }, framers = { sun: frameSun, neptune: frameNeptune };
  window.__frame = async (t) => {
    const shot = CFG.shots.find(s => t >= s.t0 && t < s.t1) || CFG.shots[CFG.shots.length - 1], lt = t - shot.t0;
    const S = worlds[shot.world] || (worlds[shot.world] = builders[shot.world]());
    if (a.group.parent !== S.sc) S.sc.add(a.group);
    const o = framers[shot.world](S, lt);
    renderer.setRenderTarget(rtMain); renderer.setClearColor(0x000000, 1); renderer.clear(); renderer.render(S.sc, cam);
    post(Object.assign({ t: lt }, o));
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  a.ready.then(() => { window.ready = 1; });
})();
