// The world of "Знайомся: Юпітер", built once in the page (render.js serves it). Units: 1 = 1000 km.
// Bodies are spheres drawn with one shader: an equirectangular map (longitude −180…180 east, left to right), sunlight
// with a soft terminator, a bump from the map's own brightness (so craters and ridges catch a low Sun), a faint fine
// grain so close-ups are not just a stretched picture, and optional extras: Jupiter's drifting bands and the turning
// Great Red Spot, glowing lava spots (Io), auroral ovals (Ganymede), an atmosphere rim (Earth), a low haze (Io).
// Shots (shots.js) move the camera and switch things on and off; window.startShot / renderShot drive them.
(() => {
  const T = THREE, D = Math.PI / 180;
  const W = 720, H = 1280;
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H); renderer.setPixelRatio(1); document.body.appendChild(renderer.domElement);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(40, W / H, 0.01, 50000);
  const loader = new T.TextureLoader();
  const load = f => new Promise((res, rej) => loader.load(f, t => { t.anisotropy = 16; t.wrapS = T.RepeatWrapping; res(t); }, undefined, rej));

  // A point on a body's surface (body frame: north = +y, longitude 0 = +x, east = toward −z).
  const dirLL = (lat, lon) => new T.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));

  const NOISE = `
    float h21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
    float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
    float fbm(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { s += a * vn(p); p *= 2.03; a *= 0.5; } return s; }`;

  const VS = `varying vec3 vO; varying vec3 vW; varying vec3 vN;
    void main() { vO = normalize(position); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz;
      vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`;

  const FS = `
    uniform sampler2D map; uniform vec3 sun; uniform float time, bump, detail, radius, amb, exposure;
    uniform vec3 ambCol;
    uniform float jup; uniform vec3 grs;            // Jupiter: Great Red Spot centre (lat, lon, rad), turning rate
    uniform float grsSpin, drift;
    uniform vec4 spots[4]; uniform vec3 spotCol;      // lava: lat, lon, radius (rad), strength
    uniform float aur, aurLat;                        // auroral ovals: strength, latitude (rad)
    uniform vec3 atmoCol; uniform float atmo;         // a glowing rim (Earth)
    uniform vec3 fogCol; uniform float fogK;          // low haze
    uniform float night;                              // extra light on the night side (Jupiter-shine)
    uniform mat3 rot;                                 // the body's turn (the model matrix is not in fragment shaders)
    varying vec3 vO; varying vec3 vW; varying vec3 vN;
    ${NOISE}
    vec2 llOf(vec3 d) { return vec2(asin(clamp(d.y, -1.0, 1.0)), atan(-d.z, d.x)); }
    vec2 uvOf(vec2 ll) { return vec2(fract((ll.y + 3.14159265) / 6.2831853), (ll.x + 1.5707963) / 3.14159265); }
    float lum(vec3 c) { return dot(c, vec3(0.3, 0.59, 0.11)); }
    void main() {
      vec3 o = normalize(vO);
      vec2 ll = llOf(o);
      vec2 tl = ll;
      if (jup > 0.5) {
        // zonal jets: neighbouring bands slide past each other
        tl.y += drift * time * (0.6 * sin(ll.x * 14.0) + 0.3 * sin(ll.x * 31.0 + 1.0));
        // the Great Red Spot turns (anticlockwise seen from above the south): rotate the map round its centre
        vec2 d = vec2((tl.y - grs.y) * cos(ll.x), tl.x - grs.x) / vec2(grs.z, grs.z * 0.62);
        float r = length(d);
        float ang = grsSpin * time * (1.0 - smoothstep(0.15, 1.35, r)) * (0.6 + 0.4 * (1.0 - smoothstep(0.3, 1.0, r)));
        float cs = cos(ang), sn = sin(ang);
        d = vec2(cs * d.x - sn * d.y, sn * d.x + cs * d.y) * vec2(grs.z, grs.z * 0.62);
        tl = vec2(grs.x + d.y, grs.y + d.x / max(cos(ll.x), 0.2));
        // fine eddies so a close look is not a stretched picture
        tl += detail * 0.0030 * (vec2(fbm(ll * vec2(160.0, 220.0) + time * 0.05), fbm(ll * vec2(160.0, 220.0) + 7.3 - time * 0.04)) - 0.5);
        tl += detail * 0.0012 * (vec2(fbm(ll * vec2(600.0, 800.0) - time * 0.08), fbm(ll * vec2(600.0, 800.0) + 3.1 + time * 0.07)) - 0.5);
      }
      vec2 uv = uvOf(tl);
      vec3 c = pow(texture2D(map, uv).rgb, vec3(2.2));
      // grain: a light multi-scale texture in the brightness, strongest close up
      float g = fbm(ll * radius * vec2(3.0, 3.0)) - 0.5;
      c *= 1.0 + detail * 0.22 * g;
      // bump from the map's brightness (east and north slopes), only where asked (rocky moons)
      vec3 n = o;
      if (bump > 0.0) {
        float e = 1.0 / 8192.0;
        float l0 = lum(texture2D(map, uv).rgb);
        float lx = lum(texture2D(map, uv + vec2(e, 0.0)).rgb), ly = lum(texture2D(map, uv + vec2(0.0, e * 2.0)).rgb);
        vec3 east = vec3(-sin(ll.y), 0.0, -cos(ll.y));
        vec3 north = vec3(-sin(ll.x) * cos(ll.y), cos(ll.x), sin(ll.x) * sin(ll.y));
        n = normalize(o - bump * ((lx - l0) * east + (ly - l0) * north));
      }
      vec3 nw = normalize(rot * n), nv = normalize(vN);
      vec3 V = normalize(cameraPosition - vW);
      float mu = dot(nw, sun), muG = dot(nv, sun);
      float dif = max(mu, 0.0) * smoothstep(-0.08, 0.12, muG);
      vec3 col = c * (dif * exposure + amb * ambCol + night * (1.0 - smoothstep(-0.1, 0.2, muG)) * ambCol);
      if (jup > 0.5) {
        col *= mix(0.5, 1.0, pow(max(dot(nv, V), 0.0), 0.35));                  // limb darkening
        col = col * col * (3.0 - 2.0 * min(col, vec3(1.0))) * 0.9 + col * 0.1; // a little more contrast in the bands
      }
      // lava: glowing where the ground is dark inside a spot, flickering
      for (int i = 0; i < 4; i++) {
        vec4 s = spots[i];
        if (s.w <= 0.0) continue;
        vec3 sd = vec3(cos(s.x) * cos(s.y), sin(s.x), -cos(s.x) * sin(s.y));
        float a = acos(clamp(dot(o, sd), -1.0, 1.0));
        float m = (1.0 - smoothstep(s.z * 0.45, s.z, a)) * smoothstep(0.70, 0.9, 1.0 - lum(texture2D(map, uv).rgb));
        // the crust is cooled dark; the heat shows along cracks and the shore, flickering
        float cr = 0.25 + 0.75 * smoothstep(0.55, 0.8, fbm(ll * radius * 55.0 + 3.0));
        m *= clamp(cr, 0.0, 1.0);
        float fl = 0.75 + 0.25 * fbm(ll * radius * 6.0 + time * 0.6);
        col += spotCol * s.w * m * fl;
      }
      if (aur > 0.0) {
        float b = exp(-pow((abs(ll.x) - aurLat) / 0.10, 2.0)) * (0.5 + 0.5 * fbm(vec2(ll.y * 7.0, time * 0.4)));
        float rim = pow(1.0 - max(dot(nv, V), 0.0), 2.0);
        col += vec3(0.5, 0.42, 1.0) * aur * b * (0.25 + 0.6 * rim) * (0.35 + 0.65 * (1.0 - smoothstep(-0.2, 0.3, muG)));
      }
      if (atmo > 0.0) {
        float rim = pow(1.0 - max(dot(nv, V), 0.0), 2.5);
        col = mix(col, atmoCol * max(muG, 0.0) * 1.5, atmo * (0.12 + 0.6 * rim));
      }
      if (fogK > 0.0) col = mix(col, fogCol * (0.25 + 0.75 * max(muG, 0.0)), 1.0 - exp(-length(cameraPosition - vW) * fogK));
      gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
    }`;

  function body(tex, R, opts = {}) {
    const u = {
      map: { value: tex }, sun: { value: new T.Vector3(1, 0, 0) }, time: { value: 0 }, bump: { value: opts.bump || 0 },
      detail: { value: opts.detail || 0 }, radius: { value: R }, amb: { value: opts.amb != null ? opts.amb : 0.002 },
      ambCol: { value: new T.Color(opts.ambCol || 0xffffff) }, exposure: { value: opts.exposure || 1.6 },
      jup: { value: opts.jup ? 1 : 0 }, grs: { value: new T.Vector3() }, grsSpin: { value: 0 }, drift: { value: 0 },
      spots: { value: [0, 1, 2, 3].map(() => new T.Vector4(0, 0, 0, 0)) }, spotCol: { value: new T.Color(1.0, 0.32, 0.07) },
      aur: { value: 0 }, aurLat: { value: 0 }, atmoCol: { value: new T.Color(0.35, 0.55, 1.0) }, atmo: { value: opts.atmo || 0 },
      fogCol: { value: new T.Color(0.9, 0.8, 0.45) }, fogK: { value: 0 }, night: { value: 0 }, rot: { value: new T.Matrix3() },
    };
    const m = new T.Mesh(new T.SphereGeometry(R, 256, 128), new T.ShaderMaterial({ uniforms: u, vertexShader: VS, fragmentShader: FS }));
    m.userData = { R, u };
    m.visible = false; scene.add(m);
    return m;
  }

  // Stars far away, following the camera.
  const sg = new T.BufferGeometry(), sp = [], sc = [];
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 4000; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.25 + 0.75 * Math.pow(rnd(), 4);
    sp.push(r * Math.cos(a) * 40000, u * 40000, r * Math.sin(a) * 40000); sc.push(b, b * 0.97, b * 1.03);
  }
  sg.setAttribute('position', new T.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new T.Float32BufferAttribute(sc, 3));
  const stars = new T.Points(sg, new T.PointsMaterial({ size: 1.7, sizeAttenuation: false, vertexColors: true, depthWrite: false, transparent: true }));
  scene.add(stars);

  // Pele's plume: particles thrown up from the vent on ballistic paths over the curved ground, an umbrella ~300 km
  // high and ~600 km out (Io's gravity 1.8 m/s², ~1 km/s), sped up so they visibly arc. Positions are computed here.
  const PN = 9000;
  const pg = new T.BufferGeometry();
  pg.setAttribute('position', new T.BufferAttribute(new Float32Array(PN * 3), 3));
  pg.setAttribute('alpha', new T.BufferAttribute(new Float32Array(PN), 1));
  const plumeMat = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    uniforms: { size: { value: 0.03 }, scale: { value: 1372 }, col: { value: new T.Color(0.78, 0.84, 1.0) }, gain: { value: 1 } },
    vertexShader: `attribute float alpha; varying float vA; uniform float size, scale;
      void main() { vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = clamp(size * scale / max(-mv.z, 0.001), 2.0, 96.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying float vA; uniform vec3 col; uniform float gain;
      void main() { vec2 d = gl_PointCoord - 0.5; float r = length(d); if (r > 0.5) discard; gl_FragColor = vec4(col * vA * gain * pow(1.0 - r * 2.0, 1.8), 1.0); }` });
  const plume = new T.Points(pg, plumeMat); plume.frustumCulled = false; plume.visible = false; scene.add(plume);
  const pp = [];
  for (let i = 0; i < PN; i++) { const el = (38 + 46 * rnd()) * D; pp.push({ ph: rnd(), az: rnd() * Math.PI * 2, el, v: (0.92 + 0.12 * rnd()) * Math.sin(63.4 * D) / Math.sin(el) }); }
  function updatePlume(bodyMesh, lat, lon, t, loop) {
    const R = bodyMesh.userData.R;
    plumeMat.uniforms.scale.value = H / (2 * Math.tan(camera.fov * D / 2));
    const up = dirLL(lat, lon), east = new T.Vector3(-Math.sin(lon * D), 0, -Math.cos(lon * D));
    const north = new T.Vector3().crossVectors(up, east).normalize();
    const pos = pg.attributes.position.array, al = pg.attributes.alpha.array;
    const v0 = 1.16, gk = 1.796e-3;                                 // km/s, km/s²
    for (let i = 0; i < PN; i++) {
      const q = pp[i], tau = ((q.ph + t / loop) % 1);
      const v = v0 * q.v, s = tau * 2 * v * Math.sin(q.el) / gk;     // each path's own flight time
      const hor = v * Math.cos(q.el) * s, ver = v * Math.sin(q.el) * s - gk * s * s / 2;   // km
      const ang = hor / (R * 1000);                                  // radians along the ground
      const dir = new T.Vector3().copy(up).multiplyScalar(Math.cos(ang))
        .addScaledVector(east, Math.sin(ang) * Math.cos(q.az)).addScaledVector(north, Math.sin(ang) * Math.sin(q.az));
      const r = R + Math.max(ver, 0) / 1000;
      const w = dir.multiplyScalar(r).applyMatrix4(bodyMesh.matrixWorld);
      pos[i * 3] = w.x; pos[i * 3 + 1] = w.y; pos[i * 3 + 2] = w.z;
      al[i] = ver > 0 ? 0.022 * Math.min(1, tau * 8) * Math.min(1, (1 - tau) * 4) : 0;
    }
    pg.attributes.position.needsUpdate = true; pg.attributes.alpha.needsUpdate = true;
  }

  // A drawn sprite (canvas), sized in pixels and turned on the screen.
  function canvas(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); return c; }
  function sprite(cv) {
    const s = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(cv), sizeAttenuation: false, transparent: true, depthWrite: false, depthTest: false }));
    s.visible = false; scene.add(s); return s;
  }
  const px = n => n / H * 2 * Math.tan(camera.fov * D / 2);
  // The Europa Clipper: a body with the big dish, two long five-panel solar wings
  const CLIPPER = canvas(512, 200, (g) => {
    g.shadowColor = 'rgba(190,215,255,0.8)'; g.shadowBlur = 10;
    for (const sx of [-1, 1]) {
      for (let k = 0; k < 5; k++) {
        const x0 = 256 + sx * (46 + k * 40), w = 36;
        const gr = g.createLinearGradient(0, 80, 0, 120); gr.addColorStop(0, '#3a5c9a'); gr.addColorStop(1, '#1b2c55');
        g.fillStyle = gr; g.fillRect(sx > 0 ? x0 : x0 - w, 82, w, 36);
        g.strokeStyle = 'rgba(160,190,240,0.5)'; g.lineWidth = 1; g.strokeRect(sx > 0 ? x0 : x0 - w, 82, w, 36);
      }
      g.fillStyle = '#9aa0a8'; g.fillRect(sx > 0 ? 256 + 30 : 256 - 46, 98, 16, 4);
    }
    const bd = g.createLinearGradient(0, 70, 0, 140); bd.addColorStop(0, '#f0e2b0'); bd.addColorStop(1, '#a8925a');
    g.fillStyle = bd; g.fillRect(236, 70, 40, 70);
    g.fillStyle = '#f4f5f6'; g.beginPath(); g.ellipse(256, 66, 30, 12, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#c9ccd1'; g.beginPath(); g.ellipse(256, 66, 22, 8, 0, 0, Math.PI * 2); g.fill();
  });
  const clipper = sprite(CLIPPER);
  const LABEL = text => canvas(512, 96, (g) => {
    g.font = '600 52px Commissioner, Arial, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.shadowColor = 'rgba(0,0,0,0.8)'; g.shadowBlur = 10; g.fillStyle = 'rgba(255,255,255,0.95)'; g.fillText(text, 256, 48);
  });

  // Full-screen passes: the dive into Jupiter's clouds and the dawn sky over Ukraine.
  const quadCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  function pass(fs, uniforms) {
    const sc = new T.Scene();
    const m = new T.Mesh(new T.PlaneGeometry(2, 2), new T.ShaderMaterial({ uniforms, vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }', fragmentShader: fs, depthTest: false }));
    sc.add(m); return { scene: sc, u: uniforms };
  }
  // Dive: a ray-marched cloud deck seen from inside, the camera sinking; three layers (white ammonia haze, tawny
  // ammonium hydrosulphide, bluish water clouds) by depth, the light dimming and reddening, now and then lightning.
  const dive = pass(`
    uniform float depth, time, aspect; varying vec2 vUv;
    ${NOISE}
    float n3(vec3 p) { vec2 o = vec2(37.0, 17.0); float y = floor(p.y), f = fract(p.y); f = f * f * (3.0 - 2.0 * f);
      return mix(vn(p.xz + o * y), vn(p.xz + o * (y + 1.0)), f); }
    float shape(vec3 p) { return n3(p * 0.28) * 0.55 + n3(p * 0.75 + 3.0) * 0.3 + n3(p * 2.1 + 7.0) * 0.15; }
    float dens(vec3 p) {
      float y = -p.y;                                         // depth below the cloud tops
      float deck = smoothstep(-0.6, 0.6, y) * (0.55 + 0.45 * smoothstep(3.0, 1.0, abs(mod(y, 5.5) - 2.75)));
      return smoothstep(0.50, 0.66, shape(p)) * deck;
    }
    vec3 layerCol(float y) {
      vec3 a = vec3(0.95, 0.93, 0.88), b = vec3(0.86, 0.6, 0.36), c = vec3(0.38, 0.44, 0.58);
      return y < 6.0 ? mix(a, b, smoothstep(1.5, 6.0, y)) : mix(b, c, smoothstep(8.0, 13.0, y));
    }
    void main() {
      vec2 q = (vUv - 0.5) * vec2(aspect, 1.0) * 1.3;
      vec3 ro = vec3(time * 0.9, -depth, time * 0.5);
      vec3 rd = normalize(vec3(q.x, -0.62 + q.y * 0.95, 1.0));
      vec3 col = vec3(0.0); float tr = 1.0;
      for (int i = 0; i < 64; i++) {
        float s = 0.2 + float(i) * 0.2;
        vec3 p = ro + rd * s;
        float d = dens(p);
        if (d > 0.01) {
          float y = -p.y;
          float sh = exp(-dens(p + vec3(0.25, 0.7, 0.1)) * 2.2);          // light from above, shadowed by the cloud
          float sky = exp(-max(y, 0.0) * 0.17);
          vec3 c = layerCol(y) * (0.05 + 1.05 * sky * (0.35 + 0.65 * sh)) + vec3(0.5, 0.11, 0.03) * smoothstep(9.0, 16.0, y) * (1.0 - sh * 0.5) * 0.14;
          float a = d * 0.42;
          col += tr * a * c; tr *= 1.0 - a;
          if (tr < 0.02) break;
        }
      }
      float up = smoothstep(-0.2, 0.5, rd.y);
      vec3 above = mix(vec3(0.62, 0.56, 0.5), vec3(0.08, 0.1, 0.18), smoothstep(-1.0, -4.0, -depth));
      vec3 below = mix(vec3(0.5, 0.55, 0.65) * exp(-depth * 0.15), vec3(0.09, 0.02, 0.012), smoothstep(9.0, 16.0, depth));
      col += tr * mix(below, above * exp(-max(depth, 0.0) * 0.12), up);
      float fl = step(0.982, h21(vec2(floor(time * 7.0), 3.0))) * smoothstep(5.0, 9.0, depth);
      col += vec3(0.75, 0.8, 1.0) * fl * 0.6 * exp(-length(q - vec2(0.15, -0.15)) * 2.5);
      gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
    }`, { depth: { value: 0 }, time: { value: 0 }, aspect: { value: W / H } });
  // Dawn over Ukraine: a dark sky brightening to blue and a thin orange band low in the east (left), stars fading,
  // Jupiter a bright point high in the south-east, a line of hills and trees below.
  const dawn = pass(`
    uniform float time, aspect, k; uniform vec2 jup; varying vec2 vUv;
    ${NOISE}
    void main() {
      vec2 p = vUv;
      float h = p.y;
      vec3 top = mix(vec3(0.01, 0.015, 0.05), vec3(0.04, 0.08, 0.2), k);
      vec3 mid = mix(vec3(0.03, 0.05, 0.12), vec3(0.18, 0.28, 0.48), k);
      vec3 low = mix(vec3(0.08, 0.07, 0.1), vec3(0.85, 0.48, 0.26), k);
      float east = 1.0 - p.x;                       // the east is on the left
      vec3 sky = mix(low, mid, smoothstep(0.18, 0.45, h + 0.08 * (1.0 - east)));
      sky = mix(sky, top, smoothstep(0.45, 1.0, h));
      // stars, fading with the dawn
      vec2 sp = p * vec2(aspect, 1.0) * 260.0; vec2 cell = floor(sp);
      float st = step(0.9965, h21(cell)) * smoothstep(0.35, 0.1, length(fract(sp) - 0.5)) * (1.0 - k * 0.85) * smoothstep(0.25, 0.5, h);
      sky += vec3(st);
      // Jupiter: a steady bright point with a soft glow
      vec2 d = (p - jup) * vec2(aspect, 1.0);
      float r = length(d);
      sky += vec3(1.0, 0.96, 0.88) * (exp(-r * 900.0) * 3.0 + exp(-r * 140.0) * 0.35 + exp(-r * 40.0) * 0.05);
      // the ground: rolling hills and a ragged tree line, in silhouette
      float hill = 0.19 + 0.018 * sin(p.x * 3.0 + 1.0) + 0.008 * sin(p.x * 9.0);
      float trees = hill + 0.022 * smoothstep(0.38, 0.62, fbm(vec2(p.x * 7.0, 1.0))) + 0.005 * fbm(vec2(p.x * 70.0, 2.0));
      float g = smoothstep(trees + 0.002, trees - 0.002, h);
      vec3 col = mix(sky, vec3(0.012, 0.014, 0.02) + low * 0.03, g);
      gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
    }`, { time: { value: 0 }, aspect: { value: W / H }, k: { value: 0 }, jup: { value: new T.Vector2(0.62, 0.62) } });

  (async () => {
    const [jt, et, io, eu, ga, ca, me] = await Promise.all([
      load('/site/jupiter.jpg'), load('/site/earth_day.jpg'), load('/maps/io.jpg'), load('/maps/europa.jpg'),
      load('/maps/ganymede.jpg'), load('/site/callisto.jpg'), load('/site/mercury.jpg')]);
    const jupiter = body(jt, 71.492, { jup: true, detail: 1, exposure: 1.0, amb: 0.0 });
    jupiter.scale.set(1, 66.854 / 71.492, 1);                    // flattened by its fast spin
    jupiter.userData.u.grs.value.set(-20.5 * D, -46.9 * D, 9.5 * D);
    const bodies = {
      jupiter,
      earth: body(et, 6.371, { atmo: 0.6, exposure: 1.4 }),
      io: body(io, 1.8216, { bump: 2.5, detail: 0.6, exposure: 1.25 }),
      europa: body(eu, 1.5608, { bump: 3.0, detail: 0.5, exposure: 1.0 }),
      ganymede: body(ga, 2.6341, { bump: 2.0, detail: 0.4, exposure: 1.3 }),
      callisto: body(ca, 2.4103, { bump: 1.5, detail: 0.4, exposure: 1.4 }),
      mercury: body(me, 2.4397, { bump: 1.5, detail: 0.4, exposure: 1.3 }),
    };
    window.J = { T, D, W, H, renderer, scene, camera, bodies, stars, plume, plumeMat, updatePlume, clipper, sprite, canvas, LABEL, px, dirLL, dive, dawn, quadCam };
    window.WORLD_READY = 1;
  })();

  // One shot at a time: everything hidden, then the shot shows what it needs.
  window.startShot = async (name) => {
    const J = window.J;
    for (const b of Object.values(J.bodies)) { b.visible = false; b.position.set(0, 0, 0); b.rotation.set(0, 0, 0); }
    J.plume.visible = false; J.clipper.visible = false; J.stars.visible = true;
    J.extra = [];
    const s = window.SHOTS[name];
    if (s.setup) await s.setup(J);
  };
  window.renderShot = (name, t) => {
    const J = window.J, s = window.SHOTS[name];
    const r = s.frame(J, t) || {};
    for (const b of Object.values(J.bodies)) {
      b.userData.u.time.value = t + (s.t0 || 0);
      b.updateMatrixWorld(true);
      b.userData.u.rot.value.setFromMatrix4(new J.T.Matrix4().extractRotation(b.matrixWorld));
    }
    J.stars.position.copy(J.camera.position);
    if (r.pass) { J.renderer.render(r.pass.scene, J.quadCam); }
    else { J.camera.updateProjectionMatrix(); J.renderer.render(J.scene, J.camera); }
    return J.renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
})();
