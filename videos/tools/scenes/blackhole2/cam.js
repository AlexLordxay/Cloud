// «Що буде, якщо впасти в чорну діру?» v2 (85 s, the author's voice): Sagittarius A* and the Nebozvid astronaut.
// One world in units of the Schwarzschild radius (r_s = 1, the hole at the origin, its disc in the y = 0 plane), drawn
// by a full-screen shader that bends every ray (Schwarzschild); the astronaut, the flashes of light and the horizon grid
// are drawn over it with the same camera. For the pull-out to the whole Milky Way the galaxy scene of `scale` / v1
// (light years) takes over; the sky round the hole is that galaxy seen from its centre (a cube map, made once).
// Shots by voice line (times in seconds of the video) — see script.md:
//   0–6.2 hook: the visor close up, pull back, the astronaut turns to the hole · 6.2–16.4 out to the galaxy and back in,
//   Mercury's orbit for scale · 16.4–20.9 from above (the 2022 photo) · 20.9–41.8 the event horizon: flashes from the
//   helmet lamp, the light that gets away shrinks to nothing · 42–50.6 a friend far away: slower, redder, frozen ·
//   50.6–59.3 the fall goes on; light round the photon sphere, his own back ahead · 59.3–62.6 a small hole stretches him ·
//   62.6–67.3 Sgr A*: thumbs up · 67.3–79 through his eyes: the sky behind shrinks to a bright circle, then a dot ·
//   79–86.5 the hole again under the question and the end card.
(() => {
  const smooth = window.__smooth, lerp = window.__lerp, D = Math.PI / 180;
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const lerpLog = (a, b, k) => Math.exp(lerp(Math.log(a), Math.log(b), k));
  const sm = (a, b, t) => smooth((t - a) / (b - a));                 // 0 before a, 1 after b, smooth between
  const ease = x => { x = clamp(x, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const RS_LY = 1.34e-6;                 // Schwarzschild radius of Sgr A* (4.3 million Suns, 12.7 million km) in light years
  const SUN_R = 26000;                   // the Sun's distance from the centre, ly
  let ready = false, G = null;

  /* ---------- Galaxy model (shared by the shader and the star sampler) ---------- */
  const THETA_SUN = Math.PI / 2;                       // the Sun at (x 0, z 26 000)
  const THETA_BAR = THETA_SUN + Math.PI - 27 * D;      // near end of the bar, 27° off the Sun–centre line
  const PITCH_B = 1 / Math.tan(12 * D), R0 = 11000;
  const ARMS = [[THETA_BAR, 1.0], [THETA_BAR + Math.PI, 1.0], [THETA_BAR + Math.PI / 2, 0.7], [THETA_BAR + 1.5 * Math.PI, 0.7]];
  // the Orion spur: a short arm piece through the Sun
  const SPUR_PHI = THETA_SUN - PITCH_B * Math.log(SUN_R / R0);
  const GLSL_MODEL = `
    const float PI = 3.14159265;
    float wrapA(float a) { return mod(a + PI, 2.0 * PI) - PI; }
    float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float vnoise(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
    float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 6; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; } return s; }
    // distance across an arm, in ly (negative on its inner side)
    float armOff(float r, float th, float phi) {
      float d = wrapA(th - (phi + ${PITCH_B.toFixed(5)} * log(max(r, 1.0) / ${R0.toFixed(1)})));
      return d * r * ${Math.sin(12 * D).toFixed(5)};
    }
  `;
  const ARMS_GLSL = ARMS.map(([p, w]) => `vec2(${p.toFixed(5)}, ${w.toFixed(2)})`).join(', ');

  // JS twin of the density for sampling stars: returns [arms, disc, bulge, bar, dust]
  function wrapA(a) { return ((a + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI; }
  function armOff(r, th, phi) { return wrapA(th - (phi + PITCH_B * Math.log(Math.max(r, 1) / R0))) * r * Math.sin(12 * D); }
  function model(x, z) {
    const r = Math.hypot(x, z), th = Math.atan2(z, x);
    let arms = 0, dust = 0;
    const w = 1300 + 0.045 * r;
    if (r > 9000) for (const [phi, wt] of ARMS) {
      const o = armOff(r, th, phi), wind = PITCH_B * Math.log(Math.max(r, 1) / R0), big = wt > 0.8;
      const fadeIn = smooth((r - 9000) / 5000) * (1 - smooth((wind - (big ? 4.2 : 3.0)) / 1.3));
      arms += wt * fadeIn * Math.exp(-(o * o) / (2 * w * w));
      const od = o + 0.55 * w;
      dust += wt * fadeIn * Math.exp(-(od * od) / (2 * (0.28 * w) ** 2));
    }
    if (r > 20000 && r < 33000) {
      const o = armOff(r, th, SPUR_PHI), k = Math.exp(-(((r - SUN_R) / 4500) ** 2));
      arms += 0.45 * k * Math.exp(-(o * o) / (2 * (0.7 * w) ** 2));
    }
    const disc = Math.exp(-r / 11000) * (1 - smooth((r - 50000) / 15000));
    const bulge = Math.exp(-r / 2200);
    const ca = Math.cos(THETA_BAR), sa = Math.sin(THETA_BAR), u = x * ca + z * sa, v = -x * sa + z * ca;
    const bar = Math.exp(-((u / 11000) ** 2) - ((v / 3600) ** 2));
    return [arms, disc, bulge, bar, dust];
  }

  function buildGalaxy(r, img) {
    const THREE = r.THREE, V = THREE.Vector3;
    const scene = new THREE.Scene();
    const gal = new THREE.Group(), local = new THREE.Group(), core = new THREE.Group();
    scene.add(gal, local, core);
    const rnd = Math.random, gauss = () => { let u = 0; for (let i = 0; i < 4; i++) u += rnd(); return (u - 2) * 0.866; };

    // Soft star sprites: size in px at 1 ly (attenuated), clamped; alpha fades for sub-pixel sizes.
    const pointMat = (opts = {}) => new THREE.ShaderMaterial({
      uniforms: { scale: { value: 1 }, gain: { value: 1 }, pmin: { value: opts.pmin || 0.7 }, pmax: { value: opts.pmax || 6 } },
      vertexShader: `attribute vec3 color; attribute float size; uniform float scale; uniform float pmin; uniform float pmax;
        varying vec3 vC; varying float vA;
        void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); float s = size * scale / max(-mv.z, 1e-9);
          vA = clamp(s / pmin, 0.0, 1.0); vA *= vA; gl_PointSize = clamp(s, pmin, pmax); vC = color; gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform float gain; varying vec3 vC; varying float vA;
        void main() { vec2 c = gl_PointCoord - 0.5; float d = dot(c, c) * 4.0; if (d > 1.0) discard;
          float f = exp(-d * 3.5); gl_FragColor = vec4(vC * f * vA * gain, 1.0); }`,
      transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
    });
    const pointsOf = (pos, col, size, mat) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      g.setAttribute('size', new THREE.Float32BufferAttribute(size, 1));
      const p = new THREE.Points(g, mat); p.frustumCulled = false; return p;
    };

    // 1. The galaxy's face: the NASA/JPL-Caltech/R. Hurt (SSC/Caltech) reconstruction of the Milky Way, laid on the disc
    //    (2576 px across ≈ 124 000 ly; the Sun 26 000 ly "below" the centre in the picture, which is +z here).
    const S = 124000;
    const tex = new THREE.Texture(img); tex.needsUpdate = true; tex.anisotropy = r.renderer.capabilities.getMaxAnisotropy();
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(S, S, 1, 1), new THREE.ShaderMaterial({
      uniforms: { map: { value: tex }, gain: { value: 0 } },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `uniform sampler2D map; uniform float gain; varying vec2 vUv;
        void main() {
          vec3 c = texture2D(map, vUv).rgb;
          c = max(c - vec3(0.02, 0.025, 0.05), 0.0);                       // the picture's dark-blue sky becomes black
          float edge = 1.0 - smoothstep(0.42, 0.5, length(vUv - 0.5));     // no square edge
          gl_FragColor = vec4(c * edge * gain, 1.0);
        }`,
      transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    }));
    plane.rotation.x = -Math.PI / 2;
    gal.add(plane);

    // 2. Stars scattered over the same picture, with its colours, and given thickness (a thin disc, a fat bulge), so the
    //    arms have depth when the camera flies over them.
    {
      const R = 1288, cv = document.createElement('canvas'); cv.width = cv.height = R;
      const g = cv.getContext('2d'); g.drawImage(img, 0, 0, R, R);
      const px = g.getImageData(0, 0, R, R).data;
      const n = 360000, pos = [], col = [], size = [];
      let made = 0, tries = 0;
      while (made < n && tries < n * 60) {
        tries++;
        const ix = Math.floor(rnd() * R), iy = Math.floor(rnd() * R), k = (iy * R + ix) * 4;
        const cr = px[k] / 255, cg = px[k + 1] / 255, cb = px[k + 2] / 255, lum = (cr + cg + cb) / 3;
        if (rnd() > Math.pow(Math.max(0, lum - 0.05), 2.2) * 1.6) continue;
        const x = ((ix + rnd()) / R - 0.5) * S, z = ((iy + rnd()) / R - 0.5) * S, rr = Math.hypot(x, z);
        pos.push(x, gauss() * (220 + 2600 * Math.exp(-rr / 2800)), z);
        const b = (0.55 + rnd() ** 3 * 1.6) / Math.max(0.35, lum);
        col.push(cr * b, cg * b, cb * b);
        size.push(rnd() < 0.015 ? 9000 : 3500);
        made++;
      }
      const pts = pointsOf(pos, col, size, pointMat({ pmin: 0.9, pmax: 2.2 }));
      gal.add(pts);
      scene.userData.galStars = pts;
    }
    // 4. The bulge: a warm glow sprite.
    const glowTex = (() => {
      const cv = document.createElement('canvas'); cv.width = cv.height = 256;
      const g = cv.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      gr.addColorStop(0, 'rgba(255,240,215,1)'); gr.addColorStop(0.15, 'rgba(255,214,160,0.6)'); gr.addColorStop(0.45, 'rgba(255,190,130,0.15)'); gr.addColorStop(1, 'rgba(255,180,120,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(cv);
    })();
    const bulgeGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0 }));
    bulgeGlow.scale.set(26000, 26000, 1); gal.add(bulgeGlow);
    // 5. Faint far galaxies behind it all.
    {
      const pos = [], col = [], size = [];
      for (let k = 0; k < 3000; k++) {
        const u = rnd() * 2 - 1, t = rnd() * 2 * Math.PI, s = Math.sqrt(1 - u * u), R = 3e6;
        pos.push(s * Math.cos(t) * R, u * R, s * Math.sin(t) * R); const b = 0.2 + rnd() * 0.5; col.push(b, b * 0.95, b * 0.9); size.push(2e6);
      }
      scene.add(pointsOf(pos, col, size, pointMat({ pmin: 0.8, pmax: 2.2 })));
    }

    // Local neighbourhood around the Sun (own coordinates: the Sun at 0, so it stays sharp up close).
    {
      // a few real neighbours (ly, rough direction) with their colours, then a random field out to 3000 ly
      const near = [[4.24, [1, 0.6, 0.45], 0.5], [4.37, [1, 0.95, 0.85], 1.6], [5.96, [1, 0.6, 0.45], 0.4], [8.6, [0.8, 0.88, 1], 3.0], [11.4, [1, 0.85, 0.7], 1.2], [16.7, [0.85, 0.9, 1], 2.2], [25, [0.8, 0.88, 1], 2.6]];
      const pos = [], col = [], size = [];
      near.forEach(([d, c, b], i) => { const a = i * 2.4 + 0.6, e = (i % 3 - 1) * 0.35; pos.push(Math.cos(a) * Math.cos(e) * d, Math.sin(e) * d, Math.sin(a) * Math.cos(e) * d); col.push(c[0] * b, c[1] * b, c[2] * b); size.push(60); });
      for (let k = 0; k < 400; k++) {
        const d = 6 + 80 * Math.cbrt(rnd()), u = rnd() * 2 - 1, t = rnd() * 2 * Math.PI, s = Math.sqrt(1 - u * u), b = 0.8 + rnd() ** 2 * 2.5, warm = rnd() < 0.6;
        pos.push(s * Math.cos(t) * d, u * d * 0.6, s * Math.sin(t) * d); col.push(b * (warm ? 1 : 0.78), b * 0.88, b * (warm ? 0.72 : 1)); size.push(40);
      }
      for (let k = 0; k < 40000; k++) {
        const d = 3000 * Math.cbrt(rnd()) + 3, u = rnd() * 2 - 1, t = rnd() * 2 * Math.PI, s = Math.sqrt(1 - u * u);
        pos.push(s * Math.cos(t) * d, u * d * 0.35, s * Math.sin(t) * d);
        const warm = rnd() < 0.7, b = 0.3 + rnd() ** 4 * 2.2;
        col.push(b * (warm ? 1 : 0.75), b * (warm ? 0.85 : 0.85), b * (warm ? 0.7 : 1)); size.push(25 + rnd() * 40);
      }
      const p = pointsOf(pos, col, size, pointMat({ pmin: 0.9, pmax: 5 })); local.add(p); scene.userData.localStars = p;
      // the Sun itself and a "you are here" ring
      const sun = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, color: 0xffe9c0, sizeAttenuation: false }));
      sun.scale.set(0.05, 0.05, 1); local.add(sun); scene.userData.sun = sun;
      const cv = document.createElement('canvas'); cv.width = cv.height = 256;
      cv.width = 512; cv.height = 512;
      const g = cv.getContext('2d'); g.strokeStyle = 'rgba(243,185,100,0.95)'; g.lineWidth = 6; g.beginPath(); g.arc(256, 200, 90, 0, 2 * Math.PI); g.stroke();
      g.fillStyle = 'rgba(255,205,130,1)'; g.shadowColor = 'rgba(0,0,0,0.9)'; g.shadowBlur = 12; g.font = '700 70px sans-serif'; g.textAlign = 'center'; g.fillText('ти тут', 256, 370);
      const ring = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthTest: false, depthWrite: false, sizeAttenuation: false, opacity: 0 }));
      ring.scale.set(0.2, 0.2, 1); ring.center.set(0.5, 0.61); local.add(ring); scene.userData.ring = ring;
    }
    // Around the centre (own coordinates): the nuclear star cluster and the S-stars close to the black hole.
    {
      const pos = [], col = [], size = [];
      for (let k = 0; k < 60000; k++) {
        const d = 40 * Math.pow(rnd(), 2.2) + 0.05, u = rnd() * 2 - 1, t = rnd() * 2 * Math.PI, s = Math.sqrt(1 - u * u);
        pos.push(s * Math.cos(t) * d, u * d * 0.7, s * Math.sin(t) * d); const b = 0.3 + rnd() ** 3 * 1.5; col.push(b, b * 0.82, b * 0.62); size.push(0.6 + rnd());
      }
      for (let k = 0; k < 40; k++) {
        const d = 0.003 + 0.03 * rnd(), u = rnd() * 2 - 1, t = rnd() * 2 * Math.PI, s = Math.sqrt(1 - u * u);
        pos.push(s * Math.cos(t) * d, u * d, s * Math.sin(t) * d); col.push(0.75, 0.85, 1.2); size.push(0.004);
      }
      const p = pointsOf(pos, col, size, pointMat({ pmin: 0.9, pmax: 5 })); core.add(p); scene.userData.coreStars = p;
    }

    const cam = new THREE.PerspectiveCamera(r.camera.fov, r.camera.aspect, 1, 1e7);
    return { scene, gal, local, core, cam, plane, bulgeGlow };
  }

  /* ---------- The black hole: every pixel's ray bent in the Schwarzschild metric (r_s = 1) ---------- */
  // Sky: a cube map (the galaxy from its centre, turned by skyRot). Disc: thin, hot near the innermost stable orbit
  // (3 r_s), turning faster inside, the side coming at us brighter and bluer (Doppler), redder deep in the well;
  // streaks along the orbits wound into a loose spiral. merc: Mercury's orbit (58 million km = 4.55 r_s) dashed on the
  // disc plane, so it is lensed like the disc. blue: the observer hovers just above the horizon — the sky ahead is
  // squeezed, brighter and bluer. A camera inside the 60 r_s sphere starts its rays as a static observer would see them.
  function buildHole(r) {
    const THREE = r.THREE;
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        sky: { value: null }, skyRot: { value: new THREE.Matrix3() }, skyGain: { value: 1 },
        camPos: { value: new THREE.Vector3() }, camRot: { value: new THREE.Matrix3() }, tanHalf: { value: 0.4 }, aspect: { value: 0.5625 },
        time: { value: 0 }, discK: { value: 1 }, discTint: { value: new THREE.Vector3(1, 1, 1) }, discHot: { value: 1 }, merc: { value: 0 }, blue: { value: 0 },
      },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
      fragmentShader: `
        uniform samplerCube sky; uniform mat3 skyRot; uniform float skyGain;
        uniform vec3 camPos; uniform mat3 camRot; uniform float tanHalf; uniform float aspect;
        uniform float time; uniform float discK; uniform vec3 discTint; uniform float discHot; uniform float merc; uniform float blue;
        varying vec2 vUv;
        float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        // value noise, periodic (P cells) in y: y runs round the disc
        float vnp(vec2 p, float P) {
          vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          float y0 = mod(i.y, P), y1 = mod(i.y + 1.0, P);
          return mix(mix(h21(vec2(i.x, y0)), h21(vec2(i.x + 1.0, y0)), f.x), mix(h21(vec2(i.x, y1)), h21(vec2(i.x + 1.0, y1)), f.x), f.y);
        }
        vec3 skyCol(vec3 d) {
          vec3 c = textureCube(sky, skyRot * d).rgb * skyGain;
          if (blue > 0.0) c = mix(c, vec3(dot(c, vec3(0.3, 0.5, 0.2))) * vec3(0.72, 0.88, 1.3), 0.6 * blue) * (1.0 + 2.5 * blue);
          return c;
        }
        vec3 bbody(float x) {            // deep orange .. yellow .. white .. blue-white
          vec3 a = vec3(1.0, 0.30, 0.05), b = vec3(1.0, 0.62, 0.26), c = vec3(1.0, 0.92, 0.78), d = vec3(0.80, 0.88, 1.0);
          return x < 0.5 ? mix(a, b, x / 0.5) : x < 1.0 ? mix(b, c, x / 0.5 - 1.0) : mix(c, d, clamp(x - 1.0, 0.0, 1.0));
        }
        void main() {
          vec2 sc = (vUv * 2.0 - 1.0) * vec2(tanHalf * aspect, tanHalf);
          vec3 dir = normalize(camRot * vec3(sc, -1.0));
          vec3 p = camPos;
          float b = dot(p, dir), c = dot(p, p) - 3600.0, disc = b * b - c;
          if (c > 0.0 && (disc < 0.0 || b > 0.0)) { gl_FragColor = vec4(skyCol(dir), 1.0); return; }
          vec3 v = dir;
          if (c > 0.0) p += dir * (-b - sqrt(disc));
          else {
            // a static observer: local angle psi to the radial direction -> coordinate velocity (vr, vt)
            float rr = length(p); vec3 n = p / rr; float cp = dot(dir, n);
            vec3 tg = dir - n * cp; float tl = length(tg);
            v = n * cp + (tl > 1e-6 ? tg / tl : vec3(0.0)) * tl / sqrt(max(1.0 - 1.0 / rr, 1e-6));
          }
          vec3 col = vec3(0.0); float alpha = 0.0;
          vec3 hc = cross(p, v); float h2 = dot(hc, hc);
          bool captured = false;
          for (int i = 0; i < 320; i++) {
            float rr = length(p);
            if (rr < 1.0) { captured = true; break; }
            if (rr > 61.0 && dot(p, v) > 0.0) break;
            float dt = clamp(0.07 * rr * min(1.0, (rr - 1.0) * 4.0 + 0.02), 0.0015, 2.0);
            vec3 pPrev = p;
            v += -1.5 * h2 * p / pow(rr, 5.0) * dt; p += v * dt;
            if (pPrev.y * p.y < 0.0) {
              vec3 q = mix(pPrev, p, pPrev.y / (pPrev.y - p.y));
              float qr = length(q.xz);
              if (merc > 0.0) {
                float mr = qr - 4.55, ang = atan(q.z, q.x);
                float dash = step(0.42, fract(ang / 6.2832 * 48.0));
                col += vec3(0.45, 0.82, 1.0) * exp(-mr * mr / 0.0018) * dash * merc * 1.6 * (1.0 - 0.6 * alpha);
              }
              if (discK > 0.0 && qr > 2.2 && qr < 18.0) {
                float ang = atan(q.z, q.x), lr = log(qr);
                float sw = ang + time * 0.9 / pow(qr, 1.5) + lr * 1.4;     // turning (faster inside), wound into a spiral
                float u = sw / 6.2832;
                float st = 0.55 * vnp(vec2(lr * 14.0, u * 14.0), 14.0) + 0.3 * vnp(vec2(lr * 42.0 + 5.0, u * 40.0), 40.0) + 0.15 * vnp(vec2(lr * 110.0, u * 90.0), 90.0);
                float nt = pow(3.0 / qr, 0.75) * pow(max(1.0 - sqrt(3.0 / qr), 0.0), 0.25) / 0.49;   // thin-disc temperature, peak ~1 near 4 r_s
                float temp = max(nt, 0.35 * smoothstep(2.2, 3.0, qr) * (1.0 - smoothstep(3.0, 3.6, qr))) * (1.0 - smoothstep(11.0, 17.5, qr));
                // Doppler: the disc turns anticlockwise seen from +y; gas coming at us is bluer and much brighter
                float beta = sqrt(0.5 / max(qr - 1.0, 0.5));
                vec3 vel = normalize(vec3(-q.z, 0.0, q.x)) * beta;
                float g = sqrt(max(1.0 - 1.0 / qr, 0.05)) * sqrt(1.0 - beta * beta) / (1.0 - dot(vel, -normalize(v)));
                float I = temp * (0.35 + 1.3 * st) * pow(g, 3.0);
                vec3 e = bbody(temp * g * 1.05 * discHot) * I * 1.7 * discTint;
                float a = clamp(temp * (0.6 + 0.8 * st), 0.0, 0.94) * discK * (1.0 - alpha);
                col += e * a; alpha += a;
                if (alpha > 0.97) break;
              }
            }
          }
          vec3 back = captured ? vec3(0.0) : skyCol(normalize(v));
          gl_FragColor = vec4(col + back * (1.0 - alpha), 1.0);
        }`,
      depthTest: false, depthWrite: false,
    });
    const scene = new THREE.Scene(); scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    return { scene, mat, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }

  // Final picture: the hole's frame and the galaxy's frame crossfaded, a soft filmic shoulder, a vignette, a white
  // flash (the horizon), and the 2022 photo laid over the hole when there is one (scenes/blackhole2/eht.jpg).
  function buildComposite(r) {
    const THREE = r.THREE;
    const mat = new THREE.ShaderMaterial({
      uniforms: { hole: { value: null }, gal: { value: null }, k: { value: 1 }, exposure: { value: 1 }, flash: { value: 0 }, aspect: { value: 0.5625 },
        eht: { value: null }, ehtK: { value: 0 }, ehtC: { value: new THREE.Vector2(0.5, 0.5) }, ehtS: { value: 0.3 } },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
      fragmentShader: `uniform sampler2D hole; uniform sampler2D gal; uniform float k; uniform float exposure; uniform float flash; uniform float aspect;
        uniform sampler2D eht; uniform float ehtK; uniform vec2 ehtC; uniform float ehtS; varying vec2 vUv;
        void main() {
          vec3 c = mix(texture2D(gal, vUv).rgb, texture2D(hole, vUv).rgb, k) * exposure;
          c = 1.0 - exp(-c);
          if (ehtK > 0.0) {
            vec2 u = (vUv - ehtC) * vec2(aspect, 1.0) / ehtS + 0.5;
            float m = smoothstep(0.5, 0.4, length(u - 0.5));
            c = mix(c, texture2D(eht, clamp(u, 0.0, 1.0)).rgb, ehtK * m);
          }
          vec2 q = (vUv - 0.5) * vec2(aspect, 1.0);
          c *= 1.0 - 0.38 * smoothstep(0.32, 0.75, length(q) * 1.15);
          gl_FragColor = vec4(c + flash, 1.0);
        }`,
      depthTest: false, depthWrite: false,
    });
    const scene = new THREE.Scene(); scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    return { scene, mat, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }

  /* ---------- Over the hole, with the same camera: the astronaut, light, the horizon ---------- */
  const glowTex2 = THREE => {
    const cv = document.createElement('canvas'); cv.width = cv.height = 128;
    const g = cv.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.2, 'rgba(255,240,210,0.55)'); gr.addColorStop(0.55, 'rgba(255,220,170,0.12)'); gr.addColorStop(1, 'rgba(255,200,150,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(cv);
  };
  const dotsMat = THREE => new THREE.ShaderMaterial({
    uniforms: { gain: { value: 1 } },
    vertexShader: `attribute vec3 color; attribute float size; varying vec3 vC;
      void main() { vC = color; gl_PointSize = size; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform float gain; varying vec3 vC;
      void main() { vec2 c = gl_PointCoord - 0.5; float d = dot(c, c) * 4.0; if (d > 1.0) discard; gl_FragColor = vec4(vC * gain * exp(-d * 2.6), 1.0); }`,
    transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
  });
  function dynDots(THREE, n) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('size', new THREE.Float32BufferAttribute(new Float32Array(n), 1));
    g.setDrawRange(0, 0);
    const p = new THREE.Points(g, dotsMat(THREE)); p.frustumCulled = false;
    let k = 0;
    p.userData = {
      reset() { k = 0; },
      add(x, y, z, r, gg, b, s) { if (k >= n) return; const P = g.attributes.position.array, C = g.attributes.color.array; P[3 * k] = x; P[3 * k + 1] = y; P[3 * k + 2] = z; C[3 * k] = r; C[3 * k + 1] = gg; C[3 * k + 2] = b; g.attributes.size.array[k] = s; k++; },
      done() { g.setDrawRange(0, k); g.attributes.position.needsUpdate = g.attributes.color.needsUpdate = g.attributes.size.needsUpdate = true; },
    };
    return p;
  }

  function buildOverlay(r) {
    const THREE = r.THREE, a = window.__makeAstronaut(THREE), scene = new THREE.Scene();
    scene.add(a.group);
    const key = a.light(0xffd0a0, 1.8, new THREE.Vector3(0, 0.3, -1));
    const fill = new THREE.DirectionalLight(0x9fb4e0, 0.5), amb = new THREE.HemisphereLight(0x6a78a8, 0x2a1a10, 0.12);
    scene.add(key, key.target, fill, fill.target, amb);
    const cam = new THREE.PerspectiveCamera(45, 0.5625, 0.002, 5000);
    const dots = dynDots(THREE, 9000); scene.add(dots);
    // the horizon (r = 1) as a glowing grid of dots: 12 meridians, 7 parallels
    const gp = [], gc = [], gs = [];
    for (let m = 0; m < 12; m++) for (let i = 0; i <= 90; i++) { const th = i / 90 * Math.PI, ph = m / 12 * 2 * Math.PI; gp.push(Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)); gc.push(0.35, 0.62, 1.0); gs.push(2.6); }
    for (let l = 1; l < 8; l++) for (let i = 0; i < 160; i++) { const th = l / 8 * Math.PI, ph = i / 160 * 2 * Math.PI; gp.push(Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)); gc.push(0.35, 0.62, 1.0); gs.push(2.6); }
    const gg = new THREE.BufferGeometry();
    gg.setAttribute('position', new THREE.Float32BufferAttribute(gp, 3)); gg.setAttribute('color', new THREE.Float32BufferAttribute(gc, 3)); gg.setAttribute('size', new THREE.Float32BufferAttribute(gs, 1));
    const grid = new THREE.Points(gg, dotsMat(THREE)); grid.frustumCulled = false; scene.add(grid);
    const flare = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex2(THREE), transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: false }));
    scene.add(flare);
    const envs = new Map();
    const env = (name, warm) => { if (!envs.has(name)) envs.set(name, window.__astronautEnv(THREE, r.renderer, { warm })); return envs.get(name); };
    return { a, scene, cam, key, fill, amb, dots, grid, flare, env };
  }

  /* ---------- Light from the helmet lamp (the event-horizon explanation) ---------- */
  // A photon from an emitter hovering at distance r, sent at local angle psi to the outward radial: h = r sin(psi) /
  // sqrt(1 - 1/r), coordinate velocity (cos psi, sin psi / sqrt(1 - 1/r)); then the same law as in the shader
  // (a = -3/2 h^2 p / r^5). Stored by path length s, so on screen every photon flies at the same speed.
  function photonPath(ex, ey, psi) {
    const r0 = Math.hypot(ex, ey), nx = ex / r0, ny = ey / r0, tx = -ny, ty = nx;
    const vr = Math.cos(psi), vt = Math.sin(psi) / Math.sqrt(1 - 1 / r0);
    let x = ex, y = ey, vx = nx * vr + tx * vt, vy = ny * vr + ty * vt, s = 0, fate = 'out';
    const h = x * vy - y * vx, h2 = h * h, pts = [[0, x, y]];
    for (let i = 0; i < 40000; i++) {
      const rr = Math.hypot(x, y);
      if (rr < 1.0005) { fate = 'in'; break; }
      if (rr > 48 && x * vx + y * vy > 0) break;
      const dt = Math.min(0.04, 0.01 * rr * Math.min(1, (rr - 1) * 4 + 0.03)), f = -1.5 * h2 / Math.pow(rr, 5);
      vx += f * x * dt; vy += f * y * dt;
      const sp = Math.hypot(vx, vy);
      x += vx * dt; y += vy * dt; s += sp * dt;
      if (s - pts[pts.length - 1][0] > 0.03) pts.push([s, x, y]);
    }
    pts.push([s, x, y]);
    return { pts, fate, len: s };
  }
  function along(P, s) {             // position at path length s (binary search)
    const p = P.pts; let lo = 0, hi = p.length - 1;
    if (s <= 0) return [p[0][1], p[0][2]];
    if (s >= p[hi][0]) return [p[hi][1], p[hi][2]];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (p[m][0] < s) lo = m; else hi = m; }
    const k = (s - p[lo][0]) / (p[hi][0] - p[lo][0]);
    return [lerp(p[lo][1], p[hi][1], k), lerp(p[lo][2], p[hi][2], k)];
  }

  /* ---------- Shots (shots.js) ---------- */
  let SH = null, V, plane4, lamp4, r4, th4, BURSTS, Qh, shotAt;
  function loadShots() {
    SH = window.__bhShots({ smooth, lerp, D, clamp, lerpLog, sm, ease, RS_LY });
    ({ V, plane4, lamp4, r4, th4, BURSTS, Qh, shotAt } = SH);
    if (G) G.bursts = BURSTS.map(t0 => {
      const r = r4(t0), th = th4(t0), ex = r * Math.cos(th), ey = r * Math.sin(th);
      return { t0, paths: Array.from({ length: 36 }, (_, j) => photonPath(ex, ey, (j + 0.37) / 36 * 2 * Math.PI)) };
    });
  }
  window.__bhReload = loadShots;            // a dev harness re-reads shots.js and calls this

  /* ---------- Setup ---------- */
  window.__sceneSetup = async (r) => {
    const THREE = r.THREE, s = r.state, ren = r.renderer;
    s.rate = 0; loadShots();
    const W = ren.domElement.width, H = ren.domElement.height, rtOpts = { type: THREE.HalfFloatType, depthBuffer: true };
    G = {
      ...buildGalaxy(r, await new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = '/scene/milkyway.jpg'; })),
      hole: buildHole(r), comp: buildComposite(r), O: buildOverlay(r), Q: Qh(),
      rtHole: new THREE.WebGLRenderTarget(W, H, rtOpts), rtGal: new THREE.WebGLRenderTarget(W, H, rtOpts),
    };
    await G.O.a.ready;
    { const a = G.O.a; a.pose(0); a.group.updateMatrixWorld(true); const h = a.joints.head.getWorldPosition(new THREE.Vector3()), l = a.joints.head.localToWorld(new THREE.Vector3(-0.226, 0.2, -0.115)); console.log('[scene] head', h.toArray().map(x => x.toFixed(3)).join(' '), 'lamp', l.toArray().map(x => x.toFixed(3)).join(' ')); }
    // the 2022 photo, if it is there
    G.eht = await new Promise(ok => { const im = new Image(); im.onload = () => { const tx = new THREE.Texture(im); tx.needsUpdate = true; ok(tx); }; im.onerror = () => ok(null); im.src = '/scene/eht.jpg'; });
    // The sky round the hole: the galaxy seen from its centre, once, into a cube map (2048 per face, mip-mapped).
    const cube = new THREE.WebGLCubeRenderTarget(2048, { generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
    const cc = new THREE.CubeCamera(1e-6, 1e7, cube);
    G.gal.position.set(0, 0, 0); G.local.position.set(0, 0, SUN_R); G.core.position.set(0, 0, 0);
    G.scene.children.forEach(o => { if (o.isPoints) o.material.uniforms.scale.value = 1024; });
    for (const p of [G.scene.userData.galStars, G.scene.userData.localStars, G.scene.userData.coreStars]) p.material.uniforms.scale.value = 1024;
    G.plane.material.uniforms.gain.value = 0; G.bulgeGlow.material.opacity = 0;
    G.scene.userData.galStars.material.uniforms.gain.value = 0.9; G.scene.userData.localStars.material.uniforms.gain.value = 0;
    G.scene.userData.coreStars.material.uniforms.gain.value = 1; G.scene.userData.coreStars.material.uniforms.pmax.value = 3;
    G.scene.userData.sun.material.opacity = 0; G.scene.userData.ring.material.opacity = 0;
    ren.setClearColor(0x000000, 1);
    cc.update(ren, G.scene);
    G.scene.userData.coreStars.material.uniforms.pmax.value = 5;
    G.sky = cube.texture;
    loadShots();                            // again, now with G: the flashes of the lamp, every photon's path once
    console.log('[scene] bursts', G.bursts.map(b => b.paths.filter(p => p.fate === 'out').length).join(' '));
    ready = true;
  };

  /* ---------- Each frame ---------- */
  window.__recCam = () => { if (ready) G.t = window.__vt() - (window.__t0 || 0); };

  function orient(obj, fwd, up) {
    const THREE = window.__rec.THREE, z = fwd.clone().negate().normalize(), x = new THREE.Vector3().crossVectors(up, z).normalize(), y = new THREE.Vector3().crossVectors(z, x);
    obj.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  }
  function shake(cam, amp, t) {
    if (!amp) return;
    cam.rotateX(amp * (Math.sin(t * 37.1) * 0.6 + Math.sin(t * 23.3 + 1.3) * 0.4));
    cam.rotateY(amp * (Math.sin(t * 29.7 + 0.4) * 0.6 + Math.sin(t * 17.9 + 2.1) * 0.4));
    cam.rotateZ(amp * 0.5 * Math.sin(t * 19.3 + 0.7));
  }

  // the astronaut for this frame (pose, place, light), or hidden
  function placeAstro(S, t, cam) {
    const THREE = window.__rec.THREE, O = G.O, a = O.a, g = a.group, A = S.astro;
    if (!A || (A.op != null && A.op <= 0.001)) { g.visible = false; return null; }
    g.visible = true;
    a.pose(A.poseT != null ? A.poseT : t);
    if (A.thumbs) a.gestureAt(t, 'thumbsUp', { start: A.thumbs[0], end: A.thumbs[1], side: 'R' });
    orient(g, A.fwd, A.up);
    if (A.tumble != null) { const k = A.tumble; g.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(0.3, 0.25 - 0.2 * k, -0.15 + 0.8 * k, 'YXZ'))); }
    const k = A.stretch || 1; g.scale.set(A.s / Math.sqrt(k), A.s * k, A.s / Math.sqrt(k));
    g.position.copy(A.pos || V(0, 0, 0));
    g.updateMatrixWorld(true);
    if (A.lookCam) a.lookAt(cam.position, A.lookCam);
    if (A.lamp) { g.updateMatrixWorld(true); const lw = a.joints.head.localToWorld(V(-0.226, 0.2, -0.115)); g.position.add(A.lamp.clone().sub(lw)); g.updateMatrixWorld(true); }
    const tn = A.tint || [1, 1, 1]; a.setTint(tn[0], tn[1], tn[2]); a.setOpacity(A.op != null ? A.op : 1);
    const c = g.getWorldPosition(new THREE.Vector3()), toHole = c.clone().negate().normalize();
    O.key.userData.dir.copy(toHole).addScaledVector(V(0, 1, 0), 0.25).normalize();
    O.fill.position.copy(c).add(cam.position.clone().sub(c).normalize()); O.fill.target.position.copy(c); O.fill.target.updateMatrixWorld();
    a.rim.color.value.setRGB(0.95 * tn[0], 0.62 * tn[1], 0.32 * tn[2]);
    O.scene.environment = O.env(A.env, A.warm);
    a.aim();
    return A;
  }

  // the dots: lamp flashes (S4), light round the photon sphere (S6), the horizon grid
  function drawDots(S, t) {
    const O = G.O, d = O.dots.userData; d.reset();
    O.flare.visible = false;
    if (S.bursts) {
      const { e1, e2 } = plane4(), TRAIL = 2.6, K = 22, SPEED = 8;
      for (const b of G.bursts) {
        const age = t - b.t0; if (age < 0 || age > 9) continue;
        const head = SPEED * age;
        for (const P of b.paths) {
          if (head - TRAIL > P.len) continue;
          for (let i = 0; i <= K; i++) {
            const s = head - TRAIL * i / K; if (s < 0 || s > P.len) continue;
            const [x, y] = along(P, s), rr = Math.hypot(x, y), gz = Math.sqrt(Math.max(0, 1 - 1 / rr));
            const w = Math.pow(1 - i / K, 1.6) * (P.fate === 'in' ? Math.min(1, (P.len - s) * 3 + 0.2) : 1);
            const q = e1.clone().multiplyScalar(x).addScaledVector(e2, y);
            d.add(q.x, q.y, q.z, 1.0 * w * (0.4 + 0.6 * gz), 0.9 * w * gz, 0.7 * w * gz * gz, i === 0 ? 6 : 4.2 - 2.4 * i / K);
          }
        }
      }
      // the lamp: always a small glow, a burst of light at each flash
      const L = lamp4(t); let fl = 0.035;
      for (const b of G.bursts) { const age = t - b.t0; if (age > -0.05 && age < 0.6) fl += 0.16 * Math.exp(-Math.max(0, age) / 0.15); }
      O.flare.visible = true; O.flare.position.copy(L); O.flare.scale.set(fl, fl, 1); O.flare.material.opacity = S.astro && S.astro.op != null ? S.astro.op : 1;
    }
    if (S.orbit > 0) {
      const { A, B } = S.orb;
      for (let j = 0; j < 7; j++) for (let i = 0; i < 40; i++) {
        const al = 2.6 * t + j / 7 * 2 * Math.PI - i * 0.025, w = Math.pow(1 - i / 40, 1.5) * S.orbit;
        const q = A.clone().multiplyScalar(1.5 * Math.cos(al)).addScaledVector(B, 1.5 * Math.sin(al));
        d.add(q.x, q.y, q.z, 1.0 * w, 0.88 * w, 0.66 * w, i === 0 ? 7 : 4.5 - 3 * i / 40);
      }
    }
    d.done();
    O.grid.visible = S.grid > 0.002; O.grid.material.uniforms.gain.value = S.grid; O.grid.rotation.y = t * 0.15;
  }

  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer, THREE = r.THREE;
    if (!ready) { ren.render(r.scene, r.camera); return; }
    const t = G.t || 0, S = shotAt(t), O = G.O, cam = O.cam;
    const W = ren.domElement.width, H = ren.domElement.height;
    cam.position.copy(S.cam.pos); cam.up.copy(S.cam.up); cam.lookAt(S.cam.look); shake(cam, S.shake, t);
    cam.fov = S.cam.fov; cam.aspect = W / H;
    const dist = cam.position.length();
    cam.near = Math.min(0.002, Math.max(1e-5, (dist - 1) * 0.05)); cam.far = 5000; cam.updateProjectionMatrix(); cam.updateMatrixWorld();
    // the galaxy takes over far out
    const L = Math.log10(dist), kHole = 1 - smooth((L - Math.log10(600)) / (Math.log10(8000) - Math.log10(600)));
    if (kHole > 0) {
      const u = G.hole.mat.uniforms;
      u.sky.value = G.sky; u.skyRot.value.setFromMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(G.Q));
      u.camPos.value.copy(cam.position); u.camRot.value.setFromMatrix4(cam.matrixWorld);
      u.tanHalf.value = Math.tan(cam.fov * D / 2); u.aspect.value = cam.aspect; u.time.value = t * 6;
      u.discK.value = S.discK; u.discTint.value.set(...S.discTint); u.discHot.value = S.discHot; u.merc.value = S.merc; u.blue.value = S.blue;
      ren.setRenderTarget(G.rtHole); ren.render(G.hole.scene, G.hole.cam);
    }
    if (kHole < 1) {
      const gc = G.cam, q = G.Q;
      gc.position.copy(cam.position).applyQuaternion(q).multiplyScalar(RS_LY);
      gc.up.copy(S.cam.up).applyQuaternion(q);
      gc.lookAt(S.cam.look.clone().applyQuaternion(q).multiplyScalar(RS_LY));
      const dl = gc.position.length();
      gc.fov = cam.fov; gc.aspect = cam.aspect; gc.near = Math.max(dl * 1e-4, 1e-9); gc.far = 1e7; gc.updateProjectionMatrix();
      G.gal.position.set(0, 0, 0); G.local.position.set(0, 0, SUN_R); G.core.position.set(0, 0, 0);
      const scale = H / (2 * Math.tan(gc.fov * D / 2));
      G.scene.children.forEach(o => { if (o.isPoints) o.material.uniforms.scale.value = scale; });
      for (const p of [G.scene.userData.galStars, G.scene.userData.localStars, G.scene.userData.coreStars]) p.material.uniforms.scale.value = scale;
      const Ll = Math.log10(dl);
      G.plane.material.uniforms.gain.value = 1.15 * smooth((Ll - 3.75) / 0.8);
      G.scene.userData.galStars.material.uniforms.gain.value = 0.16 + 0.6 * smooth((4.6 - Ll) / 1.2);
      G.scene.userData.localStars.material.uniforms.gain.value = 1.7 * (1 - smooth((Ll - 3.2) / 0.8));
      G.bulgeGlow.material.opacity = 0.12 * smooth((Ll - 4.3) / 0.7);
      G.scene.userData.coreStars.material.uniforms.gain.value = 1;
      G.scene.userData.sun.material.opacity = S.you;
      G.scene.userData.ring.material.opacity = S.you;
      ren.setRenderTarget(G.rtGal); ren.setClearColor(0x000000, 1); ren.clear(); ren.render(G.scene, gc);
    }
    const cu = G.comp.mat.uniforms;
    cu.hole.value = G.rtHole.texture; cu.gal.value = G.rtGal.texture; cu.k.value = kHole; cu.exposure.value = S.exposure; cu.flash.value = S.flash; cu.aspect.value = cam.aspect;
    cu.ehtK.value = G.eht ? S.eht : 0;
    if (G.eht && S.eht > 0) {                  // the photo over the hole, its ring on the shadow's edge
      const p = new THREE.Vector3(0, 0, 0).project(cam); cu.eht.value = G.eht; cu.ehtC.value.set(p.x * 0.5 + 0.5, p.y * 0.5 + 0.5);
      cu.ehtS.value = 2.9 * 2.6 / (dist * Math.tan(cam.fov * D / 2)) * 0.5;
    }
    ren.setRenderTarget(null); ren.clear(); ren.render(G.comp.scene, G.comp.cam);
    // over it: the astronaut (filmic, soft shadows), his ghost, the dots
    const A = placeAstro(S, t, cam);
    drawDots(S, t);
    const ac = ren.autoClear, tm = ren.toneMapping, te = ren.toneMappingExposure, smE = ren.shadowMap.enabled, st = ren.shadowMap.type;
    ren.autoClear = false; ren.toneMapping = THREE.ACESFilmicToneMapping; ren.toneMappingExposure = 1.15;
    ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
    ren.clearDepth(); ren.render(O.scene, cam);
    if (A && A.ghost && A.ghost.k > 0.002) {
      const g = O.a.group, keep = { p: g.position.clone(), q: g.quaternion.clone() };
      O.dots.visible = O.grid.visible = O.flare.visible = false;
      O.a.pose(t + 3.1); orient(g, A.ghost.fwd, A.ghost.up); g.position.copy(A.ghost.pos); g.updateMatrixWorld(true);
      O.a.setTint(0.55, 0.75, 1.25); O.a.setOpacity(0.42 * A.ghost.k); O.a.aim();
      ren.clearDepth(); ren.render(O.scene, cam);
      g.position.copy(keep.p); g.quaternion.copy(keep.q); O.dots.visible = true;
    }
    ren.autoClear = ac; ren.toneMapping = tm; ren.toneMappingExposure = te; ren.shadowMap.enabled = smE; ren.shadowMap.type = st;
  };
})();
