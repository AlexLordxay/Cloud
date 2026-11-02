// «Скільки ти протримаєшся…» v2 — the worlds with ground (the Moon, Mercury, Venus, Mars, Titan), ported from
// scenes/weight/page.js (the same recipes: craters with their exact shadows, dunes, lava plates, far ridges; the real
// LOLA Moon of moon_meet) but drawn in LINEAR light for page.js's HDR chain (bloom, ACES): no gamma at the end of the
// shaders, colours given gamma-encoded in the recipes are decoded here.
//
//   const G = window.__groundWorlds(THREE, renderer, a, CFG);
//   const w = await G.build(name);   // { near, sky, sun, G(x,z), feet(x,z), far?, farAt?, wd, fogU }
//   G.skyPass(w, cam, skyCam)        // renders the sky (dome or the far Moon) into the current target
(() => {
  window.__groundWorlds = (T, renderer, a, CFG) => {
    const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
    const hash2 = (i, j) => { let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
    function vn(x, z) {
      const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j, u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
      const A = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
      return A + (b - A) * u + (c - A) * v + (A - b - c + d) * u * v;
    }
    const fbm = (x, z, n) => { let s = 0, q = 1, f = 1; for (let k = 0; k < n; k++) { s += q * (vn(x * f + 17 * k, z * f - 9 * k) - 0.5); q *= 0.5; f *= 2.03; } return s; };
    const ridged = (x, z, n) => { let s = 0, q = 1, f = 1; for (let k = 0; k < n; k++) { const r = 1 - Math.abs(2 * vn(x * f + 5 * k, z * f + 11 * k) - 1); s += q * r * r; q *= 0.5; f *= 2.1; } return s / 1.75; };
    const dirOf = (az, el) => { const A = az * Math.PI / 180, e = el * Math.PI / 180; return new T.Vector3(Math.sin(A) * Math.cos(e), Math.sin(e), -Math.cos(A) * Math.cos(e)); };
    const V3 = v => new T.Vector3(...v);
    const lin = c => c.map(x => Math.pow(x, 2.2));

    // the regolith's fine texture
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
    function recipe(wd, S, dem) {
      const g = wd.ground, out = [0, 1];
      return (x, z) => {
        out[0] = 0; out[1] = 1;
        const r = Math.hypot(x, z), calm = smooth((r - 0.9) / 2.5), fade = 1 - smooth((r - 900) / 1200);
        for (const [C, r0, r1, p, seed] of g.craters || []) craters(x, z, C, r0, r1, p, seed, (C > 20 ? smooth((r - 8 * C / 20) / 10) : 1) * calm * (g.craterK || 1), out, S);
        out[0] += (g.swell || 0.6) * fbm(x * 0.035 + 5, z * 0.035, 3) * (0.3 + 0.7 * calm) + 0.18 * fbm(x * 0.17, z * 0.17, 3) * calm + 0.03 * fbm(x * 1.1, z * 1.1, 2);
        if (g.dunes) {
          const ph = (x * 0.35 + z * 0.94) / g.dunes[0] + 2.5 * fbm(x * 0.02 + 9, z * 0.02, 2), f = ph - Math.floor(ph);
          out[0] += g.dunes[1] * (f < 0.72 ? smooth(f / 0.72) : smooth((1 - f) / 0.28)) * calm * (0.5 + vn(x * 0.03, z * 0.03));
        }
        if (g.plates) {
          const q = (fbm(x * 0.12, z * 0.12, 3) + 0.5) * 5, fl = Math.floor(q);
          out[0] += g.plates * (fl + smooth((q - fl - 0.85) / 0.15)) * calm;
        }
        if (g.rocks) {             // scattered boulders on the near ground (Mars, Mercury): little domes
          const C = 2.2, ci = Math.floor(x / C), cj = Math.floor(z / C);
          for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
            if (hash2(i + 91, j) > g.rocks) continue;
            const cx = (i + hash2(i, j + 91)) * C, cz = (j + hash2(i - 91, j)) * C, rr = 0.08 + 0.35 * hash2(j, i + 91) ** 3;
            const d = Math.hypot(x - cx, z - cz) / rr; if (d < 1) out[0] += rr * 0.7 * Math.sqrt(1 - d * d) * calm;
          }
        }
        out[0] *= fade; out[1] = 1 - (1 - out[1]) * fade;
        if (g.mountains) {
          const [A, r0, L] = g.mountains;
          out[0] += A * smooth((r - r0) / (r0 * 1.5)) * (0.35 + ridged(x / L + 3, z / L, 4)) * (0.75 + 0.25 * Math.sin(Math.atan2(x, z) * 3 + 1));
        }
        if (dem) out[0] += dem(x, z);
        else out[0] -= r * r / (2 * wd.R);
        return out;
      };
    }
    // the sky dome in linear light: the air from horizon to zenith, the Sun's disc and glow (colours given gamma-encoded)
    const domeMat = new T.ShaderMaterial({ side: T.BackSide, depthWrite: false,
      uniforms: { zen: { value: new T.Color() }, hor: { value: new T.Color() }, sunD: { value: new T.Vector3() }, sunC: { value: new T.Color() },
        cosR: { value: 0.9999 }, glow: { value: 0 }, haze: { value: 0 }, dust: { value: 0 }, tt: { value: 0 } },
      vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform vec3 zen, hor, sunD, sunC; uniform float cosR, glow, haze, dust, tt; varying vec3 vD;
        float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
        float fb(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * n2(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; } return s; }
        void main() {
          vec3 d = normalize(vD); float up = max(d.y, 0.0), m = dot(d, sunD);
          vec3 c = mix(hor, zen, pow(up, 0.55)) * (d.y < 0.0 ? 0.85 : 1.0);
          c = pow(c, vec3(2.2));
          c += sunC * (smoothstep(cosR - (1.0 - cosR) * 0.15, cosR, m) * 6.0);
          c += sunC * glow * (pow(max(m, 0.0), 900.0) * 1.6 + pow(max(m, 0.0), 60.0) * 0.3 + pow(max(m, 0.0), 6.0) * 0.06 * haze);
          if (dust > 0.0) {         // a dust storm on the horizon: a billowing brown wall over a band of azimuths
            float az = atan(d.x, -d.z);
            float dz = abs(mod(az - 2.75 + 3.14159, 6.28318) - 3.14159), band = smoothstep(1.3, 0.35, dz);
            float top = 0.1 + 0.2 * fb(vec2(az * 2.5 + tt * 0.04, 1.0)) * band + 0.06 * fb(vec2(az * 8.0 - tt * 0.08, 3.0));
            float wall = (1.0 - smoothstep(top - 0.05, top + 0.01, d.y)) * band * dust;
            float bill = fb(vec2(az * 10.0 + tt * 0.06, d.y * 14.0 - tt * 0.04)), lit = smoothstep(top - 0.12, top, d.y);
            vec3 dc = mix(vec3(0.36, 0.2, 0.11), vec3(0.78, 0.55, 0.36), 0.35 * bill + 0.65 * lit * bill);
            c = mix(c, pow(dc, vec3(2.2)), wall * 0.95);
          }
          gl_FragColor = vec4(c, 1.0);
        }` });
    function starsMesh(n, seed) {
      const g = new T.BufferGeometry(), p = [], c = []; let s = seed; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
      for (let i = 0; i < n; i++) { const u = rnd() * 2 - 1, an = rnd() * 6.283, r = Math.sqrt(1 - u * u), b = 0.05 + 0.5 * Math.pow(rnd(), 3);
        p.push(r * Math.cos(an) * 900, u * 900, r * Math.sin(an) * 900); c.push(b, b, b * 1.05); }
      g.setAttribute('position', new T.Float32BufferAttribute(p, 3)); g.setAttribute('color', new T.Float32BufferAttribute(c, 3));
      return new T.Points(g, new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
    }
    function groundMaterial(U) {
      return new T.ShaderMaterial({ uniforms: U,
        vertexShader: `attribute float lit; varying float vLit; varying vec3 vW, vN;
          void main() { vLit = lit; vN = normal; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
        fragmentShader: `uniform sampler2D col, shd, rg, rb; uniform vec3 sun, sunC, amb, alb, fogC, glowC; uniform float fogK, grain, dxN, mapK, glowK; uniform vec2 off;
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
            o += glowC * glowK * gr * (0.6 + 0.4 * sin(vW.x * 0.7) * sin(vW.z * 0.9));   // hot ground (Venus) glowing faintly
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
    function skyBody(tex, dir, deg, sun, extra) {
      const D = 800, m = new T.Mesh(new T.SphereGeometry(D * Math.tan(deg / 2 * Math.PI / 180), 96, 48), new T.ShaderMaterial({
        uniforms: { map: { value: tex }, sun: { value: sun }, k: { value: (extra && extra.k) || 1.6 }, fade: { value: (extra && extra.fade) || 0 }, fadeC: { value: new T.Color(...lin((extra && extra.fadeC) || [0, 0, 0])) } },
        vertexShader: 'varying vec2 vUv; varying vec3 vN; void main() { vUv = uv; vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
        fragmentShader: `uniform sampler2D map; uniform vec3 sun, fadeC; uniform float k, fade; varying vec2 vUv; varying vec3 vN;
          void main() { vec3 c = pow(texture2D(map, vUv).rgb, vec3(2.2)) * max(dot(normalize(vN), sun), 0.0) * k; gl_FragColor = vec4(mix(c, fadeC, fade), 1.0); }` }));
      m.position.copy(dir).multiplyScalar(D); m.rotation.set(0.3, 2.0, 0.2); return m;
    }

    const cache = {};
    async function build(name) {
      if (cache[name]) return cache[name];
      const wd = CFG.worlds[name], W0 = { name, wd };
      const sun = dirOf(...(wd.sun || [0, 10])), sunH = Math.hypot(sun.x, sun.z) || 1;
      const S = { tanE: sun.y / sunH, sx: sun.x / sunH, sz: sun.z / sunH, hard: wd.shadowHard == null ? 1 : wd.shadowHard };
      const near = new T.Scene(), sky = new T.Scene();
      W0.near = near; W0.sky = sky; W0.sun = sun;
      let dem = null, U;
      if (wd.moon) {
        const far = window.__moon || (window.__moon = await buildMoon());
        far.og.value = 1;                                       // linear out, for the HDR chain
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
        fogC: { value: new T.Color(...lin(wd.fog ? wd.fog[0] : [0, 0, 0])) }, fogK: { value: wd.fog ? wd.fog[1] : 0 }, grain: { value: wd.grain == null ? 0.75 : wd.grain },
        rg: { value: GRIT }, rb: { value: BUMP }, glowC: { value: new T.Color(...(wd.glowC || [0, 0, 0])) }, glowK: { value: 0 } });
      W0.U = U;
      const Gr = recipe(wd, S, dem);
      const G = (x, z) => Gr(x, z)[0];
      const pg = polarGeometry(Gr, wd.Rmax || 3000, 640);
      const ground = new T.Mesh(pg.geo, groundMaterial(U)); ground.frustumCulled = false; near.add(ground);
      W0.G = G; W0.feet = G;
      // light on the figure: the Sun, the sky above, the ground below (no shadow maps here: the figure stands in the open)
      const key = new T.DirectionalLight(new T.Color(...wd.keyC), wd.keyK); key.position.copy(sun).multiplyScalar(40); near.add(key, key.target); W0.key = key;
      W0.hemi = new T.HemisphereLight(new T.Color(...wd.hemi[0]), new T.Color(...wd.hemi[1]), wd.hemi[2]); near.add(W0.hemi);
      near.environment = window.__astronautEnv(T, renderer, { warm: sun, mars: !!wd.marsEnv });
      // the figure's shadow: a soft dark blob on the ground under him (stretched away from the Sun)
      const blobT = (() => { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
        gr.addColorStop(0, 'rgba(0,0,0,0.75)'); gr.addColorStop(0.5, 'rgba(0,0,0,0.4)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new T.CanvasTexture(c); })();
      const blob = new T.Mesh(new T.PlaneGeometry(1, 1), new T.MeshBasicMaterial({ map: blobT, transparent: true, depthWrite: false, opacity: wd.blob == null ? 0.8 : wd.blob }));
      blob.rotation.x = -Math.PI / 2; blob.renderOrder = 1; near.add(blob); W0.blob = blob;
      // the sky
      if (!wd.moon) {
        const dome = new T.Mesh(new T.SphereGeometry(1000, 64, 32), domeMat); dome.renderOrder = -1; sky.add(dome);
        W0.dome = { zen: wd.sky[0], hor: wd.sky[1], sunD: sun, sunC: wd.sunDisc || [0, 0, 0], cosR: Math.cos((wd.sunDeg || 0.5) / 2 * Math.PI / 180), glow: wd.sunGlow || 0, haze: wd.haze || 0, dust: wd.dust || 0 };
        if (wd.stars) sky.add(starsMesh(wd.stars, 7));
        for (const b of wd.bodies || []) sky.add(skyBody(await texLoad('/site/' + b.tex), dirOf(b.az, b.el), b.deg, sun, b));
      }
      cache[name] = W0; return W0;
    }
    // where he stands and how the blob sits under him
    function place(W0, x, z, k = 1) {
      const y = W0.G(x, z);
      W0.blob.position.set(x + W0.sun.x * -0.25, W0.G(x + W0.sun.x * -0.25, z + W0.sun.z * -0.25) + 0.01, z + W0.sun.z * -0.25);
      W0.blob.scale.set(1.1 * k, 1.1 * k, 1); W0.blob.material.opacity = (W0.wd.blob == null ? 0.8 : W0.wd.blob) * k;
      return y;
    }
    function skyPass(W0, cam, skyCam, t) {
      if (W0.far) {
        const f = W0.far, fp = W0.farAt(cam.position);
        skyCam.fov = cam.fov; skyCam.aspect = cam.aspect; skyCam.near = 0.05; skyCam.far = 20000; skyCam.updateProjectionMatrix(); skyCam.position.copy(fp); skyCam.quaternion.copy(cam.quaternion);
        f.stars.position.copy(fp);
        f.earth.position.copy(fp).addScaledVector(f.earthFrame.dir, f.earthFrame.D); f.halo.position.copy(f.earth.position);
        f.earthFrame.U.C.value.copy(f.earth.position); f.earthFrame.U.R.value = f.earthFrame.R;
        renderer.render(f.scene, skyCam);
      } else {
        const d = W0.dome, u = domeMat.uniforms;
        u.zen.value.setRGB(...d.zen); u.hor.value.setRGB(...d.hor); u.sunD.value.copy(d.sunD); u.sunC.value.setRGB(...d.sunC);
        u.cosR.value = d.cosR; u.glow.value = d.glow; u.haze.value = d.haze; u.dust.value = d.dust; u.tt.value = t || 0;
        skyCam.fov = cam.fov; skyCam.aspect = cam.aspect; skyCam.near = 1; skyCam.far = 5000; skyCam.updateProjectionMatrix(); skyCam.position.set(0, 0, 0); skyCam.quaternion.copy(cam.quaternion);
        renderer.render(W0.sky, skyCam);
      }
    }
    return { build, place, skyPass, dirOf };
  };
})();
