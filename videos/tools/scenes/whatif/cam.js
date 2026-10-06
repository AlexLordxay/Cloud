// "What if instead of the Moon…: what would happen to the Earth". Each world gets a place that shows what it would do:
// the Moon over night hills; Mars over a sea whose tide climbs a pier; Venus lighting a city's night like dusk; Neptune
// and Jupiter from space (the Earth now circles them; Jupiter hides the Sun); Saturn over mountains with a waking
// volcano; the Sun filling the sky; the Moon again. Bodies in the sky hang at the Moon's distance at their true
// angular size. Scene changes are dips through black (compose.py, CUTS); times must match captions.py (SETS).
(() => {
  const smooth = window.__smooth, D = Math.PI / 180;
  const SETS = [0, 5.6, 14.0, 22.4, 31.4, 40.4, 50.0, 57.4, 999];
  const DIST = 1000, MOON_KM = 384400;
  let ready = false, keep = null, root = null;
  const sets = [];

  const skyPos = (T, az, el, d = DIST) => new T.Vector3(Math.sin(az * D) * Math.cos(el * D) * d, Math.sin(el * D) * d, -Math.cos(az * D) * Math.cos(el * D) * d);
  const black = T => new T.MeshBasicMaterial({ color: new T.Color(0x020307).convertSRGBToLinear(), side: T.DoubleSide, toneMapped: false, fog: false });

  // A ring of ground silhouettes: h(az) in degrees above the horizon, R units away, from az0 to az1 (degrees).
  function ridge(T, h, R, az0, az1, mat, n = 900) {
    const pos = [];
    for (let i = 0; i < n; i++) {
      const a0 = (az0 + (az1 - az0) * i / n) * D, a1 = (az0 + (az1 - az0) * (i + 1) / n) * D;
      const y0 = R * Math.tan(h(a0 / D) * D), y1 = R * Math.tan(h(a1 / D) * D);
      const p = (a, y) => [Math.sin(a) * R, y, -Math.cos(a) * R];
      pos.push(...p(a0, -R), ...p(a1, -R), ...p(a0, y0), ...p(a1, -R), ...p(a1, y1), ...p(a0, y0));
    }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    const m = new T.Mesh(g, mat);
    m.material.transparent = true; m.renderOrder = 10;     // after the Sun and the sky, so it stays a silhouette
    return m;
  }
  const hillsH = az => { const a = az * D; return 0.9 + 0.7 * Math.sin(a * 3) + 0.45 * Math.sin(a * 8 + 1) + 0.25 * Math.sin(a * 23 + 2); };

  // Sky glow: a faint colour along the horizon fading upwards, plus a wide soft glow round the bright body.
  function skyDome(T, horizon, strength, bodyDir, bodyGlow) {
    return new T.Mesh(new T.SphereGeometry(1800, 64, 32), new T.ShaderMaterial({
      uniforms: { c: { value: new T.Color(...horizon) }, k: { value: strength }, b: { value: bodyDir.clone().normalize() }, bg: { value: bodyGlow } },
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform vec3 c, b; uniform float k, bg; varying vec3 vP;
        void main(){ if (vP.y < -0.02) discard; float h = exp(-max(vP.y, 0.0) * 7.0) * k;
          float g = pow(max(dot(vP, b), 0.0), 40.0) * bg + pow(max(dot(vP, b), 0.0), 6.0) * bg * 0.25;
          gl_FragColor = vec4(c * (h + g), 1.0); }`,
      side: T.BackSide, transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    }));
  }

  let load, ringTex;
  // A world hung in the sky at the Moon's distance, true angular size.
  async function skyBody(T, km, file, az, el, ring) {
    const ang = 2 * Math.atan(km / 2 / MOON_KM), rad = DIST * Math.tan(ang / 2);
    const node = new T.Group();
    const sph = new T.Mesh(new T.SphereGeometry(rad, 96, 64), new T.MeshStandardMaterial({ map: await load(file), roughness: 1, metalness: 0 }));
    sph.rotation.y = -Math.PI / 2;
    node.add(sph);
    if (ring) {
      node.add(ringMesh(rad * 1.24, rad * 2.27, ringTex, 0xffffff));
      node.rotation.x = 0.42; node.rotation.z = -0.18;
    }
    if (ang < 2.5 * D) node.add(glowSprite('230,236,255', Math.max(rad * 9, 20), 0.35));
    node.position.copy(skyPos(T, az, el));
    return { node, sph, rad };
  }
  // the Moon-like light from the left, and the site's faint fill (the site's own lights are switched off)
const moonLight = T => { const g = new T.Group(), l = new T.DirectionalLight(0xfff4e6, 2.3); l.position.set(-0.9, 0.35, 0.25); g.add(l, new T.AmbientLight(0x8fa0c8, 0.14)); return g; };
  const lookSky = (cam, T, az, el) => { cam.position.set(0, 0, 0); cam.up.set(0, 1, 0); cam.lookAt(skyPos(T, az, el, 10)); };

  function sunMaterial(T) {
    // fine granulation that keeps its size however close the surface comes (the pattern follows the sky direction)
    return new T.ShaderMaterial({
      uniforms: { opacity: { value: 1 }, time: { value: 0 } },
      vertexShader: 'varying vec3 vP; void main(){ vP = (modelMatrix * vec4(position, 1.0)).xyz - cameraPosition; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `
        uniform float opacity, time; varying vec3 vP;
        float h(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
        float n(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                     mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
        void main(){
          vec3 p = normalize(vP);
          float big = n(p * 9.0 + time * 0.02) * 0.6 + n(p * 19.0 - time * 0.03) * 0.4;
          float gr = n(p * 70.0 + time * 0.05) * 0.55 + n(p * 150.0 - time * 0.04) * 0.45;
          float v = clamp(0.25 + 0.45 * big + 0.45 * gr, 0.0, 1.0);
          gl_FragColor = vec4(mix(vec3(0.78, 0.30, 0.05), vec3(1.0, 0.78, 0.42), v) * 0.92, opacity);
        }`,
      transparent: true, depthTest: false, depthWrite: false,
    });
  }

  /* ---------- the places ---------- */

  // Night hills with the Moon (intro and the end).
  async function hillsSet(T) {
    const g = new T.Group();
    const moon = await skyBody(T, 3474, 'moon_2k.jpg', 4, 5.2);
    g.add(skyDome(T, [0.16, 0.24, 0.42], 0.16, moon.node.position, 0.05), ridge(T, hillsH, 600, 0, 360, black(T)), moon.node, moonLight(T));
    return { g, cam: (cam, t, u) => { lookSky(cam, T, 4 + 1.5 * u, 9); moon.node.rotation.y = 0.02 * t; } };
  }

  // Sea at night: Mars low over the water, its light a glittering path; the tide climbs a pier.
  async function seaSet(T) {
    const g = new T.Group();
    const AZ = 2, EL = 7;
    const mars = await skyBody(T, 6779, 'mars_2k.jpg', AZ, EL);
    const dir = mars.node.position.clone().normalize();
    const water = new T.Mesh(new T.PlaneGeometry(7000, 7000, 1, 1), new T.ShaderMaterial({
      uniforms: { time: { value: 0 }, b: { value: dir } },
      vertexShader: 'varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: `uniform float time; uniform vec3 b; varying vec3 vW;
        void main(){
          vec2 q = vW.xz; float d = length(q - cameraPosition.xz);
          float fade = 1.0 / (1.0 + d * 0.015);
          vec2 gr = vec2(0.0);
          vec3 W[7]; W[0] = vec3(0.8, 0.6, 0.55); W[1] = vec3(-0.3, 0.95, 0.9); W[2] = vec3(0.95, -0.2, 1.7); W[3] = vec3(0.2, 0.98, 3.1); W[4] = vec3(-0.7, 0.7, 5.3); W[5] = vec3(0.6, -0.8, 8.9); W[6] = vec3(-0.9, -0.4, 13.7);
          for (int i = 0; i < 7; i++) { vec2 dd = normalize(W[i].xy); float k = W[i].z;
            gr += dd * k * cos(dot(dd, q) * k + time * sqrt(9.8 * k) * 0.6 + float(i) * 1.7) * (0.05 / k) * (i < 3 ? 1.0 : fade * 1.4); }
          vec3 n = normalize(vec3(-gr.x, 1.0, -gr.y));
          vec3 v = normalize(vW - cameraPosition);
          vec3 r = reflect(v, n); r.y = abs(r.y);
          float fr = 0.02 + 0.98 * pow(1.0 - max(dot(-v, n), 0.0), 5.0);
          vec3 sky = mix(vec3(0.05, 0.075, 0.13), vec3(0.008, 0.012, 0.025), clamp(r.y * 5.0, 0.0, 1.0));
          float s = max(dot(r, b), 0.0);
          vec3 glint = vec3(1.0, 0.55, 0.38) * (pow(s, 1500.0) * 5.0 + pow(s, 200.0) * 0.35);
          vec3 c = vec3(0.003, 0.006, 0.012) + sky * fr + glint;
          gl_FragColor = vec4(c, 1.0);
        }`,
    }));
    water.rotation.x = -Math.PI / 2;
    // the pier: posts and a deck going out to sea on the right
    const wood = black(T), pier = new T.Group();
    for (let z = -3; z > -90; z -= 4.5) for (const x of [2.6, 4.4]) {
      const p = new T.Mesh(new T.BoxGeometry(0.28, 8, 0.28), wood); p.position.set(x, -4.9, z); pier.add(p);
    }
    const deck = new T.Mesh(new T.BoxGeometry(2.3, 0.22, 88), wood); deck.position.set(3.5, -0.95, -46); pier.add(deck);
    for (let z = -3; z > -90; z -= 9) {
      const rail = new T.Mesh(new T.BoxGeometry(0.1, 1.1, 0.1), wood); rail.position.set(4.6, -0.3, z); pier.add(rail);
    }
    const headland = ridge(T, az => az > 22 && az < 75 ? Math.max(0, 1.6 * Math.sin((az - 22) / 53 * Math.PI) + 0.3 * Math.sin(az * 0.7)) - 0.05 : -0.2, 1500, 15, 80, black(T), 300);
    g.add(skyDome(T, [0.14, 0.2, 0.36], 0.18, dir, 0.04), water, pier, headland, mars.node, moonLight(T));
    return { g, cam: (cam, t, u) => {
      // the tide comes in: from well below the deck to over it
      water.position.y = -2.9 + 2.3 * smooth(u * 1.15 - 0.05);
      water.material.uniforms.time.value = t;
      cam.position.set(0, 1.6, 0); cam.up.set(0, 1, 0);
      cam.lookAt(skyPos(T, 4 + 1.2 * u, 0.5, 10).add(cam.position));
    } };
  }

  // A city at night: Venus so bright the sky goes dusky blue.
  async function citySet(T) {
    const g = new T.Group();
    const AZ = -6, EL = 17;
    const venus = await skyBody(T, 12104, 'venus_atmosphere_2k.jpg', AZ, EL);
    const halo = glowSprite('255,248,230', 220, 0.55); venus.node.add(halo);
    const winMat = (w, h, seed) => new T.ShaderMaterial({
      uniforms: { s: { value: new T.Vector2(w, h) }, seed: { value: seed } },
      vertexShader: 'varying vec2 vU; void main(){ vU = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform vec2 s; uniform float seed; varying vec2 vU;
        float hs(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + seed) * 43758.5453); }
        void main(){
          vec2 p = vU * s / vec2(2.6, 3.2); vec2 c = floor(p), f = fract(p);
          vec3 col = vec3(0.010, 0.013, 0.024);
          bool top = vU.y * s.y > s.y - 3.5;
          float r = hs(c), r2 = hs(c + 7.1);
          if (!top && f.x > 0.28 && f.x < 0.72 && f.y > 0.3 && f.y < 0.78 && r > 0.66)
            col = mix(vec3(1.0, 0.74, 0.42), vec3(0.75, 0.84, 1.0), step(0.82, r2)) * (0.35 + 0.4 * r2);
          gl_FragColor = vec4(col, 1.0);
        }`,
      side: T.DoubleSide,
    });
    let seed = 1;
    const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (let i = 0; i < 90; i++) {
      const az = -48 + rnd() * 100, dist = 220 + rnd() * 380, w = 10 + rnd() * 26, h = 12 + Math.pow(rnd(), 1.6) * 75;
      const b = new T.Mesh(new T.PlaneGeometry(w, h + 40), winMat(w, h + 40, rnd() * 100));
      const base = -40;
      b.position.set(Math.sin(az * D) * dist, base + (h + 40) / 2, -Math.cos(az * D) * dist);
      b.lookAt(0, b.position.y, 0);
      g.add(b);
    }
    g.add(skyDome(T, [0.2, 0.3, 0.52], 0.5, venus.node.position, 0.22), venus.node, moonLight(T));
    return { g, cam: (cam, t, u) => { lookSky(cam, T, 1 + 2 * u, 10.5); venus.node.rotation.y = 0.02 * t; } };
  }

  // Mountains: Saturn and its rings over the ridges; a volcano wakes up with a faint glow and a slow plume.
  async function mountainSet(T) {
    const g = new T.Group();
    const sat = await skyBody(T, 116460, 'saturn.jpg', 4, 14.6, true);
    const far = ridge(T, az => 2.6 + 1.6 * Math.abs(Math.sin(az * 0.09 + 1)) + 0.8 * Math.abs(Math.sin(az * 0.31)) + 0.25 * Math.sin(az * 1.3),
      900, -90, 100, new T.MeshBasicMaterial({ color: new T.Color(0x0b1120).convertSRGBToLinear(), toneMapped: false }));
    far.renderOrder = 9;
    const VX = -5;   // the volcano's azimuth
    const near = ridge(T, az => {
      const v = Math.max(0, 5.4 - Math.abs(az - VX) * 0.55);              // the cone
      const crater = Math.abs(az - VX) < 1.1 ? -0.35 * (1 - Math.abs(az - VX) / 1.1) : 0;
      return Math.max(0.6 + 0.9 * Math.abs(Math.sin(az * 0.13)) + 0.3 * Math.sin(az * 0.9), v + crater);
    }, 500, -90, 100, black(T));
    const top = skyPos(T, VX, 5.0, 500);
    const glow = glowSprite('255,96,40', 46, 0.0); glow.position.copy(top); glow.renderOrder = 11;
    const plume = [];
    for (let i = 0; i < 9; i++) {
      const s = glowSprite('120,70,60', 18 + i * 5, 0.0); s.material.blending = T.NormalBlending; s.renderOrder = 11;
      g.add(s); plume.push(s);
    }
    g.add(skyDome(T, [0.16, 0.22, 0.4], 0.2, sat.node.position, 0.03), far, near, glow, sat.node, moonLight(T));
    return { g, cam: (cam, t, u) => {
      lookSky(cam, T, 1 + 1.5 * u, 12);
      const wake = smooth((u - 0.15) / 0.5);
      glow.material.opacity = 0.75 * wake * (0.9 + 0.1 * Math.sin(t * 1.3));
      plume.forEach((s, i) => {
        const k = (i / plume.length + t * 0.035) % 1;
        s.position.copy(top).add(new T.Vector3(k * 14, k * 60 + 3, 0));
        s.material.opacity = 0.32 * wake * Math.sin(k * Math.PI);
      });
    } };
  }

  // From space: an Earth with clouds and city lights, lit by the Sun from `sun` (direction).
  async function earthBall(T) {
    const R = 6.371;
    const night = await load('earth_night.jpg');
    const mat = new T.MeshStandardMaterial({ map: await load('earth_day_2k.jpg'), roughness: 1, metalness: 0, emissiveMap: night, emissive: 0xffd9a0, emissiveIntensity: 0.0 });
    const e = new T.Mesh(new T.SphereGeometry(R, 128, 96), mat);
    const ct = await load('earth_clouds.png'); ct.encoding = T.LinearEncoding;
    const cl = new T.Mesh(new T.SphereGeometry(R * 1.01, 128, 96), new T.MeshStandardMaterial({ color: 0xffffff, alphaMap: ct, roughness: 1, metalness: 0, transparent: true, depthWrite: false }));
    const atm = atmosphere(R * 1.045, [0.35, 0.6, 1.0], 3.0, 0.9);
    const grp = new T.Group(); grp.add(e, cl, atm);
    grp.rotation.z = 23.4 * D;
    return { grp, e, cl, mat, R, atm };
  }

  // Neptune from space, the Earth now its moon on a faint orbit line.
  async function neptuneSet(T) {
    const g = new T.Group();
    const RN = 24.62, A = 384.4;
    const nep = new T.Mesh(new T.SphereGeometry(RN, 128, 96), new T.MeshStandardMaterial({ map: await load('neptune.jpg'), roughness: 1, metalness: 0 }));
    nep.add(atmosphere(RN * 1.03, [0.4, 0.6, 1.0], 3.0, 0.8));
    const earth = await earthBall(T);
    const pts = []; for (let i = 0; i <= 360; i++) pts.push(new T.Vector3(Math.cos(i * D) * A, 0, Math.sin(i * D) * A));
    const orbit = new T.Line(new T.BufferGeometry().setFromPoints(pts), new T.LineBasicMaterial({ color: 0x9fb2d8, transparent: true, opacity: 0.28 }));
    const sun = new T.DirectionalLight(0xfff4e6, 2.6); sun.position.set(1, 0.15, 0.35);
    // far away the Earth is small: a soft blue glow helps it read on a phone
    earth.grp.add(glowSprite('120,170,255', 40, 0.45));
    g.add(nep, orbit, earth.grp, sun, sun.target, new T.AmbientLight(0x1a2030, 0.06));
    return { g, cam: (cam, t, u) => {
      const ph = (100 + 7 * u) * D;                       // the Earth moves along its new orbit
      earth.grp.position.set(Math.cos(ph) * A, 0, Math.sin(ph) * A);
      earth.e.rotation.y = 0.05 * t; earth.cl.rotation.y = 0.055 * t;
      const toE = earth.grp.position.clone().normalize();
      cam.up.set(0, 1, 0);
      cam.position.copy(toE).multiplyScalar(-122 + 10 * u).add(new T.Vector3(0, 62, 0));
      const dE = earth.grp.position.clone().sub(cam.position).normalize(), dN = cam.position.clone().negate().normalize();
      cam.lookAt(cam.position.clone().add(dE.multiplyScalar(0.55).add(dN.multiplyScalar(0.45))));
    } };
  }

  // Jupiter from the Earth's new orbit (almost where Io is): the Sun slips behind it and the Earth goes dark.
  async function jupiterSet(T) {
    const g = new T.Group();
    const RJ = 69.91, A = 384.4;
    const jup = new T.Mesh(new T.SphereGeometry(RJ, 160, 120), new T.MeshStandardMaterial({ map: await load('jupiter.jpg'), roughness: 1, metalness: 0 }));
    const rim = atmosphere(RJ * 1.025, [1.0, 0.78, 0.5], 4.0, 0.0); jup.add(rim);
    jup.rotation.y = 0.8;
    const earth = await earthBall(T);
    earth.grp.position.set(0, 0, A);
    const toJ = new T.Vector3(0, 0, -1);
    const camPos = new T.Vector3(0, 24, A + 36);
    const sunCore = glowSprite('255,250,235', 60, 1.0), sunGlow = glowSprite('255,214,160', 520, 0.5);
    for (const s of [sunCore, sunGlow]) { s.material.depthTest = true; s.renderOrder = 2; }
    const lJ = new T.DirectionalLight(0xfff4e6, 2.4), lE = new T.DirectionalLight(0xfff4e6, 2.4);
    g.add(jup, earth.grp, sunCore, sunGlow, lJ, lJ.target, lE, lE.target, new T.AmbientLight(0x1a2030, 0.03));
    // two lights from the Sun's direction: lJ stays on (Jupiter's lit edge), lE fades as the Sun hides (the Earth)
    return { g, cam: (cam, t, u) => {
      cam.position.copy(camPos).add(new T.Vector3(-3 * u, 0, 2 * u)); cam.up.set(0, 1, 0);
      // the Earth low in the frame, Jupiter above it
      const dE = earth.grp.position.clone().sub(cam.position).normalize(), dJ = cam.position.clone().negate().normalize();
      cam.lookAt(cam.position.clone().add(dE.multiplyScalar(0.4).add(dJ.multiplyScalar(0.6))));
      // the Sun's direction, as seen from the Earth: from beside Jupiter's limb to behind it
      const off = (11.8 - 9.5 * smooth(u * 1.1)) * D, rot = 168 * D;
      const s = toJ.clone().applyAxisAngle(new T.Vector3(1, 0, 0), off * Math.sin(rot)).applyAxisAngle(new T.Vector3(0, 1, 0), off * Math.cos(rot));
      const far = 4000;
      for (const sp of [sunCore, sunGlow]) sp.position.copy(earth.grp.position).addScaledVector(s, far);
      // how much of the Sun the Earth still sees past Jupiter's edge
      // judged from the camera, so the Earth darkens exactly as the Sun is seen to slip behind the limb
      const cs = sunCore.position.clone().sub(cam.position).normalize(), cj = cam.position.clone().negate();
      const angJ = Math.asin(RJ / cj.length()), sep = Math.acos(Math.min(1, cs.dot(cj.normalize())));
      const vis = smooth((sep - angJ + 0.35 * D) / (0.7 * D));
      lJ.position.copy(s); lJ.target.position.set(0, 0, 0);          // Jupiter: lit from behind, a thin bright edge
      lE.position.copy(earth.grp.position).addScaledVector(s, 10); lE.target.position.copy(earth.grp.position);
      lJ.intensity = 1.6; lE.intensity = 1.2 * vis;
      rim.material.uniforms.k.value = 0.15 + 0.55 * (1 - vis);
      earth.atm.material.uniforms.k.value = 0.25 + 0.65 * vis;
      earth.mat.emissiveIntensity = 1.4 * (1 - vis);
      earth.e.rotation.y = 0.05 * t; earth.cl.rotation.y = 0.055 * t;
    } };
  }

  // The Sun: grows from Jupiter's size until it covers the sky above the hills.
  async function sunSet(T) {
    const g = new T.Group();
    const sun = new T.Mesh(new T.SphereGeometry(1, 128, 96), sunMaterial(T));
    sun.renderOrder = 1;
    g.add(ridge(T, hillsH, 600, 0, 360, black(T)), sun);
    return { g, cam: (cam, t, u) => {
      const k = smooth(u * 0.95);
      const angR = (10 + 65 * k) * D, el = (14 + 16 * k), R = DIST * Math.sin(angR);
      sun.scale.setScalar(R); sun.position.copy(skyPos(T, 4, el));
      sun.material.uniforms.time.value = t;
      lookSky(cam, T, 4, 12.5 + 4 * k);
    } };
  }

  window.__sceneSetup = async (r) => {
    const T = r.THREE;
    keep = r.scene.children.find(o => o.isPoints && o.material.vertexColors);   // the starfield
    root = new T.Group(); r.scene.add(root);
    sunLight.visible = false;
    const loader = new T.TextureLoader();
    load = f => new Promise(res => loader.load('textures/' + f, t => { t.encoding = T.sRGBEncoding; t.anisotropy = 8; res(t); }));
    ringTex = await load('saturn_ring.png');
    const hillsA = await hillsSet(T), hillsB = await hillsSet(T);
    for (const s of [hillsA, await seaSet(T), await citySet(T), await neptuneSet(T), await mountainSet(T), await jupiterSet(T), await sunSet(T), hillsB]) {
      s.g.visible = false; root.add(s.g); sets.push(s);
    }
    ready = true;
  };

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, t = window.__vt() - (window.__t0 || 0);
    for (const o of r.scene.children) if (o !== keep && o !== root) o.visible = false;
    let k = 0;
    while (k < sets.length - 1 && t >= SETS[k + 1]) k++;
    sets.forEach((s, i) => { s.g.visible = i === k; });
    const u = Math.min(1, (t - SETS[k]) / (SETS[k + 1] - SETS[k]));
    sets[k].cam(r.camera, t, u);
    if (r.camera.near !== 0.3) { r.camera.near = 0.3; r.camera.updateProjectionMatrix(); }
  };
})();
