// «Скільки ти важиш на інших планетах?» — the in-page half of render.js: the worlds, the bathroom scale, what the
// astronaut does on each, and the camera. render.js serves this with three.js, the astronaut and (for the Moon) the
// moon_meet relief; window.__CFG holds the shots. window.__frame(t) draws the frame at time t (s) and returns a JPEG.
//
// Each frame is two passes: the sky (a dome with the world's air, the Sun, stars, a moon or planet hung in it — or, on
// the Moon, the real far relief and the Earth of moon_meet/world.js, in km), then, depth cleared, the near world in
// metres: the ground (a polar mesh round the scale, fine near it; heights from a noise recipe per world — swells,
// worn craters with their exact shadows, dunes, plates, far mountains — bent to the body's curvature; on the Moon the
// LOLA surface itself) or, on the gas giants and the Sun, a platform over a deck of cloud or the boiling photosphere;
// then the scale and the astronaut. The ground is lit like the far Moon (Lambert mixed with Lommel-Seeliger) plus
// the sky's light and the haze of the air.
(() => {
  const T = THREE, CFG = window.__CFG, W = CFG.W, H = CFG.H;
  const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const lerp = (a, b, u) => a + (b - a) * u;
  const hash2 = (i, j) => { let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
  function vn(x, z) {
    const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j, u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
    const a = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  const fbm = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { s += a * (vn(x * f + 17 * k, z * f - 9 * k) - 0.5); a *= 0.5; f *= 2.03; } return s; };
  const ridged = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { const r = 1 - Math.abs(2 * vn(x * f + 5 * k, z * f + 11 * k) - 1); s += a * r * r; a *= 0.5; f *= 2.1; } return s / 1.75; };
  const dirOf = (az, el) => { const a = az * Math.PI / 180, e = el * Math.PI / 180; return new T.Vector3(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)); };
  const V3 = a => new T.Vector3(...a);

  // ---------------- the renderer, the astronaut, the scale ----------------
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H); document.body.appendChild(renderer.domElement);
  renderer.outputEncoding = T.sRGBEncoding; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap; renderer.autoClear = false;
  const cam = new T.PerspectiveCamera(35, W / H, 0.05, 20000), skyCam = new T.PerspectiveCamera(35, W / H, 0.05, 20000);
  const a = window.__makeAstronaut(T);

  // the scale: a white body with rounded corners, a dark glass top, an LCD at the front (toward -z, the way he faces
  // before the world turns him); the display is a canvas redrawn when its text changes
  const SCALE = { w: 0.46, d: 0.40, h: 0.052 };
  const scale = new T.Group();
  { const r = 0.05, w = SCALE.w / 2 - r, d = SCALE.d / 2 - r, sh = new T.Shape();
    sh.moveTo(-w, -d - r); sh.lineTo(w, -d - r); sh.quadraticCurveTo(w + r, -d - r, w + r, -d); sh.lineTo(w + r, d); sh.quadraticCurveTo(w + r, d + r, w, d + r);
    sh.lineTo(-w, d + r); sh.quadraticCurveTo(-w - r, d + r, -w - r, d); sh.lineTo(-w - r, -d); sh.quadraticCurveTo(-w - r, -d - r, -w, -d - r);
    const body = new T.ExtrudeGeometry(sh, { depth: SCALE.h - 0.012, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 3, curveSegments: 10 });
    body.rotateX(-Math.PI / 2); body.translate(0, 0.006, 0);
    const bm = new T.Mesh(body, new T.MeshStandardMaterial({ color: 0xf2f2ef, roughness: 0.35, metalness: 0.05 })); bm.castShadow = bm.receiveShadow = true; scale.add(bm);
    const top = new T.Mesh(new T.ShapeGeometry(sh, 10), new T.MeshPhysicalMaterial({ color: 0x1b1d22, roughness: 0.08, metalness: 0.2, clearcoat: 1 }));
    top.rotation.x = -Math.PI / 2; top.position.y = SCALE.h + 0.0015; top.scale.set(0.93, 0.93, 1); top.receiveShadow = true; scale.add(top);
  }
  const lcd = document.createElement('canvas'); lcd.width = 256; lcd.height = 96;
  const lcdTex = new T.CanvasTexture(lcd); lcdTex.encoding = T.sRGBEncoding;
  { const m = new T.Mesh(new T.PlaneGeometry(0.15, 0.056), new T.MeshBasicMaterial({ map: lcdTex, toneMapped: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(0, SCALE.h + 0.003, -SCALE.d / 2 + 0.05); scale.add(m); }
  let lcdText = null;
  function setLCD(text) {
    if (text === lcdText) return; lcdText = text;
    const g = lcd.getContext('2d');
    g.fillStyle = '#0b1a24'; g.fillRect(0, 0, 256, 96);
    g.fillStyle = '#7fe3ff'; g.font = 'bold 66px "DejaVu Sans Mono", monospace'; g.textAlign = 'right'; g.textBaseline = 'middle';
    g.shadowColor = '#3ad0ff'; g.shadowBlur = 12; g.fillText(text, 236, 52);
    lcdTex.needsUpdate = true;
  }

  // ---------------- the regolith's fine texture (as marswalk / moon_final) ----------------
  const grit = document.createElement('canvas'), bump = document.createElement('canvas');
  grit.width = grit.height = bump.width = bump.height = 1024;
  { const g = grit.getContext('2d'), bg = bump.getContext('2d'), im = g.createImageData(1024, 1024);
    const vp = (x, y, P) => {
      const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = k => ((k % P) + P) % P;
      const p = hash2(w(i), w(j)), b = hash2(w(i + 1), w(j)), c = hash2(w(i), w(j + 1)), d = hash2(w(i + 1), w(j + 1));
      return p + (b - p) * u + (c - p) * v + (p - b - c + d) * u * v; };
    for (let y = 0; y < 1024; y++) for (let x = 0; x < 1024; x++) {
      const nn = 0.42 * vp(x / 32, y / 32, 32) + 0.3 * vp(x / 16, y / 16, 64) + 0.18 * vp(x / 8, y / 8, 128) + 0.1 * vp(x / 4, y / 4, 256);
      const v = Math.min(255, Math.max(0, 175 + 150 * (nn - 0.5))), k = (y * 1024 + x) * 4;
      im.data[k] = im.data[k + 1] = im.data[k + 2] = v; im.data[k + 3] = 255;
    }
    g.putImageData(im, 0, 0); bg.filter = 'blur(1px)'; bg.drawImage(grit, 0, 0); bg.filter = 'none';
    let sd = 7; const rr = () => { sd = Math.imul(sd ^ (sd >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((sd >>> 0) % 1e6) / 1e6; };
    for (let i = 0; i < 3200; i++) {
      const x = rr() * 1024, y = rr() * 1024, r = 1.0 + 5 * rr() ** 4, sh = (120 + 110 * rr()) | 0, e = r * (0.7 + 0.3 * rr()), rot = rr() * 3;
      for (const ox of [-1024, 0, 1024]) for (const oy of [-1024, 0, 1024]) {
        g.fillStyle = 'rgba(' + sh + ',' + sh + ',' + sh + ',0.8)'; g.beginPath(); g.ellipse(x + ox, y + oy, r, e, rot, 0, 6.3); g.fill();
        bg.fillStyle = 'rgba(255,255,255,0.75)'; bg.beginPath(); bg.ellipse(x + ox, y + oy, r, e, rot, 0, 6.3); bg.fill(); }
    } }
  const tileTex = c => { const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 16; return t; };
  const GRIT = tileTex(grit), BUMP = tileTex(bump);
  const WHITE = new T.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); WHITE.needsUpdate = true;
  const texLoad = f => new Promise(r => new T.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }));

  // ---------------- the worlds ----------------
  // sun [azimuth from his front (-z) clockwise seen from above, elevation], light colours as linear multipliers; sky
  // [zenith, horizon] (gamma-encoded colours); fog k per metre; ground: albedo, how strong the grain, the recipe
  const WORLDS = CFG.worlds;

  // craters on a grid of cells C (at most one per cell, radius r0…r1): adds height to out[0], multiplies the sunlight
  // in out[1] (a point in a bowl is lit if the ray to the Sun clears the rim on the sunward side)
  const RIM = 0.055;
  const prof = d => d < 1 ? 0.2 * (d * d - 1) + RIM * Math.exp(-(((d - 1) / 0.22) ** 2)) : RIM * Math.exp(-(((d - 1) / 0.4) ** 2));
  function craters(x, z, C, r0, r1, p, seed, k, out, S) {
    if (k <= 0) return;
    const ci = Math.floor(x / C), cj = Math.floor(z / C);
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
      if (hash2(i + seed, j) > p) continue;
      const cx = (i + hash2(i, j + seed)) * C, cz = (j + hash2(i - seed, j)) * C, r = r0 + (r1 - r0) * hash2(j, i + seed) ** 2;
      const px = x - cx, pz = z - cz, d = Math.hypot(px, pz) / r; if (d > 2.4) continue;
      const amp = r * (0.35 + 0.65 * hash2(i + 3 * seed, j + 7)) * k;
      out[0] += amp * prof(d);
      if (d < 1.02 && S.tanE > 0) {
        const b = px * S.sx + pz * S.sz, c = px * px + pz * pz - r * r, tt = -b + Math.sqrt(Math.max(0, b * b - c));
        out[1] *= 1 - S.hard * (1 - smooth((amp * prof(d) + tt * S.tanE - amp * RIM * 0.85) / (0.05 * r + 0.02) + 0.5));
      }
    }
  }

  // a world's ground height (m, the scale's spot at the origin) and sunlight: the recipe's parts, kept calm round the
  // scale (it stands on level ground) and fading out far away, bent to the body's curvature
  function recipe(wd, S, dem) {
    const g = wd.ground, out = [0, 1];
    return (x, z) => {
      out[0] = 0; out[1] = 1;
      const r = Math.hypot(x, z), calm = smooth((r - 0.9) / 2.5), fade = 1 - smooth((r - 900) / 1200);
      for (const [C, r0, r1, p, seed] of g.craters || []) craters(x, z, C, r0, r1, p, seed, (C > 20 ? smooth((r - 8 * C / 20) / 10) : 1) * calm * (g.craterK || 1), out, S);
      out[0] += (g.swell || 0.6) * fbm(x * 0.035 + 5, z * 0.035, 3) * (0.3 + 0.7 * calm) + 0.18 * fbm(x * 0.17, z * 0.17, 3) * calm + 0.03 * fbm(x * 1.1, z * 1.1, 2);
      if (g.dunes) {            // long crests across the wind, a gentle back and a steeper lee face
        const ph = (x * 0.35 + z * 0.94) / g.dunes[0] + 2.5 * fbm(x * 0.02 + 9, z * 0.02, 2), f = ph - Math.floor(ph);
        out[0] += g.dunes[1] * (f < 0.72 ? smooth(f / 0.72) : smooth((1 - f) / 0.28)) * calm * (0.5 + vn(x * 0.03, z * 0.03));
      }
      if (g.plates) {           // Venus: flat slabs of lava, stepped, cracked
        const q = (fbm(x * 0.12, z * 0.12, 3) + 0.5) * 5, fl = Math.floor(q);
        out[0] += g.plates * (fl + smooth((q - fl - 0.85) / 0.15)) * calm;
      }
      out[0] *= fade; out[1] = 1 - (1 - out[1]) * fade;
      if (g.mountains) {        // far off: a ring of ridges against the sky
        const [A, r0, L] = g.mountains;
        out[0] += A * smooth((r - r0) / (r0 * 1.5)) * (0.35 + ridged(x / L + 3, z / L, 4)) * (0.75 + 0.25 * Math.sin(Math.atan2(x, z) * 3 + 1));
      }
      if (dem) out[0] += dem(x, z);
      else out[0] -= r * r / (2 * wd.R);
      return out;
    };
  }

  // the sky dome (gamma-encoded output, like the ground): the air from horizon to zenith, the Sun's disc and glow
  const domeMat = new T.ShaderMaterial({ side: T.BackSide, depthWrite: false,
    uniforms: { zen: { value: new T.Color() }, hor: { value: new T.Color() }, sunD: { value: new T.Vector3() }, sunC: { value: new T.Color() },
      cosR: { value: 0.9999 }, glow: { value: 0 }, haze: { value: 0 } },
    vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 zen, hor, sunD, sunC; uniform float cosR, glow, haze; varying vec3 vD;
      void main() {
        vec3 d = normalize(vD); float up = max(d.y, 0.0), m = dot(d, sunD);
        vec3 c = mix(hor, zen, pow(up, 0.55)) * (d.y < 0.0 ? 0.85 : 1.0);
        c += sunC * (smoothstep(cosR - (1.0 - cosR) * 0.15, cosR, m) * 1.6);                 // the disc
        c += sunC * glow * (pow(max(m, 0.0), 900.0) * 1.2 + pow(max(m, 0.0), 60.0) * 0.25 + pow(max(m, 0.0), 6.0) * 0.06 * haze);
        gl_FragColor = vec4(c, 1.0);
      }` });
  function starsMesh(n, seed) {
    const g = new T.BufferGeometry(), p = [], c = []; let s = seed; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < n; i++) { const u = rnd() * 2 - 1, an = rnd() * 6.283, r = Math.sqrt(1 - u * u), b = 0.15 + 0.6 * Math.pow(rnd(), 3);
      p.push(r * Math.cos(an) * 900, u * 900, r * Math.sin(an) * 900); c.push(b, b, b * 1.05); }
    g.setAttribute('position', new T.Float32BufferAttribute(p, 3)); g.setAttribute('color', new T.Float32BufferAttribute(c, 3));
    return new T.Points(g, new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  }

  // the ground's light: as world.js lights the far Moon, plus the sky's light and the air's haze
  function groundMaterial(U) {
    return new T.ShaderMaterial({ uniforms: U,
      vertexShader: `attribute float lit; varying float vLit; varying vec3 vW, vN;
        void main() { vLit = lit; vN = normal; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
      fragmentShader: `uniform sampler2D col, shd, rg, rb; uniform vec3 sun, sunC, amb, alb, fogC; uniform float fogK, grain, dxN, mapK; uniform vec2 off;
        varying float vLit; varying vec3 vW, vN;
        vec2 slope(vec2 t, float size, float hgt) {
          float e = 1.0 / 1024.0;
          return vec2(texture2D(rb, t + vec2(e, 0.0)).r - texture2D(rb, t - vec2(e, 0.0)).r,
                      texture2D(rb, t + vec2(0.0, e)).r - texture2D(rb, t - vec2(0.0, e)).r) / (2.0 * e * size) * hgt;
        }
        void main() {
          vec2 uv = vec2((vW.x + off.x) / dxN + 0.5, 0.5 - (vW.z + off.y) / dxN);
          float dist = length(cameraPosition - vW);
          vec2 t1 = vW.xz / 2.2, t2 = mat2(0.8, -0.6, 0.6, 0.8) * vW.xz / 7.3;
          float gr = 0.6 * texture2D(rg, t1).r + 0.4 * texture2D(rg, t2).r;
          vec3 c = mix(vec3(1.0), pow(texture2D(col, uv).rgb, vec3(2.2)), mapK) * alb * mix(1.0, gr / 0.686, grain);
          vec2 sl = slope(t1, 2.2, 0.006) * (1.0 - smoothstep(5.0, 30.0, dist));
          vec2 g2 = slope(t2, 7.3, 0.02) * (1.0 - smoothstep(15.0, 90.0, dist));
          vec3 n = normalize(normalize(vN) - vec3(sl.x + 0.8 * g2.x - 0.6 * g2.y, 0.0, sl.y + 0.6 * g2.x + 0.8 * g2.y));
          float mu0 = max(dot(n, sun), 0.0), mu = max(dot(n, normalize(cameraPosition - vW)), 0.05);
          float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.35);
          float s = texture2D(shd, uv).r * vLit;
          vec3 o = c * (sunC * lit * s + amb * (0.55 + 0.45 * n.y));
          o = pow(o, vec3(1.0 / 2.2));
          o = mix(o, fogC, 1.0 - exp(-dist * fogK));
          gl_FragColor = vec4(o, 1.0);
        }` });
  }
  function polarGeometry(G, Rmax, NA) {
    const rings = [0]; { let r = 0; while (r < 10) { r += 0.05; rings.push(r); } while (r < Rmax) { r *= 1 + 2 * Math.PI / NA; rings.push(r); } }
    const NR = rings.length, pos = new Float32Array(NR * NA * 3), lit = new Float32Array(NR * NA);
    for (let k = 0; k < NR; k++) for (let i = 0; i < NA; i++) {
      const an = (i + 0.5 * (k & 1)) / NA * 2 * Math.PI, x = rings[k] * Math.cos(an), z = rings[k] * Math.sin(an), q = k * NA + i, o = G(x, z);
      pos[q * 3] = x; pos[q * 3 + 1] = o[0]; pos[q * 3 + 2] = z; lit[q] = o[1];
    }
    const idx = new Uint32Array((NR - 1) * NA * 6); let n = 0;
    for (let k = 0; k < NR - 1; k++) for (let i = 0; i < NA; i++) {
      const p0 = k * NA + i, p1 = k * NA + (i + 1) % NA, p2 = (k + 1) * NA + i, p3 = (k + 1) * NA + (i + 1) % NA;
      idx.set([p0, p1, p2, p1, p3, p2], n); n += 6;
    }
    const geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('lit', new T.BufferAttribute(lit, 1));
    geo.setIndex(new T.BufferAttribute(idx, 1)); geo.computeVertexNormals();
    return { geo, idx, rings, NA };
  }
  // a textured body hung in the sky (Charon, Io, Saturn…), lit by the Sun: angular size in degrees
  function skyBody(tex, dir, deg, sun, extra) {
    const D = 800, m = new T.Mesh(new T.SphereGeometry(D * Math.tan(deg / 2 * Math.PI / 180), 96, 48), new T.ShaderMaterial({
      uniforms: { map: { value: tex }, sun: { value: sun }, k: { value: (extra && extra.k) || 1.6 } },
      vertexShader: 'varying vec2 vUv; varying vec3 vN; void main() { vUv = uv; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform sampler2D map; uniform vec3 sun; uniform float k; varying vec2 vUv; varying vec3 vN;
        void main() { vec3 c = pow(texture2D(map, vUv).rgb, vec3(2.2)) * max(dot(normalize(vN), sun), 0.0) * k; gl_FragColor = vec4(pow(c, vec3(1.0 / 2.2)), 1.0); }` }));
    m.position.copy(dir).multiplyScalar(D); m.rotation.set(0.3, 2.0, 0.2); return m;
  }

  // ---------------- building a world ----------------
  let cur = null;
  async function build(name) {
    if (cur && cur.name === name) return cur;
    if (cur) {                            // free the last world (not the figure or the scale, which move on), take off the wings
      const free = o => { if (o === a.group || o === scale) return; if (o.geometry) o.geometry.dispose(); o.children.forEach(free); };
      free(cur.near); free(cur.sky);
      (cur.wings || []).forEach(m => { m.parent.remove(m); m.geometry.dispose(); });
    }
    const wd = WORLDS[name], W0 = { name, wd };
    const sun = dirOf(...(wd.sun || [0, 10])), sunH = Math.hypot(sun.x, sun.z) || 1;
    const S = { tanE: sun.y / sunH, sx: sun.x / sunH, sz: sun.z / sunH, hard: wd.shadowHard == null ? 1 : wd.shadowHard };
    const near = new T.Scene(), sky = new T.Scene();
    W0.near = near; W0.sky = sky; W0.sun = sun;
    let dem = null, U;
    if (wd.moon) {                        // the real Moon: the far relief of moon_meet, the near ground on its LOLA heights
      const far = window.__moon || (window.__moon = await buildMoon());
      const meta = CFG.moonMeta, hb = far.hb, N = meta.n, DX = meta.dx, EX = meta.ex, R = meta.R, HALF = (N - 1) / 2, [X0, Z0] = CFG.moonSpot;
      const raw = (x, z) => {
        const gx = (X0 + x) / DX + HALF, gz = (Z0 + z) / DX + HALF;
        const i = Math.min(N - 2, Math.max(0, Math.floor(gx))), j = Math.min(N - 2, Math.max(0, Math.floor(gz))), fx = gx - i, fz = gz - j;
        const h = (hb[j * N + i] * (1 - fx) + hb[j * N + i + 1] * fx) * (1 - fz) + (hb[(j + 1) * N + i] * (1 - fx) + hb[(j + 1) * N + i + 1] * fx) * fz;
        const X = X0 + x, Z = Z0 + z; return h * EX - (X * X + Z * Z) / (2 * R);
      };
      const BASE = raw(0, 0); dem = (x, z) => raw(x, z) - BASE;
      sun.copy(far.sun); const h = Math.hypot(sun.x, sun.z); Object.assign(S, { tanE: sun.y / h, sx: sun.x / h, sz: sun.z / h });
      W0.far = far; W0.farAt = p => new T.Vector3((X0 + p.x) / 1000, (BASE + p.y) / 1000, (Z0 + p.z) / 1000);
      const [col, shd] = await Promise.all([texLoad('/moon/colour.jpg'), texLoad('/moon/shadow.png')]);
      U = { col: { value: col }, shd: { value: shd }, mapK: { value: 1 }, dxN: { value: DX * (N - 1) }, off: { value: new T.Vector2(X0, Z0) } };
    } else U = { col: { value: WHITE }, shd: { value: WHITE }, mapK: { value: 0 }, dxN: { value: 1 }, off: { value: new T.Vector2() } };
    Object.assign(U, { sun: { value: sun }, sunC: { value: V3(wd.sunC) }, amb: { value: V3(wd.amb) }, alb: { value: V3(wd.alb || [1, 1, 1]) },
      fogC: { value: new T.Color(...(wd.fog ? wd.fog[0] : [0, 0, 0])) }, fogK: { value: wd.fog ? wd.fog[1] : 0 }, grain: { value: wd.grain == null ? 0.75 : wd.grain },
      rg: { value: GRIT }, rb: { value: BUMP } });

    // the ground, or a platform over cloud / photosphere
    let G;
    if (wd.ground) {
      const Gr = recipe(wd, S, dem);
      G = (x, z) => Gr(x, z)[0];
      const pg = polarGeometry(Gr, wd.Rmax || 3000, 640);
      const ground = new T.Mesh(pg.geo, groundMaterial(U)); ground.frustumCulled = false; near.add(ground);
      const KR = pg.rings.findIndex(r => r > 25), sg = new T.BufferGeometry();     // the figure's shadow, caught on a copy
      sg.setAttribute('position', pg.geo.attributes.position); sg.setAttribute('normal', pg.geo.attributes.normal);
      sg.setIndex(new T.BufferAttribute(pg.idx.slice(0, KR * pg.NA * 6), 1));
      const sh = new T.Mesh(sg, new T.ShadowMaterial({ opacity: wd.shadowOpacity || 0.85, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }));
      sh.receiveShadow = true; sh.frustumCulled = false; near.add(sh);
    } else {
      G = () => 0;
      const plat = new T.Mesh(new T.CylinderGeometry(1.7, 1.45, 0.2, 64), new T.MeshStandardMaterial({ color: 0x8d939c, metalness: 0.85, roughness: 0.35 }));
      plat.position.y = -0.1; plat.receiveShadow = true; near.add(plat);
      const rim = new T.Mesh(new T.TorusGeometry(1.7, 0.025, 8, 96), new T.MeshBasicMaterial({ color: 0x9fe8ff, toneMapped: false })); rim.rotation.x = Math.PI / 2; near.add(rim);
      const deck = new T.Mesh(new T.CircleGeometry(9000, 128), new T.ShaderMaterial({
        uniforms: { a: { value: new T.Color(...wd.deck[0]) }, b: { value: new T.Color(...wd.deck[1]) }, c: { value: new T.Color(...wd.deck[2]) },
          fogC: U.fogC, fogK: U.fogK, sun: U.sun, tt: { value: 0 }, glow: { value: wd.deckGlow || 0 } },
        vertexShader: 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
        fragmentShader: `uniform vec3 a, b, c, fogC, sun; uniform float fogK, tt, glow; varying vec3 vW;
          float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
          float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
          float fb(vec2 p) { float s = 0.0, k = 0.5; for (int i = 0; i < 6; i++) { s += k * n(p); p = p * 2.03 + vec2(1.7, 9.2); k *= 0.5; } return s; }
          void main() {
            vec2 p = vW.xz / 70.0 + vec2(tt * 0.03, 0.0);
            float w = fb(p + vec2(fb(p * 0.7) * 2.0, 0.0)), band = 0.5 + 0.5 * sin(vW.z / 260.0 + 3.0 * fb(p * 0.3));
            vec3 col = mix(mix(a, b, smoothstep(0.35, 0.65, w)), c, smoothstep(0.55, 0.9, band) * 0.6);
            if (glow > 0.0) {                       // the photosphere: hot cells with dark lanes, boiling
              vec2 q = vW.xz / 5.0 + vec2(fb(vW.xz / 9.0) * 1.2, tt * 0.05); vec2 g = floor(q), f = fract(q); float d1 = 9.0, d2 = 9.0;
              for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) { vec2 o = vec2(float(i), float(j)); vec2 r = o + vec2(h(g + o), h(g + o + 7.3)) + 0.25 * sin(tt + 6.0 * h(g + o)) - f; float dd = dot(r, r); if (dd < d1) { d2 = d1; d1 = dd; } else if (dd < d2) d2 = dd; }
              float lane = smoothstep(0.0, 0.45, sqrt(d2) - sqrt(d1)), core = smoothstep(0.0, 0.8, 1.0 - 1.2 * sqrt(d1));
              col = mix(c, mix(b, a, core), 0.35 + 0.65 * lane) * (0.8 + 0.4 * w) * glow;
            }
            float dist = length(cameraPosition - vW);
            col = mix(col, fogC, 1.0 - exp(-dist * fogK));
            gl_FragColor = vec4(col, 1.0);
          }` }));
      deck.rotation.x = -Math.PI / 2; deck.position.y = -wd.deckY; near.add(deck); W0.deck = deck;
    }
    W0.G = G;
    // the scale sits on the ground at the origin; his feet stand on its top
    const g0 = G(0, 0); scale.position.set(0, g0 - 0.004, 0); near.add(scale);
    const top = g0 + SCALE.h + 0.004;
    W0.feet = (x, z) => (Math.abs(x) < SCALE.w / 2 - 0.02 && Math.abs(z) < SCALE.d / 2 - 0.02) ? top : G(x, z);
    // he faces the way the world's camera wants (wd.face, as rotation.y); the scale turns with him
    scale.rotation.y = wd.face || 0;
    W0.walker = a.stand({ ground: W0.feet, from: [0, 0], heading: wd.face || 0, glance: false });
    near.add(a.group);

    // light on the figure: the Sun (a shadow map round him), the sky above and the ground below
    const key = new T.DirectionalLight(new T.Color(...wd.keyC), wd.keyK); key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0003; key.shadow.normalBias = 0.012;
    Object.assign(key.shadow.camera, { left: -2.2, right: 2.2, top: 2.2, bottom: -2.2, near: 1, far: 120 });
    key.position.copy(sun).multiplyScalar(40); near.add(key, key.target);
    near.add(new T.HemisphereLight(new T.Color(...wd.hemi[0]), new T.Color(...wd.hemi[1]), wd.hemi[2]));
    if (wd.under) { const u = new T.DirectionalLight(new T.Color(...wd.under[0]), wd.under[1]); u.position.set(0.2, -1, 0.3); near.add(u); }
    near.environment = window.__astronautEnv(T, renderer, { warm: sun, mars: !!wd.marsEnv });
    a.rim.power.value = 4.0; a.rim.color.value.setRGB(...(wd.rim || [0.2, 0.25, 0.35]));

    // the sky
    if (!wd.moon) {
      const dome = new T.Mesh(new T.SphereGeometry(1000, 64, 32), domeMat); dome.renderOrder = -1; sky.add(dome);
      domeMat.uniforms.zen.value.setRGB(...wd.sky[0]); domeMat.uniforms.hor.value.setRGB(...wd.sky[1]);
      domeMat.uniforms.sunD.value.copy(sun); domeMat.uniforms.sunC.value.setRGB(...(wd.sunDisc || [0, 0, 0]));
      domeMat.uniforms.cosR.value = Math.cos((wd.sunDeg || 0.5) / 2 * Math.PI / 180); domeMat.uniforms.glow.value = wd.sunGlow || 0; domeMat.uniforms.haze.value = wd.haze || 0;
      if (wd.stars) sky.add(starsMesh(wd.stars, 7));
      for (const b of wd.bodies || []) sky.add(skyBody(await texLoad('/site/' + b.tex), dirOf(b.az, b.el), b.deg, sun, b));
      if (wd.rings) {             // Saturn's rings from inside its cloud tops: a broad band arching over the sky
        const rt = await texLoad('/site/saturn_ring.png');
        const rg = new T.RingGeometry(1.24, 2.27, 256, 1), P = rg.attributes.position, uv = rg.attributes.uv;
        for (let i = 0; i < P.count; i++) { const r = Math.hypot(P.getX(i), P.getY(i)); uv.setXY(i, (r - 1.24) / (2.27 - 1.24), 0.5); }
        const ring = new T.Mesh(rg, new T.ShaderMaterial({ uniforms: { map: { value: rt } }, side: T.DoubleSide, transparent: true, depthWrite: false,
          vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
          fragmentShader: 'uniform sampler2D map; varying vec2 vUv; void main() { vec4 c = texture2D(map, vUv); gl_FragColor = vec4(c.rgb * 1.1, c.a * 0.95); }' }));
        ring.scale.setScalar(wd.rings.size); ring.position.set(...wd.rings.pos); ring.rotation.set(...wd.rings.rot); sky.add(ring);
      }
    }
    // Titan: wings strapped to his arms (a sheet from the shoulder past the hand, trailing back)
    if (wd.wings) {
      W0.wings = ['L', 'R'].map(sd => {
        const s = sd === 'L' ? -1 : 1, sh = new T.Shape();
        sh.moveTo(0, 0); sh.lineTo(0, -0.95); sh.quadraticCurveTo(0.12, -0.9, 0.3, -0.6); sh.quadraticCurveTo(0.5, -0.25, 0.42, 0.02); sh.lineTo(0, 0);
        // the sheet in the arm's (x, y) plane, on the side that hangs toward his hip once the arm is raised: seen
        // from the front it spreads like a wingsuit
        const g = new T.ShapeGeometry(sh, 16); g.scale(-s, 1, 1);
        const m = new T.Mesh(g, new T.MeshStandardMaterial({ color: 0xf08a24, roughness: 0.6, side: T.DoubleSide, transparent: true, opacity: 0.88 }));
        m.castShadow = true; a.joints['shoulder' + sd].add(m); return m;
      });
    }
    cur = W0; return W0;
  }

  // ---------------- the neutron star (its own small scene) ----------------
  function buildPulsar() {
    const sc = new T.Scene(); sc.add(starsMesh(2500, 11));
    const star = new T.Mesh(new T.SphereGeometry(1, 96, 48), new T.ShaderMaterial({ uniforms: { tt: { value: 0 } },
      vertexShader: 'varying vec3 vN, vW; void main() { vN = normalize(mat3(modelMatrix) * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: `uniform float tt; varying vec3 vN, vW;
        void main() { float mu = max(dot(normalize(vN), normalize(cameraPosition - vW)), 0.0);
          vec3 c = mix(vec3(0.55, 0.7, 1.0), vec3(1.0), pow(mu, 1.5)) * (0.75 + 0.35 * pow(mu, 0.4)); gl_FragColor = vec4(c, 1.0); }` }));
    sc.add(star);
    const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      gr.addColorStop(0, 'rgba(200,225,255,1)'); gr.addColorStop(0.12, 'rgba(160,200,255,0.75)'); gr.addColorStop(0.4, 'rgba(90,140,255,0.18)'); gr.addColorStop(1, 'rgba(60,90,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new T.CanvasTexture(c); })();
    const glow = new T.Sprite(new T.SpriteMaterial({ map: glowTex, blending: T.AdditiveBlending, depthWrite: false, transparent: true })); glow.scale.setScalar(9); sc.add(glow);
    const axis = new T.Group(); axis.rotation.z = 0.45; sc.add(axis);
    const beamMat = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
      vertexShader: 'varying float vY; varying vec2 vUv; void main() { vY = position.y; vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: 'varying float vY; varying vec2 vUv; void main() { float a = (1.0 - smoothstep(0.5, 22.0, abs(vY))) * smoothstep(0.0, 0.5, 0.5 - abs(vUv.x - 0.5)); gl_FragColor = vec4(vec3(0.55, 0.75, 1.0) * a * 0.38, 1.0); }' });
    for (const s of [1, -1]) { const b = new T.Mesh(new T.CylinderGeometry(0.05, 0.75, 22, 48, 1, true), beamMat); b.position.y = s * 11.8; if (s < 0) b.rotation.z = Math.PI; axis.add(b); }
    // the magnetic field: faint loops from pole to pole
    for (let k = 0; k < 10; k++) {
      const pts = []; for (let i = 0; i <= 64; i++) { const th = 0.15 + (Math.PI - 0.3) * i / 64, r = (1.6 + 0.35 * k) * Math.sin(th) ** 2 + 1.0; pts.push(new T.Vector3(r * Math.sin(th), r * Math.cos(th), 0)); }
      const l = new T.Line(new T.BufferGeometry().setFromPoints(pts), new T.LineBasicMaterial({ color: 0x6f9bff, transparent: true, opacity: 0.22, blending: T.AdditiveBlending }));
      l.rotation.y = k * Math.PI / 5; axis.add(l);
    }
    return { sc, axis, star };
  }
  let pulsar = null;

  // ---------------- the camera: keys [t, azimuth° round him (0 = in front), distance, height, fov, look height] ----------------
  function camAt(shot, t) {
    const K = shot.cam; let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++;
    const k0 = K[i], k1 = K[Math.min(i + 1, K.length - 1)];
    let u = k1[0] > k0[0] ? Math.min(1, Math.max(0, (t - k0[0]) / (k1[0] - k0[0]))) : 0; u = u * u * (3 - 2 * u);
    return k0.slice(1).map((v, j) => lerp(v, k1[j + 1], u));
  }

  // ---------------- a frame ----------------
  window.__frame = async (t) => {
    const shot = CFG.shots.find(s => t >= s.t0 && t < s.t1) || CFG.shots[CFG.shots.length - 1], lt = t - shot.t0;
    renderer.setRenderTarget(null); renderer.clear();
    if (shot.world === 'pulsar') {
      pulsar = pulsar || buildPulsar();
      pulsar.axis.rotation.y = lt * 2.2;
      const [az, d, h, fov] = camAt(shot, lt);
      cam.fov = fov; cam.updateProjectionMatrix();
      cam.position.set(Math.sin(az * Math.PI / 180) * d, h, Math.cos(az * Math.PI / 180) * d); cam.lookAt(0, 0, 0);
      renderer.toneMapping = T.NoToneMapping; renderer.render(pulsar.sc, cam); renderer.toneMapping = T.ACESFilmicToneMapping;
      return renderer.domElement.toDataURL('image/jpeg', 0.93);
    }
    const Wd = await build(shot.world), wd = Wd.wd, J = a.joints;
    // the camera round him: azimuth from his front (he faces -z turned by wd.face), at a height over the ground; aimed
    // (below, once the figure is posed) at a height on him, following him up when he leaves the ground
    const [az, d, h, fov, ly] = camAt(shot, lt), ang = (wd.face || 0) + az * Math.PI / 180;
    const cx = -Math.sin(ang) * d, cz = -Math.cos(ang) * d;
    cam.fov = fov; cam.updateProjectionMatrix(); cam.position.set(cx, Wd.G(cx, cz) + h, cz);
    // the figure: standing, plus what this world does to him
    let lift = 0, crouch = 0, lean = 0;
    const act = shot.act || {};
    if (act.jump) {                                   // the Moon: a crouch, a slow high leap (~3 m, ~3.9 s at 1/6 g), a soft landing
      const [t0, T1, hgt] = act.jump, tl = lt - t0, prep = smooth((tl + 0.5) / 0.4) * (1 - smooth(tl / 0.15));
      const air = tl > 0 && tl < T1 ? 4 * hgt * (tl / T1) * (1 - tl / T1) : 0, land = tl > T1 ? smooth((tl - T1) / 0.12) * (1 - smooth((tl - T1 - 0.25) / 0.5)) : 0;
      lift = air; crouch = 0.12 * prep + 0.1 * land;
      Wd.inAir = air > 0.01;
    }
    if (act.heavy) { const k = smooth(lt / act.heavy[0]); crouch = act.heavy[1] * k; lean = -act.heavy[2] * k; }
    Wd.walker.update(lt + shot.t0, { lean, crouch });
    if (act.jump) { const f = Math.min(1, lift / 0.6); for (const sd of ['L', 'R']) { const s = sd === 'L' ? -1 : 1; J['shoulder' + sd].rotation.z += s * 1.0 * f; J['shoulder' + sd].rotation.x -= 0.5 * f; } }
    if (act.heavy) { for (const sd of ['L', 'R']) { J['shoulder' + sd].rotation.z *= 1 - 0.6 * smooth(lt / act.heavy[0]); } J.head.rotation.x -= 0.12 * smooth(lt / act.heavy[0]); }
    if (act.wings) {                                  // Titan: arms out, flapping, lifting off
      const k = smooth(lt / 1.2), fl = Math.sin(lt * 2 * Math.PI * 1.3) * smooth((lt - 0.8) / 0.6);
      for (const sd of ['L', 'R']) { const s = sd === 'L' ? -1 : 1; J['shoulder' + sd].rotation.set(0.05, 0, s * (1.45 * k + 0.35 * fl)); J['elbow' + sd].rotation.set(0.05, 0, 0); }
      lift = 2.6 * smooth((lt - 1.4) / 5.0) + 0.06 * fl;
    }
    if (act.wave) a.gesture('wave', smooth((lt - act.wave) / 0.5), { t: lt, side: 'R' });
    if (act.look) a.lookAt(cam.position, act.look);
    if (act.peek) { const k = smooth((lt - act.peek[0]) / 0.5) * (1 - smooth((lt - act.peek[1]) / 0.6)); if (k > 0) a.lookAt(new T.Vector3(0, Wd.G(0, 0), -0.5).applyAxisAngle(new T.Vector3(0, 1, 0), wd.face || 0), k); }
    a.group.position.y += lift;
    // the scale: what it shows (0 while he is in the air; squashed flat on the Sun)
    scale.scale.y = act.squash ? lerp(1, 0.25, smooth((lt - act.squash) / 0.25)) : 1;
    setLCD(act.squash && lt > act.squash ? '- - -' : (Wd.inAir ? '0.0' : shot.lcd(lt)));
    Wd.inAir = false;
    a.group.updateMatrixWorld(true);
    if (Wd.deck) Wd.deck.material.uniforms.tt.value = t;
    cam.lookAt(0, Wd.G(0, 0) + ly + 0.6 * lift, 0);
    // the sky pass: the far Moon (km) or the dome round the camera
    if (Wd.far) {
      const f = Wd.far, fp = Wd.farAt(cam.position);
      skyCam.fov = fov; skyCam.near = 0.05; skyCam.far = 20000; skyCam.updateProjectionMatrix(); skyCam.position.copy(fp); skyCam.quaternion.copy(cam.quaternion);
      f.stars.position.copy(fp);
      f.earth.position.copy(fp).addScaledVector(f.earthFrame.dir, f.earthFrame.D); f.halo.position.copy(f.earth.position);
      f.earthFrame.U.C.value.copy(f.earth.position); f.earthFrame.U.R.value = f.earthFrame.R;
      renderer.toneMapping = T.NoToneMapping; renderer.render(f.scene, skyCam);
    } else {
      skyCam.fov = fov; skyCam.near = 1; skyCam.far = 5000; skyCam.updateProjectionMatrix(); skyCam.position.set(0, 0, 0); skyCam.quaternion.copy(cam.quaternion);
      renderer.toneMapping = T.NoToneMapping; renderer.render(Wd.sky, skyCam);
    }
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.clearDepth(); renderer.render(Wd.near, cam);
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
  a.ready.then(() => { window.ready = 1; });
})();
