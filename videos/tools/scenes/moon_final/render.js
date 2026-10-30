// The finale of the stick cartoon ("що з цією планетою не так"): the Nebozvid astronaut on the real Moon, near the
// south pole, walks a few steps toward the Earth hanging low over the hills, stops, looks at it, and lowers his head.
// The camera starts a little way off (the relief and the Earth in view) and flies in smoothly behind him, closing to a
// long lens so the Earth hangs just over his helmet.
//
//   node scenes/moon_final/render.js stills 0,4,8   -> work/moon_final/still_<t>.jpg
//   node scenes/moon_final/render.js video          -> work/moon_final/frames/f_00000.jpg …
//
// Two passes each frame: (1) the far Moon of moon_meet (scenes/moon_meet/world.js: the LOLA/LROC relief of the site
// 'south', the stars, the Earth where it really hangs, ~4.5° over the northern horizon), in km; (2) after clearing the
// depth, the near ground in metres round the walk and the astronaut. The near ground is the same LOLA surface
// (exaggerated and bent the same way, so it meets the far one) plus what 63 m cells can't hold: craters from 20 cm
// to 80 m, rubble, boulders and the boot prints, fading out with distance. The Sun is the site's (6° up in the east):
// the craters' shadows are worked out exactly for their bowls, the rocks' baked as ellipsoids, the figure's from a
// shadow map onto a shadow-catching copy of the ground.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const { moonWorld } = require('../moon_meet/world');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'moon_final');
const DATA = path.join(TOOLS, 'work', 'moon_meet', 'south'), SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [mode = 'stills', list = '0'] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30, DUR = 9.6;
if (!fs.existsSync(path.join(DATA, 'meta.json'))) { console.log('first: python3 scenes/moon_meet/terrain_data.py south'); process.exit(1); }
const meta = JSON.parse(fs.readFileSync(path.join(DATA, 'meta.json')));
// the far Moon: the site's Earth (half lit, Ukraine on its lit side), as in moon_meet's last flight
const shot = { site: 'south', mesh: 1600, earth: [0, 4.5], earthFace: [49, 31, 40], earthLean: 28, earthshine: 2.5 };
// where he stands, km east and south of the patch centre: a level, sunlit plain, the hills to the north ~2.5° high
// (found by scanning the patch: flat within ~25 m over 400 m, the Earth clear over the horizon)
const SPOT = [68.10, 4.60];

const page = `<!doctype html><html><body style="margin:0;background:#000">
<script src="/three.min.js"></script><script src="/emblem.js"></script><script src="/astronaut.js"></script><script>
${moonWorld(shot, meta)}
const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
async function setup() {
  const T = THREE;
  const far = await buildMoon(), meta = ${JSON.stringify(meta)};
  const hb = far.hb, N = meta.n, DX = meta.dx, EX = meta.ex, R = meta.R, HALF = (N - 1) / 2;
  const X0 = ${SPOT[0] * 1000}, Z0 = ${SPOT[1] * 1000};
  // the LOLA surface in metres at a point (x east, z south of the spot), exaggerated and bent as world.js draws it
  function dem(x, z) {
    const gx = (X0 + x) / DX + HALF, gz = (Z0 + z) / DX + HALF;
    const i = Math.min(N - 2, Math.max(0, Math.floor(gx))), j = Math.min(N - 2, Math.max(0, Math.floor(gz))), fx = gx - i, fz = gz - j;
    const h = (hb[j * N + i] * (1 - fx) + hb[j * N + i + 1] * fx) * (1 - fz) + (hb[(j + 1) * N + i] * (1 - fx) + hb[(j + 1) * N + i + 1] * fx) * fz;
    const X = X0 + x, Z = Z0 + z;
    return h * EX - (X * X + Z * Z) / (2 * R);
  }
  const BASE = dem(0, 0);
  const sun = far.sun.clone(), tanE = sun.y / Math.hypot(sun.x, sun.z), sx = sun.x / Math.hypot(sun.x, sun.z), sz = sun.z / Math.hypot(sun.x, sun.z);

  // ---------------- the small relief ----------------
  const hash2 = (i, j) => { let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
  function vn(x, z) {
    const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j, u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
    const a = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  const fbm = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { s += a * (vn(x * f + 17 * k, z * f - 9 * k) - 0.5); a *= 0.5; f *= 2.03; } return s; };
  // a crater's profile (d = distance / radius): a bowl a fifth as deep as it is wide, a raised rim, ejecta beyond
  const RIM = 0.055;
  const prof = d => d < 1 ? 0.2 * (d * d - 1) + RIM * Math.exp(-(((d - 1) / 0.22) ** 2)) : RIM * Math.exp(-(((d - 1) / 0.4) ** 2));
  // the walk's strip (x ~ 0, from z ~ 9 to -1): the larger craters and the rocks kept off it
  const pathMask = (x, z) => 1 - (1 - smooth((Math.abs(x) - 1.0) / 1.5)) * (1 - smooth((z - 10) / 3)) * (1 - smooth((-z - 1.5) / 2));
  // the camera's corridor (from its start, 34 m south, to the walk): no big craters or boulders in the way
  const corridor = (x, z) => { const u = Math.min(1, Math.max(0, (z - 2) / 34)), d = Math.abs(x + 5.5 * u); return smooth((d - 6) / 10) + smooth((z - 40) / 10) + smooth((-z - 4) / 8); };
  // craters on a grid of cells C (at most one per cell, radius r0…r1): adds to out[0] the height, multiplies out[1]
  // by the sunlight. A point in a bowl is lit if the ray to the Sun clears the rim on the sunward side.
  function craters(x, z, C, r0, r1, p, seed, k, out) {
    const ci = Math.floor(x / C), cj = Math.floor(z / C);
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
      if (hash2(i + seed, j) > p) continue;
      const cx = (i + hash2(i, j + seed)) * C, cz = (j + hash2(i - seed, j)) * C, r = r0 + (r1 - r0) * hash2(j, i + seed) ** 2;
      const px = x - cx, pz = z - cz, d = Math.hypot(px, pz) / r; if (d > 2.4) continue;
      const amp = r * (0.45 + 0.55 * hash2(i + 3 * seed, j + 7)) * k;     // older ones shallower
      out[0] += amp * prof(d);
      if (d < 1.02) {
        const b = px * sx + pz * sz, c = px * px + pz * pz - r * r, tt = -b + Math.sqrt(Math.max(0, b * b - c));
        const clear = amp * prof(d) + tt * tanE - amp * RIM * 0.85;
        out[1] *= smooth(clear / (0.04 * r + 0.01) + 0.5);
      }
    }
  }
  const out = [0, 1];
  function detail(x, z) {
    out[0] = 0; out[1] = 1;
    const m = pathMask(x, z), r = Math.hypot(x, z - 4), fade = 1 - smooth((r - 700) / 900);
    if (fade <= 0) return out;
    craters(x, z, 3.0, 0.15, 0.9, 0.55, 11, 0.35 + 0.65 * m, out);
    craters(x, z, 11, 0.8, 4.5, 0.6, 23, m * Math.min(1, 0.25 + corridor(x, z)), out);
    craters(x, z, 45, 4, 18, 0.65, 37, Math.min(1, smooth((r - 12) / 10) + 0.0) * Math.min(1, corridor(x, z)), out);
    craters(x, z, 190, 18, 75, 0.7, 53, Math.min(1, corridor(x, z)) * smooth((r - 30) / 30), out);
    out[0] += 0.12 * fbm(x * 0.35, z * 0.35, 3) + 0.025 * fbm(x * 2.2, z * 2.2, 2) * (0.5 + 0.5 * m);
    out[0] *= fade; out[1] = 1 - (1 - out[1]) * fade;
    return out;
  }
  const G = (x, z) => dem(x, z) - BASE + detail(x, z)[0];

  // ---------------- the near ground: a polar mesh round the walk, fine near it ----------------
  const CX = 0, CZ = 4, NA = 1024, rings = [0];
  { let r = 0; while (r < 36) { r += 0.08; rings.push(r); } while (r < 2600) { r *= 1 + 2 * Math.PI / NA; rings.push(r); } }
  const NR = rings.length, NV = NR * NA;
  const pos = new Float32Array(NV * 3), lit = new Float32Array(NV), alb = new Float32Array(NV);
  for (let k = 0; k < NR; k++) for (let a = 0; a < NA; a++) {
    const ang = (a + 0.5 * (k & 1)) / NA * 2 * Math.PI, x = CX + rings[k] * Math.cos(ang), z = CZ + rings[k] * Math.sin(ang), q = k * NA + a;
    const d = detail(x, z);
    pos[q * 3] = x; pos[q * 3 + 1] = dem(x, z) - BASE + d[0]; pos[q * 3 + 2] = z; lit[q] = d[1];
    // the soil's brightness: patches of fresher (paler) and older (darker) regolith, fine mottling
    alb[q] = 1 + 0.16 * fbm(x * 0.02 + 3, z * 0.02, 3) + 0.10 * fbm(x * 0.4, z * 0.4, 2);
  }
  const idx = new Uint32Array((NR - 1) * NA * 6); let n = 0;
  for (let k = 0; k < NR - 1; k++) for (let a = 0; a < NA; a++) {
    const p0 = k * NA + a, p1 = k * NA + (a + 1) % NA, p2 = (k + 1) * NA + a, p3 = (k + 1) * NA + (a + 1) % NA;
    idx.set([p0, p1, p2, p1, p3, p2], n); n += 6;   // facing up
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('lit', new T.BufferAttribute(lit, 1)); geo.setAttribute('alb', new T.BufferAttribute(alb, 1));
  geo.setIndex(new T.BufferAttribute(idx, 1)); geo.computeVertexNormals();

  // ---------------- rocks: rubble and a few boulders, their long shadows baked into the ground ----------------
  let seed = 99; const rng = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const rockGeos = [0, 1, 2].map(s => {
    const g = new T.SphereGeometry(1, 40, 28), P = g.attributes.position;
    for (let i = 0; i < P.count; i++) {
      const v = new T.Vector3().fromBufferAttribute(P, i), k = 1 + 0.28 * fbm(v.x * 1.7 + s * 5, v.y * 1.7 + v.z * 1.3, 3) + 0.1 * Math.abs(v.y);
      v.multiplyScalar(k); v.y = Math.max(v.y * 0.75, -0.4); P.setXYZ(i, v.x, v.y, v.z);
    }
    g.computeVertexNormals(); return g;
  });
  const ROCKS = [];
  for (let k = 0; k < 1500; k++) {
    const rr = 1.5 + 160 * Math.pow(rng(), 1.8), ang = rng() * 2 * Math.PI, x = CX + rr * Math.cos(ang), z = CZ + rr * Math.sin(ang);
    let s = Math.min(1.2, 0.03 / Math.pow(1 - 0.985 * rng(), 0.5));
    if (pathMask(x, z) < 0.5 && s > 0.08) continue;
    if (corridor(x, z) < 1 && s > 0.06 + 0.3 * corridor(x, z)) continue;
    ROCKS.push([x, G(x, z) - s * 0.2, z, s, rng() * 6.28, (rng() * 3) | 0]);
  }
  for (const [cx, cy, cz, rs] of ROCKS) {                                  // each as an ellipsoid (s wide, 0.75 s high)
    const Rr = [rs, 0.75 * rs, rs], L = [sun.x, sun.y, sun.z].map((v, k) => v / Rr[k]), LL = L[0] ** 2 + L[1] ** 2 + L[2] ** 2;
    const len = (0.8 * rs + 0.3) / tanE, reach = len + rs;
    const k0 = Math.max(0, rings.findIndex(r => r > Math.hypot(cx - CX, cz - CZ) - reach) - 1);
    for (let k = k0; k < NR && rings[k] < Math.hypot(cx - CX, cz - CZ) + reach; k++) for (let a = 0; a < NA; a++) {
      const q = k * NA + a, px = pos[q * 3] - cx; if (px > rs || px < -reach) continue;
      const pz = pos[q * 3 + 2] - cz; if (Math.abs(pz) > rs * 1.1) continue;
      const Q = [px / Rr[0], (pos[q * 3 + 1] - cy) / Rr[1], pz / Rr[2]];
      const u = -(Q[0] * L[0] + Q[1] * L[1] + Q[2] * L[2]) / LL; if (u <= 0) continue;
      const d = Math.hypot(Q[0] + L[0] * u, Q[1] + L[1] * u, Q[2] + L[2] * u);
      lit[q] *= smooth((d - 0.8) / 0.25);
    }
  }

  // ---------------- the walk ----------------
  const a = window.__makeAstronaut(T); await a.ready;
  // four steps north from 4.3 m out, then the walker's three short ones to a stop with the feet together
  const w = a.walk({ ground: G, from: [0, 4.3], heading: 0, steps: 4, start: 0.15 });
  const PR = w.prints.slice(0, 16);

  // the ground's light, as world.js lights the far relief (Lambert mixed with Lommel-Seeliger, shadows only lit by
  // the earthshine), with the soil's mottling, the crater and rock shadows, and the boot prints pressed in
  const U = { col: { value: null }, shd: { value: null }, sun: { value: sun }, es: { value: 2.5 }, tNow: { value: 0 },
    prints: { value: Array.from({ length: 16 }, (_, i) => PR[i] ? new T.Vector4(PR[i].x, PR[i].z, PR[i].side === 'L' ? -1 : 1, PR[i].t) : new T.Vector4(0, 0, 0, 1e9)) }, np: { value: PR.length },
    dxN: { value: DX * (N - 1) }, off: { value: new T.Vector2(X0, Z0) } };
  const load = f => new Promise(r => new T.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }));
  [U.col.value, U.shd.value] = await Promise.all([load('/data/colour.jpg'), load('/data/shadow.png')]);
  const groundMat = new T.ShaderMaterial({ uniforms: U,
    vertexShader: \`attribute float lit; attribute float alb; varying float vLit, vAlb; varying vec3 vW, vN;
      void main() { vLit = lit; vAlb = alb; vN = normal; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }\`,
    fragmentShader: \`uniform sampler2D col, shd; uniform vec3 sun; uniform float es, tNow, dxN; uniform vec2 off; uniform vec4 prints[16]; uniform int np;
      varying float vLit, vAlb; varying vec3 vW, vN;
      float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vno(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        vec2 uv = vec2((vW.x + off.x) / dxN + 0.5, 0.5 - (vW.z + off.y) / dxN);
        float gr = 0.55 * vno(vW.xz * 9.0) + 0.3 * vno(vW.xz * 31.0) + 0.15 * vno(vW.xz * 2.3);
        vec3 c = pow(texture2D(col, uv).rgb, vec3(2.2)) * vAlb * (0.84 + 0.32 * gr);
        vec3 n = normalize(vN);
        // the boot prints: a sole-shaped dent with cross treads, a little darker (the soil is compacted)
        for (int i = 0; i < 16; i++) {
          if (i >= np) break;
          vec4 p = prints[i]; if (tNow < p.w) continue;
          vec2 q = vW.xz - p.xy;
          float e = length(vec2(q.x / 0.075, (q.y + 0.03) / 0.16));
          float m = 1.0 - smoothstep(0.85, 1.05, e);
          float tread = 0.5 + 0.5 * sin(q.y * 140.0);
          c *= 1.0 - m * (0.22 + 0.12 * tread);
          n = normalize(n + vec3(0.0, 0.0, m * 0.25 * (tread - 0.5)));
        }
        float mu0 = max(dot(n, sun), 0.0);
        vec3 v = normalize(cameraPosition - vW);
        float mu = max(dot(n, v), 0.05);
        float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.35);
        float s = texture2D(shd, uv).r * vLit;
        vec3 o = c * (vec3(1.0, 0.98, 0.95) * 2.3 * lit * s + vec3(0.010, 0.012, 0.016) * es);
        gl_FragColor = vec4(pow(o, vec3(1.0 / 2.2)), 1.0);
      }\` });
  const scene = new T.Scene();
  const ground = new T.Mesh(geo, groundMat); ground.frustumCulled = false; scene.add(ground);
  // the figure's shadow: a shadow-catching copy of the ground round the walk
  { const KR = rings.findIndex(r => r > 30), sg = new T.BufferGeometry();
    sg.setAttribute('position', geo.attributes.position); sg.setAttribute('normal', geo.attributes.normal);
    sg.setIndex(new T.BufferAttribute(idx.slice(0, KR * NA * 6), 1));
    const sm = new T.ShadowMaterial({ opacity: 0.9, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
    const sh = new T.Mesh(sg, sm); sh.receiveShadow = true; sh.frustumCulled = false; scene.add(sh); }
  // the rocks, lit the same way
  const rockMat = new T.ShaderMaterial({ uniforms: { sun: U.sun, es: U.es },
    vertexShader: \`attribute float shade; varying vec3 vW, vN; varying float vS;
      void main() { vS = shade; mat4 m = modelMatrix * instanceMatrix; vec4 w = m * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(m) * normal); gl_Position = projectionMatrix * viewMatrix * w; }\`,
    fragmentShader: \`uniform vec3 sun; uniform float es; varying vec3 vW, vN; varying float vS;
      void main() {
        vec3 n = normalize(vN), v = normalize(cameraPosition - vW);
        float mu0 = max(dot(n, sun), 0.0), mu = max(dot(n, v), 0.05), lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.2);
        vec3 c = vec3(0.20, 0.195, 0.19) * vS;
        gl_FragColor = vec4(pow(c * (2.3 * lit + 0.03 * es), vec3(1.0 / 2.2)), 1.0);
      }\` });
  { const M4 = new T.Matrix4(), Qq = new T.Quaternion(), E = new T.Euler(), V = new T.Vector3(), SC = new T.Vector3();
    for (let g = 0; g < 3; g++) {
      const mine = ROCKS.filter(r => r[5] === g), im = new T.InstancedMesh(rockGeos[g], rockMat, mine.length);
      const shade = new Float32Array(mine.length);
      mine.forEach(([x, y, z, s, rot], i) => {
        E.set(0.3 * Math.sin(rot * 3), rot, 0.3 * Math.cos(rot * 5)); Qq.setFromEuler(E);
        SC.set(s * (0.8 + 0.4 * Math.abs(Math.sin(rot * 7))), s, s * (0.8 + 0.4 * Math.abs(Math.cos(rot * 11))));
        M4.compose(V.set(x, y, z), Qq, SC); im.setMatrixAt(i, M4); shade[i] = 0.8 + 0.5 * Math.abs(Math.sin(rot * 13));
      });
      rockGeos[g].setAttribute('shade', new T.InstancedBufferAttribute(shade, 1));
      im.frustumCulled = false; scene.add(im);
    } }

  // ---------------- the astronaut's light ----------------
  scene.add(a.group);
  // the Sun: a shadow map just round the figure (its long shadow runs along the light, so the depth range holds it)
  const key = new T.DirectionalLight(0xfff6ea, 3.2);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0003; key.shadow.normalBias = 0.012;
  const SB = 2.2; Object.assign(key.shadow.camera, { left: -SB, right: SB, top: SB, bottom: -SB, near: 1, far: 120 });
  scene.add(key, key.target);
  // a.lights: the shadow on his own suit from the Sun (fine texels); earthshine from the north, faint and blue; the
  // sunlit ground below, grey
  const fill = new T.DirectionalLight(0x9db8ff, 0.22); fill.position.set(0, 0.08, -1); scene.add(fill);
  scene.add(new T.HemisphereLight(0x0a0c12, 0x8a8782, 0.16));
  a.rim.power.value = 4.0; a.rim.color.value.setRGB(0.25, 0.32, 0.45);
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); document.body.appendChild(renderer.domElement);
  renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap; renderer.autoClear = false;
  scene.environment = window.__astronautEnv(T, renderer, { warm: sun });

  const cam = new T.PerspectiveCamera(40, ${W} / ${H}, 0.05, 6000), farCam = new T.PerspectiveCamera(40, ${W} / ${H}, 0.05, 20000);
  const sunF = sun.clone().negate(), sunR = new T.Vector3().crossVectors(sunF, new T.Vector3(0, 1, 0)).normalize(), sunU = new T.Vector3().crossVectors(sunR, sunF);
  function aimSun(c) {                                       // the shadow box follows the figure in whole texels
    const tx = 2 * SB / 2048, snap = v => Math.round(v / tx) * tx;
    const p = sunR.clone().multiplyScalar(snap(c.dot(sunR))).addScaledVector(sunU, snap(c.dot(sunU))).addScaledVector(sunF, c.dot(sunF));
    key.target.position.copy(p); key.position.copy(p).addScaledVector(sun, 60); key.target.updateMatrixWorld();
  }

  window.__frame = (t, C) => {
    // the figure: the walk, then at rest he lifts his eyes to the Earth, holds, and lets his head sink, shoulders falling
    const up = smooth((t - C.lookUp[0]) / (C.lookUp[1] - C.lookUp[0])), down = smooth((t - C.down[0]) / (C.down[1] - C.down[0]));
    w.update(t, { lean: -0.1 * down, crouch: 0.015 * down });
    const J = a.joints;
    J.head.rotation.x += 0.2 * up * (1 - down) - 0.26 * down;
    J.head.rotation.y += 0.5 * down; J.body.rotation.y += 0.12 * down;   // turning a little away from the Earth, toward us
    J.body.rotation.x -= 0.06 * down;
    for (const sd of ['L', 'R']) { J['shoulder' + sd].rotation.z *= 1 - 0.5 * down; J['shoulder' + sd].rotation.x -= 0.06 * down; }
    a.group.updateMatrixWorld(true);
    U.tNow.value = t;
    aimSun(a.group.position.clone());
    // the camera: the keys eased along, in metres from the spot; its far twin stands at the same place in km
    // its height is over the ground beneath it (smoothed over a metre), so a hump never rises in front of the lens
    let gy = 0; for (const [dx, dz] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) gy += G(C.pos[0] + dx, C.pos[2] + dz) / 5;
    cam.position.set(C.pos[0], C.pos[1] + gy, C.pos[2]); cam.fov = C.fov; cam.updateProjectionMatrix(); cam.lookAt(...C.look);
    farCam.fov = C.fov; farCam.updateProjectionMatrix();
    farCam.position.set((X0 + C.pos[0]) / 1000, (BASE + cam.position.y) / 1000, (Z0 + C.pos[2]) / 1000); farCam.quaternion.copy(cam.quaternion);
    far.stars.position.copy(farCam.position);
    if (far.earth) {
      far.earth.position.copy(farCam.position).addScaledVector(far.earthFrame.dir, far.earthFrame.D); far.halo.position.copy(far.earth.position);
      far.earthFrame.U.C.value.copy(far.earth.position); far.earthFrame.U.R.value = far.earthFrame.R;
    }
    renderer.clear(); renderer.render(far.scene, farCam);
    renderer.clearDepth(); renderer.render(scene, cam);
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  window.__info = { stop: w.end, prints: PR.length, profile: Array.from({ length: 9 }, (_, i) => +G(-2.2 * i / 8, 15 * i / 8).toFixed(2)) };
  window.ready = 1;
}
setup();
</script></body></html>`;

// ---------------- timing and the camera ----------------
// The walk ends (feet together) at w.end (~5.2 s); then: eyes up to the Earth, a beat, the head sinks.
const TIMING = { lookUp: [5.4, 6.2], down: [7.0, 8.4] };
// camera keys [t, position (its y over the ground there), look-at, vertical fov] in metres from the spot (x east, y up, z south); the Earth is due
// north, 4.5° up: at the end the camera is 15 m behind him and a little to his left, low, on a long lens, so the
// Earth hangs over his helmet to the left and we see his helmet turn as it sinks
const KEYS = [
  [0.0, [-5.0, 4.2, 34], [0, 0.6, -20], 36],
  [6.0, [-1.45, 0.5, 15.8], [1.1, 2.4, -40], 19],
  [DUR, [-1.4, 0.48, 15.0], [1.1, 2.45, -40], 18],
];
function camAt(t) {
  let i = 0; while (i < KEYS.length - 2 && t > KEYS[i + 1][0]) i++;
  const [t0, p0, l0, f0] = KEYS[i], [t1, p1, l1, f1] = KEYS[i + 1];
  let u = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
  if (i === 0) u = u * u * u * (u * (6 * u - 15) + 10);   // the fly-in: eased in and out
  const mix = (a, b) => a.map((v, k) => v + (b[k] - v) * u);
  return { pos: mix(p0, p1), look: mix(l0, l1), fov: f0 + (f1 - f0) * u, ...TIMING };
}

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const files = { '/three.min.js': path.join(TOOLS, 'node_modules/three/build/three.min.js'),
    '/emblem.js': path.join(TOOLS, 'characters/emblem.js'), '/astronaut.js': path.join(TOOLS, 'characters/astronaut.js') };
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = req.url.split('?')[0];
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = files[u] || (u.startsWith('/data/') ? path.join(DATA, u.slice(6)) : u.startsWith('/site/') ? path.join(SITE_TEX, u.slice(6)) : null);
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.text().startsWith('[')) console.log(m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 1000 });
  console.log('ready', JSON.stringify(await p.evaluate(() => window.__info)));
  const save = async (t, file) => {
    const url = await p.evaluate(([t, c]) => window.__frame(t, c), [t, camAt(t)]);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) await save(t, path.join(WORK, `still_${t}.jpg`));
  } else {
    const dir = path.join(WORK, 'frames'); fs.mkdirSync(dir, { recursive: true });
    const n = Math.round(DUR * FPS);
    for (let i = 0; i < n; i++) { await save(i / FPS, path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`)); if (i % 30 === 0) console.log('frame', i, '/', n); }
  }
  await br.close(); srv.close();
})();
