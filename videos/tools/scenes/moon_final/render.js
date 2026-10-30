// The finale of the stick cartoon ("що з цією планетою не так"): the Nebozvid astronaut on the real Moon, near the
// south pole, walks a few steps toward the Earth hanging low over the hills, stops and looks at it. The camera starts
// a little way behind him (the relief and the Earth in view), flies in over his sunlit right shoulder and round to his
// face: the Earth and the black sky in his gold visor. Then he slowly lowers his head.
//
//   node scenes/moon_final/render.js stills 0,4,8   -> work/moon_final/still_<t>.jpg
//   node scenes/moon_final/render.js video          -> work/moon_final/frames/f_00000.jpg …
//
// Two passes each frame: (1) the far Moon of moon_meet (scenes/moon_meet/world.js: the LOLA/LROC relief of the site
// 'south', the stars, the Earth where it really hangs, ~4.5° over the northern horizon), in km; (2) after clearing the
// depth, the near ground in metres round the walk and the astronaut. The near ground is the same LOLA surface
// (exaggerated and bent the same way, so it meets the far one) plus what 63 m cells can't hold: broad swells, worn
// craters from half a metre to 80 m, the regolith's grain (a tiling texture and bump, as in marswalk) and the boot
// prints, fading out with distance. The Sun is the site's (6° up in the east): the craters' shadows are worked out
// exactly for their bowls, the figure's come from a shadow map onto a shadow-catching copy of the ground.
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const { moonWorld } = require('../moon_meet/world');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'moon_final');
const DATA = path.join(TOOLS, 'work', 'moon_meet', 'south'), SITE_TEX = path.resolve(TOOLS, '../../planetarium/textures');
const [mode = 'stills', list = '0'] = process.argv.slice(2);
const W = 720, H = 1280, FPS = 30, DUR = 11.0;
// the Earth drawn larger than life (the author, 31.10): twice its real 1.9° in the sky, 5.6 times in the visor
const EARTH_SKY = 2, VISOR_EARTH = +(process.env.VISOR_EARTH || 5.6);
// The walk ends (feet together) at ~5.2 s; then: eyes up to the Earth, a beat (the camera comes round to his face,
// the Earth in his visor), the head sinks.
const TIMING = { lookUp: [5.4, 6.2], down: [8.2, 9.8] };
// [t, azimuth°, distance m, height m, fov°, look-at offset [x, height, z]] (see shoot() in the page)
const CAM_KEYS = [
  [0.0, -9.5, 30, 4.2, 36, [0, 0.6, -24]],
  [3.0, -5, 14, 2.0, 30, [0, 1.1, -8]],
  [5.0, 35, 6.0, 1.7, 30, [0, 1.3, -1]],
  [6.6, 140, 3.0, 1.75, 30, [0, 1.75, -0.1]],
  [7.6, 168, 2.3, 1.82, 28, [0, 1.97, -0.2]],
  [DUR, 172, 2.05, 1.8, 28, [0, 1.97, -0.2]],
];
if (!fs.existsSync(path.join(DATA, 'meta.json'))) { console.log('first: python3 scenes/moon_meet/terrain_data.py south'); process.exit(1); }
const meta = JSON.parse(fs.readFileSync(path.join(DATA, 'meta.json')));
// the far Moon: the site's Earth (half lit, Ukraine on its lit side), as in moon_meet's last flight
const shot = { site: 'south', mesh: 1600, earth: [0, 4.5], earthFace: [49, 31, 40], earthLean: 28, earthshine: 2.5, earthScale: EARTH_SKY };
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
  // the walk's strip (x ~ 0, from z ~ 9 to -1): the larger craters kept off it
  const pathMask = (x, z) => 1 - (1 - smooth((Math.abs(x) - 1.0) / 1.5)) * (1 - smooth((z - 10) / 3)) * (1 - smooth((-z - 1.5) / 2));
  // the camera's corridor (from its start, 30 m south, round his right side to the front): no big craters in the way
  const corridor = (x, z) => { const u = Math.min(1, Math.max(0, (z - 2) / 30)), d = Math.abs(x + 5 * u); return Math.min(1, smooth((d - 7) / 10) + smooth((z - 38) / 10) + smooth((-z - 6) / 8)); };
  // craters on a grid of cells C (at most one per cell, radius r0…r1): adds to out[0] the height, multiplies out[1]
  // by the sunlight. A point in a bowl is lit if the ray to the Sun clears the rim on the sunward side.
  function craters(x, z, C, r0, r1, p, seed, k, out) {
    if (k <= 0) return;
    const ci = Math.floor(x / C), cj = Math.floor(z / C);
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
      if (hash2(i + seed, j) > p) continue;
      const cx = (i + hash2(i, j + seed)) * C, cz = (j + hash2(i - seed, j)) * C, r = r0 + (r1 - r0) * hash2(j, i + seed) ** 2;
      const px = x - cx, pz = z - cz, d = Math.hypot(px, pz) / r; if (d > 2.4) continue;
      const amp = r * (0.35 + 0.65 * hash2(i + 3 * seed, j + 7)) * k;     // older ones shallower, softer
      out[0] += amp * prof(d);
      if (d < 1.02) {
        const b = px * sx + pz * sz, c = px * px + pz * pz - r * r, tt = -b + Math.sqrt(Math.max(0, b * b - c));
        const clear = amp * prof(d) + tt * tanE - amp * RIM * 0.85;
        out[1] *= smooth(clear / (0.05 * r + 0.02) + 0.5);
      }
    }
  }
  // as on Mars (marswalk): broad rolling swells, few small craters and those worn soft, the fine grain in the shader
  const out = [0, 1];
  function detail(x, z) {
    out[0] = 0; out[1] = 1;
    const m = pathMask(x, z), cor = corridor(x, z), r = Math.hypot(x, z - 4), fade = 1 - smooth((r - 700) / 900);
    if (fade <= 0) return out;
    craters(x, z, 5.0, 0.3, 1.1, 0.22, 11, 0.45 * (0.3 + 0.7 * m), out);
    craters(x, z, 14, 1.2, 4.5, 0.4, 23, 0.8 * m * Math.min(1, 0.2 + cor), out);
    craters(x, z, 45, 5, 18, 0.6, 37, smooth((r - 12) / 10) * cor, out);
    craters(x, z, 190, 18, 75, 0.7, 53, cor * smooth((r - 30) / 30), out);
    out[0] += 0.9 * fbm(x * 0.035 + 5, z * 0.035, 3) * (0.5 + 0.5 * cor) + 0.22 * fbm(x * 0.17, z * 0.17, 3) + 0.035 * fbm(x * 1.1, z * 1.1, 2) * (0.4 + 0.6 * m);
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
    // the soil's brightness: patches of fresher (paler) and older (darker) regolith
    alb[q] = 1 + 0.16 * fbm(x * 0.02 + 3, z * 0.02, 3) + 0.08 * fbm(x * 0.3, z * 0.3, 2);
  }
  const idx = new Uint32Array((NR - 1) * NA * 6); let n = 0;
  for (let k = 0; k < NR - 1; k++) for (let a = 0; a < NA; a++) {
    const p0 = k * NA + a, p1 = k * NA + (a + 1) % NA, p2 = (k + 1) * NA + a, p3 = (k + 1) * NA + (a + 1) % NA;
    idx.set([p0, p1, p2, p1, p3, p2], n); n += 6;   // facing up
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('lit', new T.BufferAttribute(lit, 1)); geo.setAttribute('alb', new T.BufferAttribute(alb, 1));
  geo.setIndex(new T.BufferAttribute(idx, 1)); geo.computeVertexNormals();

  // the regolith's fine texture, as in marswalk: tiling value noise with grit and small clods (brightness), and the
  // same raised in a bump map; the shader lays it at two scales (2.2 m and 7.3 m, turned) so it never visibly repeats
  const grit = document.createElement('canvas'), bump = document.createElement('canvas');
  grit.width = grit.height = bump.width = bump.height = 1024;
  { const g = grit.getContext('2d'), bg = bump.getContext('2d'), im = g.createImageData(1024, 1024);
    const vp = (x, y, P) => {
      const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = k => ((k % P) + P) % P;
      const a = hash2(w(i), w(j)), b = hash2(w(i + 1), w(j)), c = hash2(w(i), w(j + 1)), d = hash2(w(i + 1), w(j + 1));
      return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
    for (let y = 0; y < 1024; y++) for (let x = 0; x < 1024; x++) {
      const nn = 0.42 * vp(x / 32, y / 32, 32) + 0.3 * vp(x / 16, y / 16, 64) + 0.18 * vp(x / 8, y / 8, 128) + 0.1 * vp(x / 4, y / 4, 256);
      const v = Math.min(255, Math.max(0, 175 + 150 * (nn - 0.5))), k = (y * 1024 + x) * 4;
      im.data[k] = im.data[k + 1] = im.data[k + 2] = v; im.data[k + 3] = 255;
    }
    g.putImageData(im, 0, 0); bg.filter = 'blur(1px)'; bg.drawImage(grit, 0, 0); bg.filter = 'none';
    let sd = 7; const rr = () => { sd = Math.imul(sd ^ (sd >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((sd >>> 0) % 1e6) / 1e6; };
    for (let i = 0; i < 3200; i++) {
      const x = rr() * 1024, y = rr() * 1024, r = 1.0 + 5 * rr() ** 4, sh = 120 + 110 * rr(), e = r * (0.7 + 0.3 * rr()), rot = rr() * 3;
      for (const ox of [-1024, 0, 1024]) for (const oy of [-1024, 0, 1024]) {
        const gs = sh | 0; g.fillStyle = 'rgba(' + gs + ',' + gs + ',' + gs + ',0.8)'; g.beginPath(); g.ellipse(x + ox, y + oy, r, e, rot, 0, 6.3); g.fill();
        bg.fillStyle = 'rgba(255,255,255,0.75)'; bg.beginPath(); bg.ellipse(x + ox, y + oy, r, e, rot, 0, 6.3); bg.fill(); }
    } }
  const tex = c => { const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 16; return t; };

  // ---------------- the walk ----------------
  const a = window.__makeAstronaut(T); await a.ready;
  // four steps north from 4.3 m out, then the walker's three short ones to a stop with the feet together
  const w = a.walk({ ground: G, from: [0, 4.3], heading: 0, steps: 4, start: 0.15 });
  const PR = w.prints.slice(0, 16);

  // the ground's light, as world.js lights the far relief (Lambert mixed with Lommel-Seeliger, shadows only lit by
  // the earthshine), with the soil's mottling and grain, the crater shadows, and the boot prints pressed in
  const U = { col: { value: null }, shd: { value: null }, sun: { value: sun }, es: { value: 2.5 }, tNow: { value: 0 },
    rg: { value: tex(grit) }, rb: { value: tex(bump) },
    prints: { value: Array.from({ length: 16 }, (_, i) => PR[i] ? new T.Vector4(PR[i].x, PR[i].z, PR[i].side === 'L' ? -1 : 1, PR[i].t) : new T.Vector4(0, 0, 0, 1e9)) }, np: { value: PR.length },
    dxN: { value: DX * (N - 1) }, off: { value: new T.Vector2(X0, Z0) } };
  const load = f => new Promise(r => new T.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }));
  [U.col.value, U.shd.value] = await Promise.all([load('/data/colour.jpg'), load('/data/shadow.png')]);
  const groundMat = new T.ShaderMaterial({ uniforms: U,
    vertexShader: \`attribute float lit; attribute float alb; varying float vLit, vAlb; varying vec3 vW, vN;
      void main() { vLit = lit; vAlb = alb; vN = normal; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }\`,
    fragmentShader: \`uniform sampler2D col, shd, rg, rb; uniform vec3 sun; uniform float es, tNow, dxN; uniform vec2 off; uniform vec4 prints[16]; uniform int np;
      varying float vLit, vAlb; varying vec3 vW, vN;
      // the grain's slope at one scale: the bump map's differences, as metres of height per metre
      vec2 slope(vec2 t, float size, float hgt) {
        float e = 1.0 / 1024.0;
        return vec2(texture2D(rb, t + vec2(e, 0.0)).r - texture2D(rb, t - vec2(e, 0.0)).r,
                    texture2D(rb, t + vec2(0.0, e)).r - texture2D(rb, t - vec2(0.0, e)).r) / (2.0 * e * size) * hgt;
      }
      void main() {
        vec2 uv = vec2((vW.x + off.x) / dxN + 0.5, 0.5 - (vW.z + off.y) / dxN);
        float dist = length(cameraPosition - vW);
        mat2 rot = mat2(0.8, -0.6, 0.6, 0.8);
        vec2 t1 = vW.xz / 2.2, t2 = rot * vW.xz / 7.3;
        float gr = 0.6 * texture2D(rg, t1).r + 0.4 * texture2D(rg, t2).r;
        vec3 c = pow(texture2D(col, uv).rgb, vec3(2.2)) * vAlb * mix(1.0, gr / 0.686, 0.75);
        vec3 n = normalize(vN);
        vec2 sl = slope(t1, 2.2, 0.006) * (1.0 - smoothstep(5.0, 30.0, dist));
        vec2 g2 = slope(t2, 7.3, 0.02) * (1.0 - smoothstep(15.0, 90.0, dist));
        vec2 s2 = vec2(0.8 * g2.x - 0.6 * g2.y, 0.6 * g2.x + 0.8 * g2.y);   // back from the turned texture to x, z
        n = normalize(n - vec3(sl.x + s2.x, 0.0, sl.y + s2.y));
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

  // ---------------- the astronaut's light ----------------
  scene.add(a.group);
  // the Sun: a shadow map just round the figure (its long shadow runs along the light, so the depth range holds it)
  const key = new T.DirectionalLight(0xfff6ea, 3.2);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0003; key.shadow.normalBias = 0.012;
  const SB = 2.2; Object.assign(key.shadow.camera, { left: -SB, right: SB, top: SB, bottom: -SB, near: 1, far: 120 });
  scene.add(key, key.target);
  // earthshine from the north, faint and blue; the sunlit ground below, grey
  // (from up high, so its glint on the visor stays clear of the Earth's reflection)
  const fill = new T.DirectionalLight(0x9db8ff, 0.22); fill.position.set(-0.9, 1.0, -0.5); scene.add(fill);
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
  // the far Moon (km) seen from a point of the near scene (m): stars round it, the Earth hung at its distance
  function farAt(p, earthK) {
    const f = new T.Vector3((X0 + p.x) / 1000, (BASE + p.y) / 1000, (Z0 + p.z) / 1000);
    far.stars.position.copy(f);
    far.earth.position.copy(f).addScaledVector(far.earthFrame.dir, far.earthFrame.D); far.halo.position.copy(far.earth.position);
    const R = far.earthFrame.R * earthK;
    far.earth.scale.setScalar(R); far.halo.scale.setScalar(R);
    far.earthFrame.U.C.value.copy(far.earth.position); far.earthFrame.U.R.value = R;
    return f;
  }

  // ---------------- the visor's reflection ----------------
  // what the gold visor mirrors, from where his helmet will be when he stops: the far Moon, the sky and the Earth in
  // linear light, rendered once into a cube. The Earth in it is ${VISOR_EARTH}× life size (a true 1.9° Earth would be a speck
  // of a few pixels on the curved glass), and it is also laid over the gold by itself, in its own colours, the way the
  // clear outer coat would show a bright Earth (under the gold film alone it would turn a dull olive)
  w.update(w.end + 0.5); a.group.updateMatrixWorld(true);
  const HEAD0 = a.joints.head.localToWorld(new T.Vector3(0, 0.16, 0));
  const vm = a.materials.find(m => m.isMeshPhysicalMaterial && m.metalness === 1);
  const terrain = far.scene.children.find(o => o.isMesh && o.material.uniforms && o.material.uniforms.nrm);
  function cube(size, earthOnly) {
    const rt = new T.WebGLCubeRenderTarget(size), cc = new T.CubeCamera(0.001, 20000, rt);
    cc.position.copy(farAt(HEAD0, ${VISOR_EARTH / EARTH_SKY}));
    const tm = terrain.material;
    if (earthOnly) { terrain.material = new T.MeshBasicMaterial({ color: 0 }); far.stars.visible = false; }
    far.og.value = 1;
    renderer.autoClear = true; cc.update(renderer, far.scene); renderer.autoClear = false;
    far.og.value = 1 / 2.2; terrain.material = tm; far.stars.visible = true;
    return rt.texture;
  }
  vm.envMap = new T.PMREMGenerator(renderer).fromCubemap(cube(1024, false)).texture; vm.needsUpdate = true;
  { const earthCube = cube(1024, true);
    const ov = new T.ShaderMaterial({ uniforms: { env: { value: earthCube } }, transparent: true, depthWrite: false,
      vertexShader: 'varying vec3 vW, vN; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: \`uniform samplerCube env; varying vec3 vW, vN;
        void main() {
          vec3 r = reflect(normalize(vW - cameraPosition), normalize(vN));
          vec3 e = textureCube(env, r).rgb * 1.15;
          float k = clamp(max(e.r, max(e.g, e.b)) * 5.0, 0.0, 0.92);
          gl_FragColor = vec4(pow(e / max(k, 1e-3) * min(k, 1.0), vec3(1.0 / 2.2)), k);
        }\` });
    let vis = null; a.group.traverse(o => { if (o.isMesh && o.material === vm) vis = o; });
    const m = new T.Mesh(vis.geometry, ov);
    m.position.copy(vis.position); m.quaternion.copy(vis.quaternion); m.scale.copy(vis.scale).multiplyScalar(1.004);
    m.renderOrder = 2; vis.parent.add(m); }

  // ---------------- the camera ----------------
  // keys [t, azimuth round him (0 behind = south, 90 his right = east, 180 in front), distance, height over the ground
  // beneath the camera, vertical fov, look-at offset from him (x, height over the ground, z)]; eased through with a
  // monotone cubic, so nothing overshoots. Behind him at first, far and a little high, looking past him to the Earth;
  // in over his right shoulder (the sunlit side) as he stops, round to the front, close, looking up at the visor.
  const KEYS = ${JSON.stringify(CAM_KEYS)};
  function pchip(xs, ys, x) {
    const n = xs.length; if (x <= xs[0]) return ys[0]; if (x >= xs[n - 1]) return ys[n - 1];
    const d = [], m = [];
    for (let i = 0; i < n - 1; i++) d.push((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]));
    for (let i = 0; i < n; i++) m.push(i === 0 ? d[0] : i === n - 1 ? d[n - 2] : d[i - 1] * d[i] <= 0 ? 0 : 2 / (1 / d[i - 1] + 1 / d[i]));
    m[0] = 0; m[n - 1] = 0;                                  // starts and ends at rest
    let i = 0; while (x > xs[i + 1]) i++;
    const h = xs[i + 1] - xs[i], u = (x - xs[i]) / h, u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * ys[i] + (u3 - 2 * u2 + u) * h * m[i] + (-2 * u3 + 3 * u2) * ys[i + 1] + (u3 - u2) * h * m[i + 1];
  }
  const ch = k => KEYS.map(r => r[k]);
  const TS = ch(0);
  function reference(t) {                                    // his walk's calm line, averaged over ±0.4 s
    let x = 0, z = 0; for (let k = -2; k <= 2; k++) { const p = w.track(t + 0.2 * k); x += p[0] / 5; z += p[1] / 5; } return [x, z];
  }
  function shoot(t) {
    const [rx, rz] = reference(t), ph = pchip(TS, ch(1), t) * Math.PI / 180, d = pchip(TS, ch(2), t);
    const cx = rx + d * Math.sin(ph), cz = rz + d * Math.cos(ph);
    let gy = 0; for (const [dx, dz] of [[0, 0], [0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) gy += G(cx + dx, cz + dz) / 5;
    cam.position.set(cx, gy + pchip(TS, ch(3), t), cz);
    cam.fov = pchip(TS, ch(4), t); cam.updateProjectionMatrix();
    const lo = [0, 1, 2].map(k => pchip(TS, KEYS.map(r => r[5][k]), t));
    cam.lookAt(rx + lo[0], G(rx, rz) + lo[1], rz + lo[2]);
  }

  window.__frame = (t, C) => {
    // the figure: the walk, then at rest he lifts his eyes to the Earth, holds, and lets his head sink, shoulders falling
    const up = smooth((t - C.lookUp[0]) / (C.lookUp[1] - C.lookUp[0])), down = smooth((t - C.down[0]) / (C.down[1] - C.down[0]));
    w.update(t, { lean: -0.1 * down, crouch: 0.015 * down });
    const J = a.joints;
    J.head.rotation.x += 0.2 * up * (1 - down) - 0.3 * down;
    J.head.rotation.y += 0.06 * down;
    J.body.rotation.x -= 0.06 * down;
    for (const sd of ['L', 'R']) { J['shoulder' + sd].rotation.z *= 1 - 0.5 * down; J['shoulder' + sd].rotation.x -= 0.06 * down; }
    a.group.updateMatrixWorld(true);
    U.tNow.value = t;
    aimSun(a.group.position.clone());
    shoot(t);
    farCam.fov = cam.fov; farCam.updateProjectionMatrix();
    farCam.position.copy(farAt(cam.position, 1)); farCam.quaternion.copy(cam.quaternion);
    renderer.clear(); renderer.render(far.scene, farCam);
    renderer.clearDepth(); renderer.render(scene, cam);
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  window.__info = { stop: w.end, prints: PR.length, head: HEAD0.toArray().map(v => +v.toFixed(2)) };
  window.ready = 1;
}
setup();
</script></body></html>`;

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
  p.on('console', m => { if (m.type() === 'error' && !m.text().includes('GL Driver')) console.log(m.text().slice(0, 300)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 1000 });
  console.log('ready', JSON.stringify(await p.evaluate(() => window.__info)));
  const save = async (t, file) => {
    const url = await p.evaluate(([t, c]) => window.__frame(t, c), [t, TIMING]);
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
