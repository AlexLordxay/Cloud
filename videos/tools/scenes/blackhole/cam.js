// "Where are you in the Universe": one unbroken pull-back from the Earth over Ukraine to the whole Solar System (the site's
// own scene), on into the stars around the Sun and out to the whole Milky Way, then a dive into its centre, to the black
// hole Sagittarius A*. The galaxy and the black hole exist only here, for this video: a second scene in light years
// drawn after the site's, crossfaded where the Solar System shrinks to a point.
//
// Galaxy: a barred spiral after current maps of the Milky Way — a bar ~27° from the Sun–centre line, two major arms
// (Scutum–Centaurus, Perseus) from its ends, two minor ones (Norma, Sagittarius), ~12° pitch, the Sun 26 000 ly out on the
// small Orion spur. Smooth light of the disc and bulge comes from a shader; on top of it ~700 000 star sprites, pink
// star-forming regions and dark dust lanes on the inner edges of the arms. Seen from outside it is an artist's view.
// Black hole: a full-screen shader that bends each ray in the Schwarzschild metric (r_s = 1), so the hot disc shows above
// and below the shadow, the side coming towards us is brighter (Doppler beaming), and the background is lensed.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const lerpLog = (a, b, k) => Math.exp(lerp(Math.log(a), Math.log(b), k));

  // Timeline (s). The flight never stops; each stretch hands over to the next at speed.
  const T = { moon: 6, sun: 13, system: 21, fade0: -3, fade1: -2, stars: -20, arm: -20, wide: -20, dive: -20, hole: -20, end: 34 };   // black-hole-only cut: the galaxy scene from frame 0
  // Part A (0 - A_END s): a friend far away watches the astronaut fall in. Part B: the fall through his own eyes.
  // The camera follows the old timeline in "story time" TT: part A stretches its first 5 s, part B runs a bit faster.
  const A_END = 14, FALL = 1.15;
  const TT = t => t < A_END ? t * 5 / A_END : 5 + (t - A_END) * FALL;
  const RS_LY = 1.27e-6;                 // Schwarzschild radius of Sgr A* (4.1 million Suns) in light years
  const SUN_R = 26000;                   // the Sun's distance from the centre, ly

  let ready = false, dir0 = null, G = null;
  const N = () => new window.__rec.THREE.Vector3(0, 1, 0);

  function geoOf(r, lat, lon, h) {
    const E = r.byId.earth, q = E.mesh.getWorldQuaternion(new r.THREE.Quaternion());
    const l = new r.THREE.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
    return l.applyQuaternion(q).multiplyScalar(E.radius * h).add(E.world);
  }

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

  /* ---------- Black hole: ray-traced in the Schwarzschild metric ---------- */
  function buildHole(r) {
    const THREE = r.THREE;
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        bg: { value: null }, camPos: { value: new THREE.Vector3() }, camRot: { value: new THREE.Matrix3() },
        tanHalf: { value: 0.4 }, aspect: { value: 0.56 }, time: { value: 0 }, mixIn: { value: 0 },
        viewProj: { value: new THREE.Matrix4() },
      },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
      fragmentShader: `
        uniform sampler2D bg; uniform vec3 camPos; uniform mat3 camRot; uniform float tanHalf; uniform float aspect;
        uniform float time; uniform float mixIn; uniform mat4 viewProj; varying vec2 vUv;
        float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
        vec3 bgDir(vec3 d) {                  // the galaxy behind, sampled where the bent ray points on screen
          vec4 c = viewProj * vec4(camPos + d * 1e4, 1.0);
          if (c.w <= 0.0) return vec3(0.0);
          vec2 uv = c.xy / c.w * 0.5 + 0.5;
          float edge = smoothstep(0.0, 0.04, min(min(uv.x, uv.y), min(1.0 - uv.x, 1.0 - uv.y)));
          return texture2D(bg, clamp(uv, 0.001, 0.999)).rgb * edge;
        }
        vec3 bb(float t) {                    // warm blackbody-ish ramp, t in 0..~2
          return clamp(vec3(1.0, 0.45 + 0.4 * t, 0.12 + 0.5 * t * t) * t, 0.0, 6.0);
        }
        void main() {
          vec2 sc = (vUv * 2.0 - 1.0) * vec2(tanHalf * aspect, tanHalf);
          vec3 dir = normalize(camRot * vec3(sc, -1.0));
          vec3 base = texture2D(bg, vUv).rgb;
          vec3 p = camPos;
          // only rays that pass near the hole need bending; start them on a sphere of 60 r_s
          float b = dot(p, dir), c = dot(p, p) - 3600.0, disc = b * b - c;
          if (disc < 0.0 || -b + sqrt(max(disc, 0.0)) < 0.0) { gl_FragColor = vec4(base, 1.0); return; }
          if (c > 0.0) p += dir * (-b - sqrt(disc));
          vec3 v = dir, col = vec3(0.0); float alpha = 0.0;
          vec3 hcross = cross(p, v); float h2 = dot(hcross, hcross);
          bool captured = false;
          for (int i = 0; i < 300; i++) {
            float rr = length(p);
            if (rr < 1.0) { captured = true; break; }
            if (rr > 62.0 && dot(p, v) > 0.0) break;
            float dt = clamp(0.06 * rr, 0.02, 1.5);
            vec3 pPrev = p;
            vec3 acc = -1.5 * h2 * p / pow(rr, 5.0);
            v += acc * dt; p += v * dt;
            // crossing the disc plane (y = 0) between 3 and 16 r_s
            if (pPrev.y * p.y < 0.0) {
              vec3 q = mix(pPrev, p, pPrev.y / (pPrev.y - p.y));
              float qr = length(q.xz);
              if (qr > 2.6 && qr < 16.0) {
                float ang = atan(q.z, q.x);
                float omega = 0.9 / pow(qr, 1.5);
                float sw = ang + time * omega;
                float rings = 0.6 + 0.4 * (0.6 * vn(vec2(qr * 1.6, sw * 3.0)) + 0.4 * vn(vec2(qr * 4.0 + 2.0, sw * 7.0)));
                float temp = pow(3.0 / qr, 1.1) * smoothstep(2.6, 3.3, qr) * (1.0 - smoothstep(9.0, 15.0, qr));
                // Doppler: the disc turns anticlockwise seen from +y; gas coming at us is bluer and much brighter
                vec3 vel = normalize(vec3(-q.z, 0.0, q.x)) * sqrt(0.5 / max(qr - 1.0, 0.5));
                float g = 1.0 / (1.0 - dot(vel, -normalize(v)) * 0.95);
                float I = temp * rings * pow(g, 3.0);
                vec3 e = bb(I * 1.6) * 1.4;
                float a = clamp(temp * 1.2, 0.0, 0.92) * (1.0 - alpha);
                col += e * a; alpha += a;
                if (alpha > 0.97) break;
              }
            }
          }
          vec3 back = captured ? vec3(0.0) : bgDir(normalize(v));
          vec3 hole = col + back * (1.0 - alpha);
          gl_FragColor = vec4(mix(base, hole, mixIn), 1.0);
        }`,
      depthTest: false, depthWrite: false,
    });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
    const scene = new THREE.Scene(); scene.add(quad);
    return { scene, mat, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }

  // Final composite: the site's frame (linear) and the galaxy's frame, crossfaded, with a soft filmic curve.
  function buildComposite(r) {
    const THREE = r.THREE;
    const mat = new THREE.ShaderMaterial({
      uniforms: { site: { value: null }, gal: { value: null }, k: { value: 0 }, exposure: { value: 1 } },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
      fragmentShader: `uniform sampler2D site; uniform sampler2D gal; uniform float k; uniform float exposure; varying vec2 vUv;
        void main() {
          vec3 a = pow(max(texture2D(site, vUv).rgb, 0.0), vec3(1.0 / 2.2));
          vec3 g = texture2D(gal, vUv).rgb * exposure;
          g = 1.0 - exp(-g);                                  // filmic shoulder: bright cores glow instead of clipping
          gl_FragColor = vec4(mix(a, g, k), 1.0);
        }`,
      depthTest: false, depthWrite: false,
    });
    const scene = new THREE.Scene(); scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    return { scene, mat, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  }

  // The astronaut (a cut-out picture, AI-generated) drawn over the finished frame: it falls towards the hole, shrinks,
  // slows down, reddens and dims, and freezes just outside the shadow -- what a far-away observer would see.
  function buildAstro(r, img) {
    const THREE = r.THREE, tex = new THREE.Texture(img); tex.needsUpdate = true;
    const mat = new THREE.ShaderMaterial({
      uniforms: { map: { value: tex }, tint: { value: new THREE.Vector3(1, 1, 1) }, op: { value: 1 } },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `uniform sampler2D map; uniform vec3 tint; uniform float op; varying vec2 vUv;
        void main() { vec4 c = texture2D(map, vUv); gl_FragColor = vec4(c.rgb * tint, c.a * op); }`,
      transparent: true, depthTest: false, depthWrite: false,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(img.width / img.height, 1), mat);
    const scene = new THREE.Scene(); scene.add(mesh);
    return { scene, mesh, mat, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1) };
  }
  function drawAstro(ren, t) {
    if (t > A_END) return;
    const A = G.astro, k = 1 - Math.exp(-t / 5.5);              // goes away, slower and slower: it freezes
    const aspect = ren.domElement.width / ren.domElement.height;
    const size = lerpLog(1.3, 0.03, Math.pow(k, 1.6));          // height in screen halves
    A.mesh.position.set(lerp(0.3, 0.17, k), lerp(-0.62, 0.17, k), 0);   // ends at the upper right edge of the shadow
    A.mesh.scale.set(size / aspect, size, 1);
    A.mesh.rotation.z = 0.35 + 1.1 * k;                          // its tumble slows down with it
    const red = k * k;
    A.mat.uniforms.tint.value.set(1, 1 - 0.7 * red, 1 - 0.92 * red);
    A.mat.uniforms.op.value = 1 - smooth((t - 10.5) / 3.2);       // dimmer and dimmer, then gone
    const ac = ren.autoClear; ren.autoClear = false; ren.render(A.scene, A.cam); ren.autoClear = ac;
  }

  window.__sceneSetup = async (r) => {
    const THREE = r.THREE, s = r.state;
    s.index = r.BODIES.indexOf(r.byId.earth); s.mode = 'focus'; s.flight = null; s.rate = 0;
    window.__step(1 / 30);
    const E = r.byId.earth;
    dir0 = geoOf(r, 49.0, 31.5, 1).sub(E.world).normalize();
    for (const m of E.tiltGroup.children) if (m.geometry && m.geometry.parameters && Math.abs(m.geometry.parameters.radius - E.radius * 1.025) < 1e-6) m.visible = false;
    const W = r.renderer.domElement.width, H = r.renderer.domElement.height;
    const rtOpts = { type: THREE.HalfFloatType, depthBuffer: true };
    G = {
      ...buildGalaxy(r, await new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = '/scene/milkyway.jpg'; })), hole: buildHole(r), comp: buildComposite(r),
      rtSite: new THREE.WebGLRenderTarget(W, H, rtOpts), rtGal: new THREE.WebGLRenderTarget(W, H, rtOpts), rtHole: new THREE.WebGLRenderTarget(W, H, rtOpts),
      starfield: r.scene.children.find(o => o.isPoints && o.geometry.attributes.position.count === 7000),
    };
    G.astro = buildAstro(r, await new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = '/scene/astronaut.png'; }));
    console.log('[scene] galaxy stars', G.scene.userData.galStars.geometry.attributes.position.count);
    ready = true;
  };

  /* ---------- Camera ---------- */
  // Galaxy-scene camera: target, distance (ly), elevation and azimuth over the disc, by time.
  function galCam(t) {
    // The fall: from ~58 r_s (the whole hole and its disc) down through the photon sphere to the horizon and in.
    const V = window.__rec.THREE.Vector3;
    let rs;
    if (t < 5) rs = lerp(58, 50, t / 5);                                   // hanging there: the hook
    else if (t < 18) rs = lerpLog(50, 10, smooth((t - 5) / 13));          // falling
    else if (t < 25) rs = lerpLog(10, 4.5, smooth((t - 18) / 7));         // close: the shadow grows
    else rs = lerpLog(4.5, 2.6, smooth((t - 25) / 4));                     // the last stretch; the fade to black is the horizon
    const el = lerp(9, 14, smooth((t - 5) / 20)), az = lerp(0, 60, smooth(t / 30));
    // close in, the view tilts up off the centre so the shadow sinks low and the disc and bent sky stay in the frame
    const off = 48 * D * smooth((t - 17) / 10);
    const dir = new V(Math.cos(el * D) * Math.cos(az * D), Math.sin(el * D), Math.cos(el * D) * Math.sin(az * D));
    return { target: new V(), dist: rs * RS_LY, dir, off };
  }

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, THREE = r.THREE, V = THREE.Vector3, t = window.__vt() - (window.__t0 || 0);
    const E = r.byId.earth, C = E.world.clone(), R = E.radius, n = N();
    // Site part: from 4.6 R over Ukraine back past the Moon's orbit, the Earth and the Sun, to the whole system.
    const vel = new V().crossVectors(n, C).normalize();
    const back = vel.clone().negate().multiplyScalar(0.6).addScaledVector(C.clone().normalize(), 0.35).addScaledVector(n, 0.7).normalize();
    const top = back.clone().setY(0).normalize().multiplyScalar(0.6).addScaledVector(n, 0.8).normalize();
    let dir = dir0.clone().lerp(back, smooth((t - 2) / 6)).normalize();
    dir = dir.lerp(top, smooth((t - T.sun) / 10)).normalize();
    const d = t < T.sun ? lerpLog(R * 4.6, 60, ease(t / T.sun) * 0.6 + (t / T.sun) * 0.4)
                        : lerpLog(60, 2600, clamp((t - T.sun) / (T.fade1 - T.sun), 0, 1) ** 1.3);
    const centre = C.clone().lerp(new V(), smooth((t - 8) / 9));
    const cam = r.camera;
    cam.position.copy(centre).addScaledVector(dir, d);
    cam.up.copy(geoOf(r, 90, 0, 1).sub(C).normalize().lerp(n, smooth((t - 1) / 6)).normalize());
    cam.lookAt(centre); r.controls.target.copy(centre);
    const near = Math.max(0.002, Math.min(0.5, (cam.position.distanceTo(C) - R * 1.05) * 0.3));
    cam.far = 20000;
    if (Math.abs(cam.near - near) > near * 0.02 || cam.far !== 20000) { cam.near = near; cam.updateProjectionMatrix(); }
    const oAll = smooth((t - T.system + 3) / 3);
    for (const x of r.BODIES) if (x.orbitLine) { const o = x.parent ? (x.id === 'moon' ? 0.5 * smooth((t - 3) / 2) * (1 - smooth((t - 12) / 3)) : 0) : x.baseOpacity * 1.8 * oAll; x.orbitLine.visible = o > 0.003; x.orbitLine.material.opacity = o; }
    if (r.asteroidBelt) r.asteroidBelt.visible = r.kuiperBelt.visible = t > T.system - 3;
    G.t = TT(t); G.real = t;
  };

  // Rendering (replaces the site's renderer.render through a patch in scene.json).
  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer, THREE = r.THREE, V = THREE.Vector3;
    if (!ready) { ren.render(r.scene, r.camera); return; }
    const t = G.t || 0, k = smooth((t - T.fade0) / (T.fade1 - T.fade0));
    const needSite = k < 1, needGal = k > 0;
    if (!needGal) { ren.setRenderTarget(null); ren.render(r.scene, r.camera); return; }
    if (needSite) { ren.setRenderTarget(G.rtSite); ren.clear(); ren.render(r.scene, r.camera); }
    if (needGal) {
      const { target, dist, dir, off } = galCam(t), cam = G.cam;
      // Keep coordinates small where the camera is: each group is placed relative to the point looked at.
      const sunPos = new V(0, 0, SUN_R);
      cam.position.copy(dir).multiplyScalar(dist); cam.up.set(0, 1, 0); cam.lookAt(0, 0, 0); if (off) cam.rotateX(off); cam.updateMatrixWorld();
      G.gal.position.copy(target).negate();
      G.local.position.copy(sunPos).sub(target);
      G.core.position.copy(target).negate();
      cam.near = Math.max(dist * 1e-4, 1e-9); cam.far = 1e7; cam.aspect = r.camera.aspect; cam.updateProjectionMatrix();
      const scale = ren.domElement.height / (2 * Math.tan(cam.fov * D / 2));
      for (const p of [G.scene.userData.galStars, G.scene.userData.localStars, G.scene.userData.coreStars]) p.material.uniforms.scale.value = scale;
      G.scene.children.forEach(o => { if (o.isPoints) o.material.uniforms.scale.value = scale; });
      // what shows at which scale
      const L = Math.log10(dist);
      G.plane.material.uniforms.gain.value = 1.15 * smooth((L - 3.75) / 0.8);
      G.scene.userData.galStars.material.uniforms.gain.value = 0.16 + 0.6 * smooth((4.6 - L) / 1.2);
      G.scene.userData.localStars.material.uniforms.gain.value = 1.7 * (1 - smooth((L - 3.2) / 0.8));
      G.bulgeGlow.material.opacity = 0.12 * smooth((L - 4.3) / 0.7);
      G.scene.userData.coreStars.material.uniforms.gain.value = t > T.dive ? 1 : 0;
      const sun = G.scene.userData.sun, ring = G.scene.userData.ring;
      sun.material.opacity = t < T.wide + 1 ? 1 : 0;
      ring.material.opacity = smooth((t - T.stars - 4) / 1.5) * (1 - smooth((t - T.dive - 0.3) / 0.8));
      const toHole = t > T.dive + 6;
      ren.setRenderTarget(toHole ? G.rtHole : G.rtGal); ren.setClearColor(0x000000, 1); ren.clear();
      ren.render(G.scene, cam);
      if (toHole) {
        const u = G.hole.mat.uniforms;
        u.bg.value = G.rtHole.texture;
        u.camPos.value.copy(cam.position).divideScalar(RS_LY);
        u.camRot.value.setFromMatrix4(cam.matrixWorld);
        u.tanHalf.value = Math.tan(cam.fov * D / 2); u.aspect.value = cam.aspect; u.time.value = (G.real || 0) * 6;
        u.mixIn.value = smooth((Math.log10(dist / RS_LY) - 4.5) / -1.2);
        const vc = cam.clone(); vc.position.copy(cam.position).divideScalar(RS_LY); vc.near = 0.1; vc.far = 1e6; vc.updateMatrixWorld(); vc.updateProjectionMatrix();
        u.viewProj.value.multiplyMatrices(vc.projectionMatrix, vc.matrixWorldInverse);
        ren.setRenderTarget(G.rtGal); ren.clear(); ren.render(G.hole.scene, G.hole.cam);
      }
    }
    const cu = G.comp.mat.uniforms;
    cu.site.value = G.rtSite.texture; cu.gal.value = G.rtGal.texture; cu.k.value = k; cu.exposure.value = 1.25 * (1 - smooth((t - 28.5) / 1.5));   // the horizon: fade to black
    ren.setRenderTarget(null); ren.clear(); ren.render(G.comp.scene, G.comp.cam);
    drawAstro(ren, G.real || 0);
  };
})();
