// The Moon's terrain round a site (terrain_data.py), with stars and the Earth: the in-page code that builds them, shared
// by terrain.js (the flights of "Знайомся: Місяць") and other scenes that stand on the same ground (e.g. moon_final).
// moonWorld(shot, meta) -> the source of `async function buildMoon()`, which resolves to { scene, stars, earth, halo,
// earthFrame, hb, sun, og (the output curve's uniform) }; the page serves three.min.js, /data/ (the site's files) and /site/ (the site's Earth maps).
// Units: km, x east, y up (heights exaggerated by meta.ex and bent to the Moon's curvature), z south.
exports.moonWorld = (shot, meta) => `async function buildMoon() {
  const meta = ${JSON.stringify(meta)};
  const hb = new Float32Array(await (await fetch('/data/height.bin')).arrayBuffer());
  const N = meta.n, S = ${shot.mesh || 1280}, step = (N - 1) / (S - 1), EX = meta.ex;
  const R = meta.R / 1000, dx = meta.dx / 1000, dy = meta.dy / 1000;
  const pos = new Float32Array(S * S * 3), uv = new Float32Array(S * S * 2);
  for (let j = 0; j < S; j++) for (let i = 0; i < S; i++) {
    const gi = Math.round(i * step), gj = Math.round(j * step), k = j * S + i;
    const x = (gi - (N - 1) / 2) * dx, z = (gj - (N - 1) / 2) * dy;          // j runs north → south
    const h = hb[gj * N + gi] / 1000 * EX;
    pos[k * 3] = x; pos[k * 3 + 1] = h - (x * x + z * z) / (2 * R); pos[k * 3 + 2] = z;
    uv[k * 2] = gi / (N - 1); uv[k * 2 + 1] = 1 - gj / (N - 1);
  }
  const idx = new Uint32Array((S - 1) * (S - 1) * 6); let n = 0;
  for (let j = 0; j < S - 1; j++) for (let i = 0; i < S - 1; i++) { const a = j * S + i; idx.set([a, a + S, a + 1, a + 1, a + S, a + S + 1], n); n += 6; }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  const load = f => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }));
  const [col, nrm, shd] = await Promise.all([load('/data/colour.jpg'), load('/data/normal.png'), load('/data/shadow.png')]);
  const sun = new THREE.Vector3(...meta.sun).normalize();
  // the output curve: 1/2.2 for the screen; 1 renders linear light (e.g. into an environment map for reflections)
  const og = { value: 1 / 2.2 };
  const mat = new THREE.ShaderMaterial({
    uniforms: { col: { value: col }, nrm: { value: nrm }, shd: { value: shd }, sun: { value: sun }, ex: { value: EX }, es: { value: ${shot.earthshine || 1} }, og },
    vertexShader: 'varying vec2 vUv; varying vec3 vW; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D col; uniform sampler2D nrm; uniform sampler2D shd; uniform vec3 sun; uniform float ex; uniform float es; uniform float og;
      varying vec2 vUv; varying vec3 vW;
      void main() {
        vec3 c = pow(texture2D(col, vUv).rgb, vec3(2.2));
        vec3 t = texture2D(nrm, vUv).rgb * 2.0 - 1.0;                     // x east, y north, z up
        vec3 n = normalize(vec3(t.x * ex, t.z, -t.y * ex));
        // lunar soil throws light back toward the Sun (it looks flat and bright when lit head-on): a plain Lambert
        // mixed with Lommel-Seeliger, which does that
        float mu0 = max(dot(n, sun), 0.0);
        vec3 v = normalize(cameraPosition - vW);
        float mu = max(dot(n, v), 0.05);
        float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.35);
        float s = texture2D(shd, vUv).r;
        vec3 col = c * (vec3(1.0, 0.98, 0.95) * 2.3 * lit * s + vec3(0.010, 0.012, 0.016) * es);   // shadows: only earthshine
        vec2 e2 = min(vUv, 1.0 - vUv);
        col *= smoothstep(0.0, 0.18, min(e2.x, e2.y));                     // the patch's edges fade into the dark
        gl_FragColor = vec4(pow(col, vec3(og)), 1.0);
      }\`,
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(geo, mat));
  // faint stars (a camera exposed for the sunlit ground would hardly show them)
  const sg = new THREE.BufferGeometry(), sp = [], sc = [];
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 2500; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.15 + 0.5 * Math.pow(rnd(), 3);
    sp.push(r * Math.cos(a) * 9000, u * 9000, r * Math.sin(a) * 9000); sc.push(b, b, b * 1.05);
  }
  sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.Float32BufferAttribute(sc, 3));
  const stars = new THREE.Points(sg, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);
  // the Earth, if the shot has it: [azimuth from north through east, elevation], 1.9° across as seen from the Moon,
  // lit by the same Sun (its phase is the Moon's turned inside out). Drawn from the site's maps: the day side with
  // clouds, the ocean's glint and a blue haze toward the rim, city lights on the night side, a thin glowing atmosphere
  // round the edge. It is turned so that a chosen place faces us on the lit side (shot.earthFace: [lat, lon], and how
  // far right of the middle it sits), its north pole leaning toward us by shot.earthLean degrees.
  let earth = null, halo = null, earthFrame = null;
  const EARTH = ${JSON.stringify(shot.earth || null)};
  if (EARTH) {
    const [day, night, clouds, spec] = await Promise.all(['earth_day.jpg', 'earth_night.jpg', 'earth_clouds.png', 'earth_specular.jpg'].map(f => load('/site/' + f)));
    const U = { day: { value: day }, night: { value: night }, clouds: { value: clouds }, spec: { value: spec }, sun: { value: sun },
      A: { value: new THREE.Vector3() }, F: { value: new THREE.Vector3() }, E: { value: new THREE.Vector3() },
      lon0: { value: 0 }, C: { value: new THREE.Vector3() }, R: { value: 1 }, og };
    const VS = 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }';
    earth = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 64), new THREE.ShaderMaterial({ uniforms: U, vertexShader: VS,
      fragmentShader: \`uniform sampler2D day, night, clouds, spec; uniform vec3 sun, A, F, E, C; uniform float lon0, og;
        varying vec3 vW;
        void main() {
          vec3 n = normalize(vW - C), V = normalize(cameraPosition - vW);
          float lat = asin(clamp(dot(n, A), -1.0, 1.0)), lon = lon0 + atan(dot(n, E), dot(n, F));
          vec2 uv = vec2(fract((lon + 3.14159265) / 6.2831853), (lat + 1.5707963) / 3.14159265);
          vec3 c = pow(texture2D(day, uv).rgb, vec3(2.2));
          float cl = texture2D(clouds, uv).r, sea = texture2D(spec, uv).r;
          float mu = dot(n, sun), dif = max(mu, 0.0), dayK = smoothstep(-0.10, 0.10, mu);
          float rim = pow(1.0 - max(dot(n, V), 0.0), 2.5);
          vec3 col = c * dif * 1.9;
          // the air: a blue veil that thickens toward the rim
          col = mix(col, vec3(0.30, 0.52, 0.95) * dif * 1.4, 0.10 + 0.55 * rim);
          col = mix(col, vec3(1.0, 0.99, 0.97) * dif * 2.1, cl * 0.85);              // clouds over everything
          vec3 H = normalize(sun + V);
          col += vec3(1.0, 0.95, 0.85) * pow(max(dot(n, H), 0.0), 70.0) * sea * (1.0 - cl) * dif * 1.6;
          // city lights only (the map's faint land colour is left out): the brightest specks, warm
          float lights = smoothstep(0.35, 0.9, dot(texture2D(night, uv).rgb, vec3(0.3, 0.59, 0.11)));
          col += vec3(1.0, 0.75, 0.45) * lights * 0.35 * (1.0 - dayK) * (1.0 - 0.8 * cl);
          gl_FragColor = vec4(pow(col, vec3(og)), 1.0);
        }\` }));
    // the atmosphere seen edge-on: a thin glow just outside the limb on the sunlit side
    halo = new THREE.Mesh(new THREE.SphereGeometry(1.06, 96, 48), new THREE.ShaderMaterial({ uniforms: U, vertexShader: VS,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      fragmentShader: \`uniform vec3 sun, C; uniform float R; varying vec3 vW;
        void main() {
          vec3 d = normalize(vW - cameraPosition), oc = C - cameraPosition;
          vec3 near = cameraPosition + d * dot(oc, d);                                  // closest point to the centre
          float b = length(near - C) / R;
          if (b < 1.0) discard;
          float g = exp(-(b - 1.0) / 0.012) * smoothstep(-0.25, 0.35, dot(normalize(near - C), sun));
          gl_FragColor = vec4(vec3(0.35, 0.6, 1.0) * g * 0.9, 1.0);
        }\` }));
    const a = EARTH[0] * Math.PI / 180, e = EARTH[1] * Math.PI / 180;
    const dir = new THREE.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
    const FACE = ${JSON.stringify(shot.earthFace || [0, 0, 0])}, LEAN = ${shot.earthLean || 0} * Math.PI / 180;
    const F0 = dir.clone().negate(), Ax = new THREE.Vector3(0, 1, 0).multiplyScalar(Math.cos(LEAN)).addScaledVector(F0, Math.sin(LEAN)).normalize();
    U.A.value.copy(Ax); U.F.value.copy(F0).addScaledVector(Ax, -F0.dot(Ax)).normalize();
    U.E.value.crossVectors(dir, Ax).normalize();
    U.lon0.value = (FACE[1] - FACE[2]) * Math.PI / 180;        // the middle of the disc: the place's longitude minus its offset
    // shot.earthScale: drawn larger than life (1 = its real 1.9°)
    earthFrame = { dir, D: 8000, R: 8000 * Math.tan(0.95 * Math.PI / 180) * ${shot.earthScale || 1}, U };
    earth.scale.setScalar(earthFrame.R); halo.scale.setScalar(earthFrame.R);
    scene.add(earth, halo);
  }
  // a marked place (Apollo 11): a bright dot on the ground and a thin line up from it
  const MARK = ${JSON.stringify(shot.marker || null)};
  if (MARK) {
    const gi = Math.round(MARK[0] / dx + (N - 1) / 2), gj = Math.round(MARK[1] / dy + (N - 1) / 2);
    const y = hb[gj * N + gi] / 1000 * EX - (MARK[0] * MARK[0] + MARK[1] * MARK[1]) / (2 * R);
    const pg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y + 0.02, MARK[1])]);
    const cv = document.createElement('canvas'); cv.width = cv.height = 64;
    const gx = cv.getContext('2d'), gr = gx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,250,235,1)'); gr.addColorStop(0.18, 'rgba(255,214,130,1)'); gr.addColorStop(0.45, 'rgba(255,190,90,0.35)'); gr.addColorStop(1, 'rgba(255,190,90,0)');
    gx.fillStyle = gr; gx.fillRect(0, 0, 64, 64);
    scene.add(new THREE.Points(pg, new THREE.PointsMaterial({ size: 26, sizeAttenuation: false, map: new THREE.CanvasTexture(cv), transparent: true, depthTest: false, depthWrite: false })));
    const lg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y, MARK[1]), new THREE.Vector3(MARK[0], y + 2.5, MARK[1])]);
    scene.add(new THREE.Line(lg, new THREE.LineBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.8, depthTest: false })));
  }
  return { scene, stars, earth, halo, earthFrame, hb, sun, og };
}`;
