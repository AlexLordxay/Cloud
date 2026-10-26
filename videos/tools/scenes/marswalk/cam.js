// "An astronaut on Mars": the Nebozvid astronaut walks up a gentle slope towards a ridge at sunset (the Martian dusk is
// blue round the Sun), and on the crest plants the Nebozvid flag. Its own three.js scene drawn by __recRender.
//
// The ground is one deterministic height function H(x, z) (units ~ metres, the figure is ~1.9 tall, facing -z): a
// broad hill rising along the path to a crest at z ~ -4.6, beyond it a slope down into a wide valley, and far off the
// mountains of a crater's rim in the haze; on top, rolling noise, rock slabs (ridged noise cut into steps), craters
// with raised rims on three scales and sand ripples in the low places. Two meshes: a fine one round the path (0.1 apart)
// and a polar one out to the horizon. The terrain's own shadows (the Sun is low, they are long) are baked into the
// vertices by marching towards the Sun; the figure and the rocks cast real shadows (one shadow map).
// The walk: footprints laid out in time, each foot pinned to its print while it stands and swung on an arc between
// prints, the legs solved by two-bone IK in the side plane, the pelvis riding between the feet with a soft bounce.
(() => {
  const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

  // ---------------- the ground ----------------
  const hash2 = (i, j) => { let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
  function vn(x, z) {
    const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j, u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
    const a = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  const fbm = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { s += a * (vn(x * f + 17 * k, z * f - 9 * k) - 0.5); a *= 0.5; f *= 2.03; } return s; };
  const ridged = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { const r = 1 - Math.abs(2 * vn(x * f + 5 * k, z * f + 11 * k) - 1); s += a * r * r; a *= 0.5; f *= 2.1; } return s / 1.75; };
  // craters: at most one in each cell of a grid (size C), radius between r0 and r1; d = distance / radius
  const craterShape = d => d < 1 ? 0.2 * (d * d - 1) + 0.055 * Math.exp(-(((d - 1) / 0.22) ** 2)) : 0.055 * Math.exp(-(((d - 1) / 0.4) ** 2));
  function craters(x, z, C, r0, r1, p, seed) {
    const ci = Math.floor(x / C), cj = Math.floor(z / C); let s = 0;
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
      if (hash2(i + seed, j) > p) continue;
      const cx = (i + hash2(i, j + seed)) * C, cz = (j + hash2(i - seed, j)) * C, r = r0 + (r1 - r0) * hash2(j, i + seed) ** 2;
      const d = Math.hypot(x - cx, z - cz) / r; if (d > 2.2) continue;
      s += r * craterShape(d) * (0.55 + 0.45 * hash2(i + 3 * seed, j + 7));   // older ones softer
    }
    return s;
  }
  const RIDGE = -4.6;
  const ridgeZ = x => RIDGE + 0.5 * Math.sin(x * 0.23 + 0.4) + 0.25 * Math.sin(x * 0.61);
  // the path: a calm strip along x ~ 0 (no rocks, small features damped)
  const pathMask = (x, z) => 1 - (1 - smooth((Math.abs(x) - 0.9) / 1.6)) * (1 - smooth((z - 16) / 3)) * (1 - smooth((-z - 6) / 1.5));
  function H(x, z) {
    const dz = z - ridgeZ(x);
    // the hill: up along the path to the crest, then down into the valley
    let h = dz > 0 ? 1.3 * (1 - Math.min(1, dz / 19) ** 2) : 1.3 - 6.5 * (1 - Math.exp(-dz * dz / 60));
    h -= 0.004 * x * x * smooth(dz / 4) * (1 - smooth((Math.abs(x) - 12) / 10));   // the hill's back rounds off to the sides
    const r = Math.hypot(x, z + 40);
    h += 2.2 * fbm(x * 0.045, z * 0.045, 3) * smooth((r - 10) / 30) + 0.5 * fbm(x * 0.13, z * 0.13, 3);
    const m = pathMask(x, z);
    // rock outcrops: ridged noise lifted in soft-edged layers, on the hillsides and in the valley
    const rg = ridged(x * 0.11 + 3, z * 0.11, 3);
    h += (0.22 * smooth((rg - 0.5) / 0.14) + 0.07 * smooth((rg - 0.68) / 0.08)) * (0.25 + 0.75 * m);
    // dunes on the valley floor: long crests across the wind, a gentle back and a steeper lee face
    { const ph = (x * 0.3 + z * 0.95) / 7 + 2.5 * fbm(x * 0.04 + 9, z * 0.04, 2), f = ph - Math.floor(ph);
      h += 0.8 * (f < 0.72 ? smooth(f / 0.72) : smooth((1 - f) / 0.28)) * smooth((-dz - 9) / 6) * (0.4 + vn(x * 0.04, z * 0.04)) * (1 - smooth((Math.hypot(x, z + 60) - 120) / 60)); }
    h += craters(x, z, 3.2, 0.25, 0.8, 0.45, 11) * m + craters(x, z, 13, 1.2, 4.5, 0.5, 23) * (0.3 + 0.7 * m) + craters(x, z, 70, 8, 26, 0.6, 37);
    // fine rubble and sand ripples (ripples where the ground is low and calm)
    h += 0.05 * fbm(x * 0.9, z * 0.9, 3) * (0.35 + 0.65 * m);
    h += 0.012 * Math.sin((x * 0.35 + z) * 9.5 + 3 * fbm(x * 0.3, z * 0.3, 2)) * smooth(-dz / 6) * (1 - smooth((rg - 0.45) / 0.1));
    // far away: the valley floor, mesas, and the rim of a big crater all round (highest ahead, under the Sun)
    const R = Math.hypot(x, z + 60);
    h += 55 * smooth((R - 250) / 500) * (0.45 + ridged(x / 160, z / 160, 4)) * (0.8 + 0.2 * Math.sin(Math.atan2(x, -z - 60) * 3));
    h += 7 * smooth((ridged(x / 45 + 7, z / 45, 2) - 0.58) / 0.16) * smooth((R - 60) / 60) * (1 - smooth((R - 400) / 100));
    return h;
  }
  const H0 = H(0, 0);
  const G = (x, z) => H(x, z) - H0;   // the ground, with the start of the path at y = 0

  // ---------------- the walk ----------------
  // the astronaut's own walker (characters/astronaut.js, a.walk): 14 steps of 0.8 every 0.76 s up the slope, then
  // three short ones to a stop on the crest. PRINTS (set in setup): [time it lands, z, side, x] of every footprint.
  const STEP = 0.8, PER = 0.76, NSTEP = 14;
  let W = null, PRINTS = null;

  // The plant, after the last step: the right arm lifts the flag high, holds a beat, thrusts it down into the ground
  // (leaning in, knees bending), holds, lets go and steps the arm back. Keys: [t, shoulder x, shoulder z, elbow, body
  // lean (- forward), crouch, left shoulder, head]; the thrust accelerates, the rest ease in and out.
  let T_LAST, PLANT, T_HIT, T_DOWN, T_REL;
  function initPlant() {
    T_LAST = PRINTS[PRINTS.length - 1][0];
    PLANT = [
      [T_LAST - 0.15, 0.15, 0.3, 1.25, 0, 0, 0, 0],
      [T_LAST + 0.55, 1.3, 0.38, 0.95, 0.05, -0.01, 0.15, 0.12],
      [T_LAST + 0.85, 1.42, 0.38, 0.85, 0.07, 0, 0.2, 0.15],
      [T_LAST + 1.12, 0.52, 0.3, 0.22, -0.27, 0.15, 0.4, -0.05],
      [T_LAST + 1.85, 0.5, 0.3, 0.22, -0.26, 0.15, 0.4, -0.05],     // holding on while the fingers open
      [T_LAST + 2.4, 0.42, 0.42, 0.45, -0.12, 0.07, 0.2, 0.0],      // the open hand comes off, back and out a little
      [T_LAST + 3.2, 0.04, 0.17, 0.3, 0, 0, 0, 0],                  // the arm at its side (as the walker hangs it)
    ];
    T_HIT = T_LAST + 1.06; T_DOWN = T_LAST + 1.12; T_REL = T_LAST + 1.8;   // the spike touches; all the way in; let go
  }
  function plant(t) {
    const K = PLANT; let i = 0;
    if (t <= K[0][0]) i = -1; else while (i < K.length - 1 && K[i + 1][0] < t) i++;
    const pick = (k, u) => { const A = K[Math.max(k, 0)], B = K[Math.min(k + 1, K.length - 1)]; return A.map((v, j) => v + (B[j] - v) * u); };
    let r;
    if (i < 0 || i >= K.length - 1) r = K[i < 0 ? 0 : K.length - 1];
    else { const u = (t - K[i][0]) / (K[i + 1][0] - K[i][0]); r = pick(i, i === 2 ? u * u * (1.4 - 0.4 * u) : smooth(u)); }
    return { shX: r[1], shZ: r[2], el: r[3], lean: r[4], crouch: r[5], shL: r[6], head: r[7] };
  }
  // the right fist round the pole (looser than 'grip': the pole is thick); the pole's axis along the fist (the wrist's
  // local x), through the hollow of the curled fingers
  const GRIP = { f: [[0.7, 0.95, 0.55], [0.7, 0.95, 0.55], [0.72, 0.95, 0.55], [0.75, 0.95, 0.55]], spread: 0.35, th: [0.45, 0, 0.35, 0.3] };
  const GRIP_AT = [0, -0.108, -0.045];

  function walk(a, t) {
    const J = a.joints, pk = plant(t);
    const { stride, lead } = W.update(t, { lean: pk.lean, crouch: pk.crouch });
    // the left arm hangs and swings (the walker), lifting a little for balance as the flag goes in; the right one
    // carries the flag (and plants it, see PLANT)
    J.shoulderL.rotation.x += pk.shL; J.elbowL.rotation.x += 0.3 * pk.shL;
    J.shoulderR.rotation.set(pk.shX - 0.06 * lead * stride, 0.05, pk.shZ);
    J.elbowR.rotation.set(pk.el, 0, 0);
    // the wrist: the fist's axis upright while it holds the pole (placeFlag fine-tunes it), then, the hand let go,
    // turning to hang palm-in at the side
    const r = smooth((t - T_REL - 0.3) / 0.9);
    J.wristR.rotation.set(0.05 * r, Math.PI / 2 + (1.4 - Math.PI / 2) * r, 0.04 * r);
    J.head.rotation.x += pk.head;
    // the fingers: round the pole; at the release they open wide (clearly letting go), then relax as the arm comes down
    const g = 1 - smooth((t - T_REL) / 0.25), op = smooth((t - T_REL) / 0.25) * (1 - smooth((t - T_REL - 0.55) / 0.5));
    if (g > 0) a.hand('R', GRIP, g);
    if (op > 0) a.hand('R', 'open', op);
    a.group.updateMatrixWorld(true);
  }


  // ---------------- the scene ----------------
  let S = null;
  window.__sceneSetup = async (r) => {
    const T = r.THREE, scene = new T.Scene(), a = window.__makeAstronaut(T);
    a.T = T;
    await a.ready;
    W = a.walk({ ground: G, from: [0, RIDGE + 0.15 + NSTEP * STEP + 0.55 + 0.32 + 0.15 + STEP / 2], steps: NSTEP, step: STEP, period: PER, start: -0.3, arms: { R: false } });
    PRINTS = W.prints.map(p => [p.t, p.z, p.side, p.x]);
    initPlant();
    scene.add(a.group);
    const sun = new T.Vector3(-0.25, 0.14, -1).normalize(), phobos = new T.Vector3(0.42, 0.3, -1).normalize();

    // the sky (linear colour): the dusk's dim brown, a blue glow round the Sun, darker overhead; the Sun's small disc
    // and Phobos lit from the side. The same function colours the haze over the ground.
    const SKY = `
      uniform vec3 sunD; uniform vec3 phoD;
      vec3 skyCol(vec3 d) {
        float e = d.y;
        vec3 c = mix(vec3(0.22, 0.165, 0.135), vec3(0.045, 0.045, 0.06), smoothstep(-0.02, 0.4, e));
        vec3 dh = normalize(vec3(d.x, d.y * 2.0, d.z));
        float a = acos(clamp(dot(dh, sunD), -1.0, 1.0));
        float toward = max(dot(normalize(vec3(d.x, 0.0, d.z)), normalize(vec3(sunD.x, 0.0, sunD.z))), 0.0);
        c += vec3(0.09, 0.15, 0.28) * exp(-a / 0.3) * 0.7 + vec3(0.2, 0.36, 0.66) * exp(-a / 0.11) * 0.95 + vec3(0.6, 0.8, 1.0) * exp(-a / 0.035) * 1.2;
        c += vec3(0.2, 0.15, 0.13) * exp(-max(e, 0.0) / 0.04) * (0.25 + 0.45 * toward);   // the dusty band along the horizon
        return pow(c, vec3(2.2)) * 1.5;
      }`;
    const sky = new T.Mesh(new T.SphereGeometry(8000, 64, 32), new T.ShaderMaterial({
      side: T.BackSide, depthWrite: false, uniforms: { sunD: { value: sun }, phoD: { value: phobos } },
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: SKY + `
        varying vec3 vD;
        void main(){
          vec3 d = normalize(vD), c = skyCol(d);
          float a = acos(clamp(dot(d, sunD), -1.0, 1.0));
          c += vec3(1.0, 0.98, 0.95) * (smoothstep(0.0062, 0.0052, a) * 30.0 + exp(-a / 0.012) * 3.0);
          // Phobos: a small lumpy disc, lit from the Sun's side
          vec3 ux = normalize(cross(vec3(0.0, 1.0, 0.0), phoD)), uy = cross(phoD, ux);
          vec2 q = vec2(dot(d, ux), dot(d, uy)) / 0.0075; q.x *= 1.25;
          float rr = dot(q, q);
          if (rr < 1.0 && dot(d, phoD) > 0.0) {
            vec3 n = normalize(ux * q.x + uy * q.y + phoD * -sqrt(1.0 - rr));
            float l = max(dot(n, sunD), 0.0);
            c = mix(c, vec3(0.5, 0.45, 0.42) * l * 1.8 + c * 0.4, smoothstep(1.0, 0.85, rr));
          }
          gl_FragColor = vec4(c, 1.0);
          #include <tonemapping_fragment>
          #include <encodings_fragment>
        }`,
    }));
    scene.add(sky);

    // the regolith's fine texture (a multiplier near 1) and its bump
    const cv = document.createElement('canvas'); cv.width = cv.height = 1024;
    { const g = cv.getContext('2d'), im = g.createImageData(1024, 1024);
      const vp = (x, y, P) => {                               // value noise that repeats every P cells (so the texture tiles)
        const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = k => ((k % P) + P) % P;
        const a = hash2(w(i), w(j)), b = hash2(w(i + 1), w(j)), c = hash2(w(i), w(j + 1)), d = hash2(w(i + 1), w(j + 1));
        return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
      for (let y = 0; y < 1024; y++) for (let x = 0; x < 1024; x++) {
        const n = 0.42 * vp(x / 32, y / 32, 32) + 0.3 * vp(x / 16, y / 16, 64) + 0.18 * vp(x / 8, y / 8, 128) + 0.1 * vp(x / 4, y / 4, 256);
        const v = clamp(175 + 80 * (n - 0.5) * 2, 0, 255), k = (y * 1024 + x) * 4;
        im.data[k] = im.data[k + 1] = im.data[k + 2] = v; im.data[k + 3] = 255;
      }
      g.putImageData(im, 0, 0);
      let sd = 7; const rr = () => { sd = Math.imul(sd ^ (sd >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((sd >>> 0) % 1e6) / 1e6; };
      for (let i = 0; i < 2600; i++) {                                    // grit and pebbles (wrapped at the edges)
        const x = rr() * 1024, y = rr() * 1024, r = 1.2 + 6 * rr() ** 4, sh = 70 + 90 * rr();
        for (const ox of [-1024, 0, 1024]) for (const oy of [-1024, 0, 1024]) {
          g.fillStyle = `rgba(${sh},${sh},${sh},0.85)`; g.beginPath(); g.ellipse(x + ox, y + oy, r, r * (0.7 + 0.3 * rr()), rr() * 3, 0, 6.3); g.fill();
          g.fillStyle = 'rgba(235,235,235,0.5)'; g.beginPath(); g.arc(x + ox - r * 0.25, y + oy - r * 0.25, r * 0.45, 0, 6.3); g.fill(); }
      } }
    const tex = new T.CanvasTexture(cv); tex.wrapS = tex.wrapT = T.RepeatWrapping; tex.anisotropy = 8;

    // baked sunlight on the ground: march towards the Sun; 1 = lit, 0 = in a shadow (a soft edge)
    const sunH = Math.hypot(sun.x, sun.z), tanE = sun.y / sunH, sx = sun.x / sunH, sz = sun.z / sunH;
    function lit(x, y, z, far) {
      let res = 1, t = 0.08;
      while (t < far) {
        const d = y + t * tanE - G(x + sx * t, z + sz * t);
        res = Math.min(res, 6 * d / t);
        if (res < -0.2) break;
        t *= 1.13; t += 0.02;
      }
      return smooth((res + 0.2) / 1.2);
    }
    // the ground's colour: rusty regolith, dark rock on the slabs and steep faces, paler dust in the hollows
    const lin = c => c.map(v => Math.pow(v, 2.2));
    const C_SOIL = lin([0.66, 0.39, 0.24]), C_ROCK = lin([0.33, 0.22, 0.16]), C_DUST = lin([0.76, 0.52, 0.35]);
    function colour(x, z, y, ny) {
      const rg = ridged(x * 0.11 + 3, z * 0.11, 3), rock = clamp(smooth((rg - 0.5) / 0.06) * 0.8 + smooth((0.82 - ny) / 0.15), 0, 1);
      const dust = clamp(smooth(fbm(x * 0.2 + 30, z * 0.2, 3) * 3 + 0.2) * (1 - rock), 0, 1);
      const v = 0.85 + 0.3 * (vn(x * 1.7, z * 1.7) - 0.5) + 0.2 * (vn(x * 0.21, z * 0.21) - 0.5);
      return [0, 1, 2].map(i => (C_SOIL[i] + (C_DUST[i] - C_SOIL[i]) * dust * 0.7 + (C_ROCK[i] - C_SOIL[i]) * rock) * v);
    }
    function terrainGeo(pos, idx, far) {
      const n = pos.length / 3, col = new Float32Array(n * 3), sh = new Float32Array(n), uv = new Float32Array(n * 2);
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setIndex(new T.BufferAttribute(idx, 1));
      g.computeVertexNormals();
      const N = g.attributes.normal;
      for (let i = 0; i < n; i++) {
        const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
        col.set(colour(x, z, y, N.getY(i)), i * 3);
        sh[i] = lit(x, y + 0.01, z, far);
        uv[i * 2] = x * 0.4; uv[i * 2 + 1] = z * 0.4;
      }
      g.setAttribute('color', new T.BufferAttribute(col, 3)); g.setAttribute('sunlit', new T.BufferAttribute(sh, 1)); g.setAttribute('uv', new T.BufferAttribute(uv, 2));
      return g;
    }
    // the fine mesh round the path
    const X0 = -16, X1 = 16, Z0 = -26, Z1 = 18, DX = 0.1, NX = Math.round((X1 - X0) / DX) + 1, NZ = Math.round((Z1 - Z0) / DX) + 1;
    const nearGeo = (() => {
      const pos = new Float32Array(NX * NZ * 3), idx = new Uint32Array((NX - 1) * (NZ - 1) * 6);
      for (let j = 0; j < NZ; j++) for (let i = 0; i < NX; i++) { const x = X0 + i * DX, z = Z0 + j * DX; pos.set([x, G(x, z), z], (j * NX + i) * 3); }
      let m = 0; for (let j = 0; j < NZ - 1; j++) for (let i = 0; i < NX - 1; i++) { const q = j * NX + i; idx.set([q, q + NX, q + 1, q + 1, q + NX, q + NX + 1], m); m += 6; }
      return terrainGeo(pos, idx, 60);
    })();
    // the far mesh: rings round the middle out to the horizon; under the fine mesh it is pushed down out of sight
    const CX = 0, CZ = -4, NA = 720, NR = 200, RMIN = 12, RMAX = 4000;
    const farGeo = (() => {
      const pos = new Float32Array(NA * NR * 3), idx = new Uint32Array(NA * (NR - 1) * 6);
      for (let j = 0; j < NR; j++) for (let i = 0; i < NA; i++) {
        const rr = RMIN * Math.pow(RMAX / RMIN, j / (NR - 1)), an = 2 * Math.PI * i / NA, x = CX + rr * Math.sin(an), z = CZ - rr * Math.cos(an);
        const inside = x > X0 + 0.3 && x < X1 - 0.3 && z > Z0 + 0.3 && z < Z1 - 0.3;
        pos.set([x, G(x, z) - (inside ? 1.5 : 0), z], (j * NA + i) * 3);
      }
      let m = 0; for (let j = 0; j < NR - 1; j++) for (let i = 0; i < NA; i++) { const q = j * NA + i, q1 = j * NA + (i + 1) % NA; idx.set([q, q1, q + NA, q1, q1 + NA, q + NA], m); m += 6; }
      return terrainGeo(pos, idx, 600);
    })();

    // the haze and the baked sunlight, added to the standard material
    const fogK = { value: 0.0011 };
    function marsify(mat, baked) {
      mat.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { sunD: { value: sun }, phoD: { value: phobos }, fogK });
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP;' + (baked ? '\nattribute float sunlit; varying float vSun;' : ''))
          .replace('#include <fog_vertex>', '#include <fog_vertex>\n{ vec4 wp = vec4(transformed, 1.0);\n#ifdef USE_INSTANCING\n wp = instanceMatrix * wp;\n#endif\n vWP = (modelMatrix * wp).xyz; }' + (baked ? '\nvSun = sunlit;' : ''));
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; uniform float fogK;' + (baked ? '\nvarying float vSun;' : '') + SKY)
          .replace(/RE_Direct\( directLight, geometry, material, reflectedLight \);/g, (baked ? 'directLight.color *= vSun; ' : '') + 'RE_Direct( directLight, geometry, material, reflectedLight );')
          .replace('#include <fog_fragment>', `{
            vec3 dv = vWP - cameraPosition; float dist = length(dv);
            vec3 hd = normalize(vec3(dv.x, max(dv.y, 0.0) * 0.3 + 0.004 * length(dv.xz), dv.z));
            vec3 fc = skyCol(hd);
            #ifdef TONE_MAPPING
            fc = toneMapping(fc);
            #endif
            fc = linearToOutputTexel(vec4(fc, 1.0)).rgb;
            gl_FragColor.rgb = mix(gl_FragColor.rgb, fc, 1.0 - exp(-dist * fogK));
          }`);
      };
      mat.customProgramCacheKey = () => 'mars' + baked;   // the two variants must not share a program
      return mat;
    }
    const groundMat = marsify(new T.MeshPhysicalMaterial({ vertexColors: true, roughness: 1, metalness: 0, specularIntensity: 0.12, map: tex, bumpMap: tex, bumpScale: 0.008 }), true);   // dust: hardly any sheen
    const near = new T.Mesh(nearGeo, groundMat), far = new T.Mesh(farGeo, groundMat);
    near.receiveShadow = true; far.receiveShadow = false;
    scene.add(near, far);

    // rocks and boulders: a few shapes, hundreds of them (sizes from a power law), not on the path
    const rockMat = marsify(new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.9, metalness: 0, specularIntensity: 0.3, flatShading: true, map: tex }), false);
    const shapes = [0, 1, 2].map(k => {
      const g = new T.IcosahedronGeometry(1, 2), p = g.attributes.position;
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i), d = 1 + 0.35 * (vn(x * 1.6 + 10 * k, z * 1.6 + 3 * y + 5) - 0.5) + 0.15 * (vn(x * 4 + y * 3, z * 4 - 7 * k) - 0.5);
        p.setXYZ(i, x * d, Math.max(y * d * (0.6 + 0.12 * k), -0.4), z * d * (1 + 0.15 * k));
      }
      g.computeVertexNormals(); return g;
    });
    const rng = (() => { let s = 12345; return () => { s = Math.imul(s ^ (s >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((s >>> 0) % 1e6) / 1e6; }; })();
    const NROCK = 750, perShape = Math.ceil(NROCK / 3);
    const rockMeshes = shapes.map(g => { const m = new T.InstancedMesh(g, rockMat, perShape); m.receiveShadow = true; m.count = 0; scene.add(m); return m; });   // their shadows are baked into the ground (below)
    const ROCKS = [];
    const M4 = new T.Matrix4(), Q = new T.Quaternion(), E = new T.Euler(), V = new T.Vector3(), SC = new T.Vector3(), Cc = new T.Color();
    for (let k = 0; k < NROCK * 3 && rockMeshes.some(m => m.count < perShape); k++) {
      const x = -15 + 30 * rng(), z = -25 + 42 * rng(), u = rng();
      let s = Math.min(1.3, 0.05 / Math.pow(1 - 0.985 * u, 0.5));
      if (Math.abs(x) < 0.9 + s && z > -6 && z < 17) continue;       // keep the path clear
      if (pathMask(x, z) < 0.5 && s > 0.12) s *= 0.4;
      const m = rockMeshes[k % 3]; if (m.count >= perShape) continue;
      E.set(rng() * 0.5, rng() * 6.28, rng() * 0.5); Q.setFromEuler(E);
      SC.set(s * (0.8 + 0.4 * rng()), s, s * (0.8 + 0.4 * rng()));
      V.set(x, G(x, z) + s * 0.1, z); M4.compose(V, Q, SC); m.setMatrixAt(m.count, M4); ROCKS.push([x, G(x, z) + s * 0.1, z, s]);
      const l = lit(x, G(x, z) + s * 0.5, z, 60), v = 0.75 + 0.4 * rng();
      Cc.setRGB(0.5 * v, 0.33 * v, 0.23 * v).convertSRGBToLinear().multiplyScalar(0.7 + 0.3 * l); m.setColorAt(m.count, Cc);
      m.count++;
    }
    rockMeshes.forEach(m => { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; });
    // The rocks' long shadows, baked into the ground's sunlight (a shadow map wide enough for all of them is too coarse
    // on the figure and makes its shadows crawl): each rock as an ellipsoid (s wide, 0.75 s high); a ground point is in
    // its shadow where the ray towards the Sun passes through it, the edge soft.
    { const SL = nearGeo.attributes.sunlit, Ls = [sun.x, sun.y, sun.z];
      for (const [cx, cy, cz, rs] of ROCKS) {
        const R = [rs, 0.75 * rs, rs], Lq = Ls.map((v, k) => v / R[k]), LL = Lq[0] ** 2 + Lq[1] ** 2 + Lq[2] ** 2;
        const len = (0.9 * rs + 0.4) / tanE, ex = cx - sx * len, ez = cz - sz * len;
        const i0 = Math.max(0, Math.floor((Math.min(cx, ex) - rs - X0) / DX)), i1 = Math.min(NX - 1, Math.ceil((Math.max(cx, ex) + rs - X0) / DX));
        const j0 = Math.max(0, Math.floor((Math.min(cz, ez) - rs - Z0) / DX)), j1 = Math.min(NZ - 1, Math.ceil((Math.max(cz, ez) + rs - Z0) / DX));
        for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
          const q = j * NX + i, P = nearGeo.attributes.position, Pq = [(P.getX(q) - cx) / R[0], (P.getY(q) - cy) / R[1], (P.getZ(q) - cz) / R[2]];
          const u = -(Pq[0] * Lq[0] + Pq[1] * Lq[1] + Pq[2] * Lq[2]) / LL; if (u <= 0) continue;
          const d = Math.hypot(Pq[0] + Lq[0] * u, Pq[1] + Lq[1] * u, Pq[2] + Lq[2] * u);
          SL.setX(q, SL.getX(q) * smooth((d - 0.75) / 0.3));
        }
      }
      SL.needsUpdate = true; }

    // the light: the low Sun (its shadow map covers the walk and the rocks round it: the Sun is so low that this
    // box reaches far along the ground), a dim brown sky and ground, a cool rim on the figure
    const key = new T.DirectionalLight(0xfff1e2, 2.6);
    key.position.copy(sun).multiplyScalar(80).add(new T.Vector3(0, 0, -5)); key.target.position.set(0, 0, -5);
    // its shadow map covers just the figure and the flag (2.4 each way across the light: fine texels, ~2 mm; the long
    // shadow behind still falls in it, as it runs along the light) and follows the figure in whole texels, so the
    // shadows on the suit stay put instead of crawling
    key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0003; key.shadow.normalBias = 0.012;
    const SB = 2.4; Object.assign(key.shadow.camera, { left: -SB, right: SB, top: SB, bottom: -SB, near: 1, far: 170 });
    scene.add(key, key.target);
    const sunF = sun.clone().negate(), sunR = new T.Vector3().crossVectors(sunF, new T.Vector3(0, 1, 0)).normalize(), sunU = new T.Vector3().crossVectors(sunR, sunF);
    function aimSun(c) {
      const tx = 2 * SB / 2048, snap = v => Math.round(v / tx) * tx;
      const p = sunR.clone().multiplyScalar(snap(c.dot(sunR))).addScaledVector(sunU, snap(c.dot(sunU))).addScaledVector(sunF, c.dot(sunF));
      key.target.position.copy(p); key.position.copy(p).addScaledVector(sun, 80); key.target.updateMatrixWorld();
    }
    scene.add(new T.HemisphereLight(0x6a7088, 0x4a2c1e, 0.38));
    a.rim.color.value.setRGB(0.45, 0.65, 1.0);
    scene.environment = window.__astronautEnv(T, r.renderer, { warm: sun });

    const cam = new T.PerspectiveCamera(36, 720 / 1280, 0.03, 12000);

    // ---- the flag: an aluminium pole with a spike, a cross bar at the top that holds the cloth spread (as on the
    // Moon), the cloth deep blue with the emblem and НЕБОЗВІД. Local frame: +y up the pole (its foot at 0), cloth to +x.
    try { const ff = new FontFace('Unbounded', 'url(/fonts/Unbounded.ttf)'); await ff.load(); document.fonts.add(ff); } catch (e) { console.log('[scene] no font', e.message); }
    const emblem = await new Promise(ok => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = window.__astronautEmblem || ''; });
    const fcv = document.createElement('canvas'); fcv.width = 1024; fcv.height = 690;
    { const g = fcv.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 690);
      gr.addColorStop(0, '#1a2d5e'); gr.addColorStop(1, '#0c1736'); g.fillStyle = gr; g.fillRect(0, 0, 1024, 690);
      g.strokeStyle = '#c9a54a'; g.lineWidth = 10; g.strokeRect(22, 22, 980, 646);              // a thin gold border
      if (emblem) g.drawImage(emblem, 512 - 200, 52, 400, 400);
      g.fillStyle = '#f3f5f9'; g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.font = '700 96px Unbounded, sans-serif';
      try { g.letterSpacing = '8px'; } catch (e) {}
      g.fillText('НЕБОЗВІД', 512, 600); }
    const ftex = new T.CanvasTexture(fcv); ftex.encoding = T.sRGBEncoding; ftex.anisotropy = 8;
    const POLE = 2.0, CW = 0.66, CH = 0.445;
    const flag = new T.Group(); scene.add(flag);
    const alu = new T.MeshStandardMaterial({ color: 0xd4d8de, metalness: 0.85, roughness: 0.32 });
    const add = (g, m, x, y, z) => { const o = new T.Mesh(g, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; flag.add(o); return o; };
    add(new T.CylinderGeometry(0.015, 0.015, POLE, 20), alu, 0, POLE / 2, 0);
    add(new T.ConeGeometry(0.015, 0.1, 20).rotateX(Math.PI), alu, 0, -0.05, 0);                  // the spike
    add(new T.SphereGeometry(0.026, 20, 14), new T.MeshStandardMaterial({ color: 0xd8b25a, metalness: 1, roughness: 0.25 }), 0, POLE + 0.012, 0);
    add(new T.CylinderGeometry(0.009, 0.009, CW + 0.03, 12).rotateZ(Math.PI / 2), alu, (CW + 0.03) / 2, POLE - 0.035, 0);   // the cross bar
    const clothGeo = new T.PlaneGeometry(CW, CH, 33, 22).translate(CW / 2 + 0.015, POLE - 0.04 - CH / 2, 0);
    const clothRest = clothGeo.attributes.position.array.slice();
    // printed on both faces (the back one mirrored back, so the name reads right from either side); a little of the
    // dusk shines through
    const ftexB = ftex.clone(); ftexB.wrapS = T.RepeatWrapping; ftexB.repeat.x = -1; ftexB.offset.x = 1; ftexB.needsUpdate = true;
    for (const [side, tx] of [[T.FrontSide, ftex], [T.BackSide, ftexB]])
      add(clothGeo, new T.MeshStandardMaterial({ map: tx, side, roughness: 0.8, metalness: 0, emissive: 0xffffff, emissiveMap: tx, emissiveIntensity: 0.18 }), 0, 0, 0);
    // the cloth stirs in the thin wind, more while it is carried (amp: 0 at the pole, 1 at the free edge)
    function stir(t, carried) {
      const P = clothGeo.attributes.position;
      for (let i = 0; i < P.count; i++) {
        const x = clothRest[i * 3] - 0.015, y = clothRest[i * 3 + 1], u = Math.max(0, x) / CW, amp = Math.pow(u, 1.15);
        const z = amp * ((0.026 + 0.03 * carried) * Math.sin(9 * x - 3.2 * t + 2.2 * y) + 0.012 * Math.sin(19 * x - 5.3 * t + 6 * y) + 0.04 * carried * Math.sin(2 * Math.PI * t / (2 * PER)));
        P.setXYZ(i, clothRest[i * 3] - 0.03 * amp * amp * (0.4 + carried), y - 0.012 * amp * amp, z);
      }
      P.needsUpdate = true; clothGeo.computeVertexNormals();
    }
    // the flag in the hand: the wrist is turned so the pole stands along D (world), the cloth turned towards side
    const QI = new T.Quaternion(), V1 = new T.Vector3(1, 0, 0);
    function holdFlag(t, k = 1) {                          // k: how much of the wrist's turn to apply (eased out after the release)
      const W = a.joints.wristR; a.group.updateMatrixWorld(true);
      const carry = 1 - smooth((t - T_LAST + 0.3) / 0.8);
      const D = new T.Vector3(0.05 * Math.sin(Math.PI * t / PER) * carry, 1, -0.12 * carry - 0.04).normalize();
      const q = W.getWorldQuaternion(new T.Quaternion()), R = new T.Quaternion().slerp(new T.Quaternion().setFromUnitVectors(V1.clone().applyQuaternion(q), D), k);
      W.quaternion.copy(W.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(R).multiply(q));
      a.group.updateMatrixWorld(true);
      const grip = W.localToWorld(new T.Vector3(...GRIP_AT));
      const slide = S0 + (S1 - S0) * smooth((t - T_LAST - 0.05) / 0.5);
      const side = new T.Vector3(0.15 + 0.85 * (1 - carry), 0, 1 - 0.4 * (1 - carry)), X = side.addScaledVector(D, -side.dot(D)).normalize();
      const M = new T.Matrix4().makeBasis(X, D, new T.Vector3().crossVectors(X, D)).setPosition(grip.addScaledVector(D, -slide));
      return M;
    }
    const S0 = 0.5, DEPTH = 0.2;
    let S1 = S0;
    walk(a, T_DOWN); { const M = holdFlag(T_DOWN), foot = new T.Vector3().setFromMatrixPosition(M), Dy = M.elements[5];
      S1 = clamp(S0 + (foot.y - (G(foot.x, foot.z) - DEPTH)) / Dy, 0.4, 1.3); }
    walk(a, T_REL); const PLANTED = holdFlag(T_REL);
    const FOOT = new T.Vector3().setFromMatrixPosition(PLANTED);
    function placeFlag(t) {
      flag.matrixAutoUpdate = false;
      if (t < T_REL) flag.matrix.copy(holdFlag(t));
      else { holdFlag(t, 1 - smooth((t - T_REL) / 0.5)); flag.matrix.copy(PLANTED); }   // let go: the wrist's turn eases out, no jump
      flag.matrixWorldNeedsUpdate = true;
      stir(t, 1 - smooth((t - T_LAST + 0.3) / 0.8));
    }

    // ---- footprints: the sole's print pressed into the dust (darker, the lugs' grooves, a rim of pushed-up soil),
    // laid over the ground where each foot lands, from the moment it lands
    const pcv = document.createElement('canvas'); pcv.width = 128; pcv.height = 320;
    const acv = document.createElement('canvas'); acv.width = 128; acv.height = 320;
    { const sole = (g, grow) => { g.beginPath(); g.ellipse(64, 95, 50 + grow, 78 + grow, 0, 0, 7); g.fill(); g.beginPath(); g.ellipse(64, 240, 42 + grow, 62 + grow, 0, 0, 7); g.fill(); g.fillRect(24 - grow, 95, 80 + 2 * grow, 145); };
      const g = pcv.getContext('2d'); g.fillStyle = 'rgb(235,235,235)'; sole(g, 7);                    // the rim
      g.fillStyle = 'rgb(120,120,120)'; sole(g, 0);                                                     // the floor, pressed down
      g.fillStyle = 'rgb(70,70,70)'; for (let y = 30; y < 300; y += 22) g.fillRect(20, y, 88, 9);       // the lugs' grooves
      g.filter = 'blur(1.5px)'; g.drawImage(pcv, 0, 0); g.filter = 'none';
      const h = acv.getContext('2d'); h.filter = 'blur(4px)'; h.fillStyle = '#fff'; sole(h, 9); }
    const pTex = new T.CanvasTexture(pcv), aTex = new T.CanvasTexture(acv);
    const pMat = marsify(new T.MeshPhysicalMaterial({ color: 0xffffff, map: pTex, alphaMap: aTex, bumpMap: pTex, bumpScale: 0.012, transparent: true, depthWrite: false,
      roughness: 1, specularIntensity: 0.12, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }), false);
    const prints = PRINTS.map(([tl, z, side, x]) => {
      const g = new T.PlaneGeometry(0.15, 0.37, 6, 12).rotateX(-Math.PI / 2), P = g.attributes.position, col = [];
      for (let i = 0; i < P.count; i++) { const px = x + P.getX(i), pz = z - 0.085 + P.getZ(i); P.setXYZ(i, px, G(px, pz) + 0.004, pz); col.push(...colour(px, pz, 0, 1).map(v => v * 0.85)); }
      g.setAttribute('color', new T.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
      const m = new T.Mesh(g, pMat); m.material = pMat.clone(); m.material.vertexColors = true; m.material.onBeforeCompile = pMat.onBeforeCompile; m.receiveShadow = true; m.userData.t = tl; scene.add(m); return m;
    });

    // ---- dust: kicked up where a foot lands and where it pushes off, a puff where the spike goes in, and fine motes
    // drifting in the air. Every grain moves by a formula of time (drag, slow settling, never below where it started),
    // so the frames don't depend on each other; lit by the Sun, bright where it scatters towards the camera.
    const DP = [], DV = [], DT = [], DL = [], DS = [], DK = [];
    const drng = (() => { let s = 777; return () => { s = Math.imul(s ^ (s >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((s >>> 0) % 1e6) / 1e6; }; })();
    const grain = (p, v, t0, life, size, k) => { DP.push(p[0], p[1], p[2]); DV.push(v[0], v[1], v[2]); DT.push(t0); DL.push(life); DS.push(size); DK.push(k); };
    PRINTS.forEach(([tl, z, side, x], i) => {
      if (i < 1) return;
      const n = i >= PRINTS.length - 2 ? 20 : 46;
      for (let k = 0; k < n; k++) {                            // the landing: out from under the sole, low and wide
        const a0 = drng() * 6.283, r = Math.sqrt(drng()), px = x + 0.09 * r * Math.cos(a0), pz = z - 0.08 + 0.17 * r * Math.sin(a0), sp = 0.25 + 0.75 * drng();
        grain([px, G(px, pz) + 0.01, pz], [Math.cos(a0) * sp, 0.12 + 0.45 * drng(), Math.sin(a0) * sp - 0.25], tl + 0.06 * drng(), 1.2 + 1.8 * drng(), 0.02 + 0.04 * drng(), 2.6);
      }
      const nx = PRINTS.find((q, j) => j > i && q[2] === side);
      if (nx) { const t0 = PRINTS[PRINTS.indexOf(nx) - 1][0] + 0.1 * (nx[0] - PRINTS[PRINTS.indexOf(nx) - 1][0]);
        for (let k = 0; k < 26; k++) {                         // the push-off: thrown back and up from the toe
          const px = x + 0.08 * (drng() - 0.5), pz = z - 0.24 + 0.06 * drng();
          grain([px, G(px, pz) + 0.01, pz], [0.3 * (drng() - 0.5), 0.35 + 0.7 * drng(), 0.4 + 0.8 * drng()], t0 + 0.12 * drng(), 1.0 + 1.6 * drng(), 0.015 + 0.03 * drng(), 2.2); } }
    });
    for (let k = 0; k < 400; k++) {                            // the spike goes in
      const a0 = drng() * 6.283, sp = 0.3 + 1.1 * drng();
      grain([FOOT.x + 0.04 * Math.cos(a0), G(FOOT.x, FOOT.z) + 0.01, FOOT.z + 0.04 * Math.sin(a0)], [Math.cos(a0) * sp, 0.2 + 0.9 * drng(), Math.sin(a0) * sp], T_HIT + 0.08 * drng(), 1.8 + 2.2 * drng(), 0.012 + 0.025 * drng(), 2.0);
    }
    for (let k = 0; k < 700; k++) {                            // motes in the air along the walk
      const px = -5 + 10 * drng(), pz = -10 + 24 * drng();
      grain([px, G(px, pz) + 0.1 + 2.6 * drng(), pz], [0.06 + 0.04 * drng(), 0.01 * (drng() - 0.5), 0.02 * (drng() - 0.5)], -5, 99, 0.004 + 0.008 * drng(), 0.02);
    }
    const dg = new T.BufferGeometry();
    dg.setAttribute('position', new T.Float32BufferAttribute(DP, 3)); dg.setAttribute('v0', new T.Float32BufferAttribute(DV, 3));
    dg.setAttribute('t0', new T.Float32BufferAttribute(DT, 1)); dg.setAttribute('life', new T.Float32BufferAttribute(DL, 1));
    dg.setAttribute('sz', new T.Float32BufferAttribute(DS, 1)); dg.setAttribute('kd', new T.Float32BufferAttribute(DK, 1));
    const dustU = { uT: { value: 0 }, sunD: { value: sun }, uScale: { value: 1280 / (2 * Math.tan(18 * Math.PI / 180)) } };
    const dust = new T.Points(dg, new T.ShaderMaterial({
      uniforms: dustU, transparent: true, depthWrite: false,
      vertexShader: `uniform float uT; uniform vec3 sunD; uniform float uScale;
        attribute vec3 v0; attribute float t0; attribute float life; attribute float sz; attribute float kd;
        varying float vA; varying float vPh;
        void main() {
          float tau = uT - t0;
          if (tau < 0.0 || tau > life) { gl_Position = vec4(0.0, 0.0, -2.0, 1.0); gl_PointSize = 0.0; vA = 0.0; return; }
          vec3 p = position + v0 * (1.0 - exp(-kd * tau)) / kd;
          p.y -= 0.05 * tau * tau / (1.0 + tau);                  // settling, slowly
          p.y = max(p.y, position.y - 0.005);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          float g = tau / life;
          gl_PointSize = max(1.0, sz * (1.0 + 2.5 * g) * uScale / -mv.z);
          vA = pow(1.0 - g, 1.6) * smoothstep(0.0, 0.04, tau) * (kd < 0.1 ? 0.55 : 0.5 / (1.0 + 1.2 * g));
          vPh = pow(max(dot(normalize(p - cameraPosition), sunD), 0.0), 6.0);
        }`,
      fragmentShader: `varying float vA; varying float vPh;
        void main() {
          vec2 q = gl_PointCoord * 2.0 - 1.0; float r = dot(q, q); if (r > 1.0) discard;
          vec3 c = vec3(0.55, 0.36, 0.24) * (0.45 + 2.4 * vPh) + vec3(0.2, 0.3, 0.5) * 0.4 * vPh;
          gl_FragColor = vec4(c, vA * exp(-r * 3.0));
          #include <tonemapping_fragment>
          #include <encodings_fragment>
        }`,
    }));
    dust.frustumCulled = false; scene.add(dust);
    S = { T, scene, a, cam, sky, key, placeFlag, prints, dustU, aimSun };
  };

  // ---------------- the camera ----------------
  // keys [t, camera offset, look-at offset], both from a calm reference: the walk's smooth line (w.track, averaged over
  // ±0.4 s) at the standing pelvis height over the ground (so the camera never bobs or sways with the steps); between
  // the keys a spline even in time (its speed doesn't jump at a key); kept softly above the ground.
  // low by the boots (a step into the dust), alongside, ahead looking back, round behind on the crest for the flag,
  // ahead-left for the thumbs-up, then round, up and back over the valley into the blue dusk.
  const CAM = [
    [0.0, [0.9, -1.12, 2.9], [0.0, -0.8, -1.0]],
    [2.6, [1.5, -0.75, 3.4], [0.0, -0.4, -0.8]],
    [5.0, [5.6, 0.35, 0.8], [0, 0.15, -0.3]],
    [8.0, [4.4, 0.6, -3.6], [0, 0.2, 0]],
    // back round its right side to behind it, for the flag
    [10.4, [5.3, 0.6, 0.6], [0, 0.2, -0.4]],
    [12.4, [2.6, 0.5, 4.8], [0, 0.25, -1.5]],
    [13.4, [1.7, -0.3, 4.6], [-0.15, 0.35, -1.0]],
    [14.8, [1.9, -0.3, 4.0], [-0.1, 0.1, -0.8]],
    // round its left side to the front (an orbit ~4 away), for the thumbs-up
    [16.0, [-2.0, -0.1, 3.46], [0.0, -0.15, -0.3]],
    [17.2, [-4.0, 0.15, 0.35], [0.1, -0.15, 0.0]],
    [18.4, [-2.65, 0.35, -3.0], [0.2, -0.05, 0.0]],
    [20.4, [-2.5, 0.45, -2.8], [0.2, -0.05, 0.0]],
    // back round its left, up and behind, out over the valley
    [21.8, [-4.0, 1.3, 0.3], [0.1, -0.1, -0.4]],
    [23.0, [-2.4, 1.7, 3.6], [0.0, -0.1, -0.6]],
    [24.4, [-0.6, 2.0, 6.0], [0.1, -0.2, -3.0]],
    [30.0, [0.3, 3.4, 10.2], [0.2, -0.5, -6.0]],
  ];
  function key3(i, q) { return CAM[Math.max(0, Math.min(CAM.length - 1, i))][q]; }
  function spline(t, q) {
    const K = CAM, n = K.length; if (t <= K[0][0]) return K[0][q]; if (t >= K[n - 1][0]) return K[n - 1][q];
    let i = 0; while (K[i + 1][0] < t) i++;
    const t1 = K[i][0], t2 = K[i + 1][0], h = t2 - t1, u = (t - t1) / h;
    const tan = k => { const a0 = Math.max(0, k - 1), b0 = Math.min(n - 1, k + 1); return [0, 1, 2].map(j => (key3(b0, q)[j] - key3(a0, q)[j]) / (K[b0][0] - K[a0][0])); };
    const m1 = tan(i), m2 = tan(i + 1), p1 = K[i][q], p2 = K[i + 1][q];
    const h00 = 2 * u ** 3 - 3 * u * u + 1, h10 = u ** 3 - 2 * u * u + u, h01 = -2 * u ** 3 + 3 * u * u, h11 = u ** 3 - u * u;
    return [0, 1, 2].map(j => h00 * p1[j] + h10 * h * m1[j] + h01 * p2[j] + h11 * h * m2[j]);
  }
  const PELVIS_UP = 1.268;   // the pelvis over the ground, standing
  function reference(t) {
    let x = 0, z = 0, y = 0;
    for (let k = -2; k <= 2; k++) { const p = W.track(t + 0.2 * k); x += p[0] / 5; z += p[1] / 5; y += G(p[0], p[1]) / 5; }
    return [x, y + PELVIS_UP, z];
  }
  const groundSmooth = (x, z) => (G(x, z) * 2 + G(x + 0.3, z) + G(x - 0.3, z) + G(x, z + 0.3) + G(x, z - 0.3)) / 6;
  function shoot(t, a, cam) {
    const T = S.T, r = reference(t), o = spline(t, 1), l = spline(t, 2);
    const cx = r[0] + o[0], cz = r[2] + o[2], gy = groundSmooth(cx, cz) + 0.1, k = 0.06;
    const y = r[1] + o[1], yc = gy + k * Math.log(1 + Math.exp((y - gy) / k));   // a soft floor
    cam.position.set(cx, yc, cz);
    cam.lookAt(new T.Vector3(r[0] + l[0], r[1] + l[1], r[2] + l[2]));
  }

  window.__recCam = () => {};
  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer;
    if (!S) { ren.render(r.scene, r.camera); return; }
    const { T, scene, a, cam, sky } = S, t = window.__vt() - (window.__t0 || 0);
    walk(a, t);
    S.placeFlag(t);
    // the end: it turns its head to the camera and gives a thumbs-up with the left hand (the flag is on its right)
    a.gestureAt(t, 'thumbsUp', { start: T_LAST + 5.9, end: T_LAST + 8.2, side: 'L' });
    shoot(t, a, cam);
    if (t > T_LAST + 5.2) a.lookAt(cam.position, smooth((t - T_LAST - 5.2) / 0.8) * (1 - smooth((t - T_LAST - 8.4) / 0.8)));
    a.group.updateMatrixWorld(true);
    S.prints.forEach(m => { m.visible = t >= m.userData.t; });
    S.dustU.uT.value = t;
    S.aimSun(a.group.position.clone().add(new T.Vector3(0.2, -0.2, 0)));
    sky.position.copy(cam.position);
    const tm = ren.toneMapping, te = ren.toneMappingExposure, sm = ren.shadowMap.enabled, st = ren.shadowMap.type;
    ren.toneMapping = T.ACESFilmicToneMapping; ren.toneMappingExposure = 1.1; ren.shadowMap.enabled = true; ren.shadowMap.type = T.PCFSoftShadowMap;
    ren.setRenderTarget(null); ren.render(scene, cam);
    ren.toneMapping = tm; ren.toneMappingExposure = te; ren.shadowMap.enabled = sm; ren.shadowMap.type = st;
  };
})();
