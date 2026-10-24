// "How long would you last on each planet?": the Nebozvid astronaut (characters/astronaut.js) on Mercury
// (glows red-hot and bursts into sparks), Venus (the visor cracks, it sinks to its knees, the yellow haze swallows it),
// Mars (survives and waves), Jupiter (no ground: falls through the clouds into the heat and lightning) and Neptune
// (frost on the visor, then the wind blows it away). The scene is its own, rendered in place of the site's; every
// frame is a pure function of time. Times are in seconds of the video and must match captions.py.
(() => {
  const D = Math.PI / 180, clamp = x => Math.min(1, Math.max(0, x)), smooth = x => { x = clamp(x); return x * x * (3 - 2 * x); };
  const lerp = (a, b, k) => a + (b - a) * k;
  const SEG = [[0, 'mercury'], [8, 'venus'], [15.5, 'mars'], [23, 'jupiter'], [30.5, 'neptune'], [38, 'end']];
  let S = null;
  let seed = 11;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const hash = i => { const v = Math.sin(i * 127.1 + 311.7) * 43758.5453; return v - Math.floor(v); };

  // ---- textures drawn in code ----
  function canvas(n) { const c = document.createElement('canvas'); c.width = c.height = n; return [c, c.getContext('2d')]; }
  // ground: blotches of light and dark, fine grain, and (Mercury) craters with bright rims
  function groundTex(T, craters) {
    const [c, g] = canvas(1024);
    g.fillStyle = '#808080'; g.fillRect(0, 0, 1024, 1024);
    for (let i = 0; i < 900; i++) {
      const x = rnd() * 1024, y = rnd() * 1024, r = 8 + Math.pow(rnd(), 2) * 90, v = 100 + rnd() * 60;
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, `rgba(${v},${v},${v},0.25)`); gr.addColorStop(1, `rgba(${v},${v},${v},0)`);
      g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    if (craters) for (let i = 0; i < 70; i++) {
      const x = rnd() * 1024, y = rnd() * 1024, r = 6 + Math.pow(rnd(), 3) * 70;
      const gr = g.createRadialGradient(x, y, r * 0.2, x, y, r);
      gr.addColorStop(0, 'rgba(60,60,60,0.55)'); gr.addColorStop(0.8, 'rgba(90,90,90,0.3)'); gr.addColorStop(0.92, 'rgba(200,200,200,0.5)'); gr.addColorStop(1, 'rgba(128,128,128,0)');
      g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    }
    const im = g.getImageData(0, 0, 1024, 1024), d = im.data;
    for (let i = 0; i < d.length; i += 4) { const n = (rnd() - 0.5) * 40; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
    g.putImageData(im, 0, 0);
    const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(30, 30); t.anisotropy = 8; t.encoding = T.sRGBEncoding;
    return t;
  }
  // a soft puff (clouds, haze, dust) and a hot spark
  function puffTex(T) {
    const [c, g] = canvas(256);
    for (let i = 0; i < 14; i++) {
      const x = 70 + rnd() * 116, y = 80 + rnd() * 96, r = 40 + rnd() * 50;
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, 'rgba(255,255,255,0.32)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    }
    return new T.CanvasTexture(c);
  }
  function sparkTex(T) {
    const [c, g] = canvas(64), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.6)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return new T.CanvasTexture(c);
  }
  // cracks spreading from a point on the visor (k: 0..1), or frost creeping in from the edges
  function crackDraw(g, k) {
    g.clearRect(0, 0, 512, 512);
    if (k <= 0) return;
    let s = 5; const r = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    const cx = 300, cy = 230;
    g.lineCap = 'round';
    const branch = (x, y, a, len, w, depth) => {
      let L = 0;
      g.beginPath(); g.moveTo(x, y);
      while (L < len) {
        const st = 10 + r() * 14; a += (r() - 0.5) * 0.7; x += Math.cos(a) * st; y += Math.sin(a) * st; L += st;
        g.lineTo(x, y);
        if (depth < 2 && r() < 0.12) branch(x, y, a + (r() < 0.5 ? 0.8 : -0.8), len * 0.4, w * 0.6, depth + 1);
      }
      g.strokeStyle = 'rgba(255,255,255,0.95)'; g.lineWidth = w; g.stroke();
    };
    const n = 11;
    for (let i = 0; i < n; i++) branch(cx, cy, i / n * 6.283 + r() * 0.4, 260 * k * (0.5 + r() * 0.6), 3.2, 0);
    // a few rings round the hit
    for (let i = 1; i <= 3; i++) if (k > i * 0.22) {
      g.beginPath();
      for (let j = 0; j <= 24; j++) { const a = j / 24 * 6.283, rr = i * 34 * (0.85 + 0.3 * r()); j ? g.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr) : g.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); }
      g.strokeStyle = 'rgba(255,255,255,0.7)'; g.lineWidth = 2; g.stroke();
    }
    const gr = g.createRadialGradient(cx, cy, 0, cx, cy, 26); gr.addColorStop(0, 'rgba(255,255,255,0.9)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(cx - 30, cy - 30, 60, 60);
  }
  function frostDraw(g, k) {
    g.clearRect(0, 0, 512, 512);
    if (k <= 0) return;
    let s = 9; const r = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    // feathery ice crystals growing inward from the rim
    for (let i = 0; i < 260; i++) {
      const a = r() * 6.283, x0 = 256 + Math.cos(a) * 270, y0 = 256 + Math.sin(a) * 270;
      const len = (90 + r() * 190) * k, dir = a + Math.PI + (r() - 0.5) * 0.9;
      const x1 = x0 + Math.cos(dir) * len, y1 = y0 + Math.sin(dir) * len;
      g.strokeStyle = `rgba(235,245,255,${0.35 + 0.4 * r()})`; g.lineWidth = 1 + r() * 2;
      g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
      for (let j = 1; j < 5; j++) {
        const f = j / 5, x = x0 + (x1 - x0) * f, y = y0 + (y1 - y0) * f, l = len * 0.18 * (1 - f);
        g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(dir + 0.7) * l, y + Math.sin(dir + 0.7) * l);
        g.moveTo(x, y); g.lineTo(x + Math.cos(dir - 0.7) * l, y + Math.sin(dir - 0.7) * l); g.stroke();
      }
    }
    const gr = g.createRadialGradient(256, 256, 60, 256, 256, 300);
    gr.addColorStop(0, 'rgba(220,235,255,0)'); gr.addColorStop(1, `rgba(220,235,255,${0.75 * k})`);
    g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
  }

  // ---- the sky: a gradient from the horizon up, a sun with its glow, and stars where the sky is dark ----
  function sky(T, o) {
    const u = {
      top: { value: new T.Color(...o.top) }, hor: { value: new T.Color(...o.hor) }, low: { value: new T.Color(...(o.low || o.hor)) },
      sun: { value: new T.Vector3(...o.sun).normalize() }, sunC: { value: new T.Color(...(o.sunC || [1, 1, 1])) },
      sunR: { value: o.sunR || 0 }, glow: { value: o.glow || 0 }, stars: { value: o.stars || 0 }, k: { value: 1 },
    };
    const m = new T.Mesh(new T.SphereGeometry(900, 64, 32), new T.ShaderMaterial({
      uniforms: u, side: T.BackSide, depthWrite: false, fog: false, toneMapped: true,
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform vec3 top, hor, low, sunC, sun; uniform float sunR, glow, stars, k; varying vec3 vD;
        float hs(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
        void main(){
          vec3 v = normalize(vD); float h = v.y;
          vec3 c = h > 0.0 ? mix(hor, top, pow(clamp(h, 0.0, 1.0), 0.55)) : mix(hor, low, pow(clamp(-h, 0.0, 1.0), 0.5));
          float a = acos(clamp(dot(v, sun), -1.0, 1.0));
          c += sunC * ((sunR > 0.0 ? smoothstep(sunR, sunR * 0.92, a) * 12.0 : 0.0) + glow * (exp(-a / (sunR * 3.0 + 0.001)) * 1.5 + exp(-a * 4.0) * 0.25));
          if (stars > 0.0) { vec3 q = floor(v * 420.0); float s = hs(q); c += vec3(0.9, 0.93, 1.0) * stars * step(0.9975, s) * (0.4 + 2.5 * (s - 0.9975) / 0.0025); }
          gl_FragColor = vec4(c * k, 1.0);
        }`,
    }));
    m.userData.u = u; return m;
  }

  function ground(T, tex, color, rough) {
    const m = new T.Mesh(new T.PlaneGeometry(800, 800), new T.MeshLambertMaterial({ map: tex, color }));
    m.rotation.x = -Math.PI / 2; m.receiveShadow = true; return m;
  }
  function rocks(T, n, color, spread, near) {
    const g = new T.Group(), mat = new T.MeshStandardMaterial({ color, roughness: 1, envMapIntensity: 0.2 });
    for (let i = 0; i < n; i++) {
      let geo = new T.IcosahedronGeometry(1, 3); geo.deleteAttribute('normal'); geo.deleteAttribute('uv'); const p = geo.attributes.position;
      for (let j = 0; j < p.count; j++) { const x = p.getX(j), y = p.getY(j), z = p.getZ(j), k = 0.75 + 0.18 * Math.sin(x * 2.1 + y * 3.3 + i) + 0.12 * Math.sin(y * 5.7 + z * 4.1 + 2 * i) + 0.06 * Math.sin(x * 9.1 - z * 8.3); p.setXYZ(j, x * k, y * k, z * k); }
      geo.computeVertexNormals();
      { const nn = geo.attributes.normal, v = new T.Vector3(); for (let j = 0; j < p.count; j++) { v.set(p.getX(j), p.getY(j), p.getZ(j)).normalize().lerp(new T.Vector3(nn.getX(j), nn.getY(j), nn.getZ(j)), 0.35).normalize(); nn.setXYZ(j, v.x, v.y, v.z); } }
      const m = new T.Mesh(geo, mat), a = (rnd() - 0.5) * 3.4, d = near + Math.pow(rnd(), 1.5) * spread, s = 0.06 + Math.pow(rnd(), 4) * 0.6 * (1 + d / 25);
      m.scale.set(s * (0.8 + rnd() * 0.8), s * (0.4 + rnd() * 0.4), s * (0.8 + rnd() * 0.6));
      m.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
      m.position.set(Math.sin(a) * d, m.scale.y * 0.25, Math.cos(a) * d);
      m.castShadow = m.receiveShadow = true; g.add(m);
    }
    return g;
  }
  // a cloud of sprites (puffs or sparks) that the frame function moves
  function sprites(T, tex, n, add) {
    const g = new T.Group();
    for (let i = 0; i < n; i++) {
      const s = new T.Sprite(new T.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, fog: false, blending: add ? T.AdditiveBlending : T.NormalBlending }));
      g.add(s);
    }
    return g;
  }

  window.__sceneSetup = async (r) => {
    const T = r.THREE, ren = r.renderer, scene = new T.Scene(), a = window.__makeAstronaut(T);
    await a.ready;
    scene.add(a.group);
    const key = a.light(0xffffff, 2, new T.Vector3(0.5, 0.6, -0.6)), fill = a.light(0x8090b0, 0.5, new T.Vector3(-0.6, 0.3, 0.5));
    fill.castShadow = false;
    const hemi = new T.HemisphereLight(0xffffff, 0x404040, 0.2);
    scene.add(key, key.target, fill, fill.target, hemi);
    const puff = puffTex(T), spark = sparkTex(T);
    const P = {};

    // Mercury: black sky with stars, a Sun three times bigger than ours low on the horizon, grey cratered ground
    P.mercury = new T.Group();
    P.mercury.add(sky(T, { top: [0, 0, 0], hor: [0.004, 0.004, 0.005], sun: [-0.13, 0.1, 1], sunR: 2.4 * D, glow: 0.35, sunC: [1, 0.9, 0.75], stars: 0.8 }));
    P.mercury.add(ground(T, groundTex(T, true), 0x26231f), rocks(T, 60, 0x1e1b18, 60, 4));
    P.mercury.userData = { fog: null, key: [0xfff2dd, 3.4, [-0.13, 0.22, 1]], fill: [0xb0a090, 0.55], hemi: [0x222222, 0x333333, 0.25], env: [-0.32, 0.09, 1] };
    const embers = sprites(T, spark, 160, true); P.mercury.add(embers);
    const halo = sprites(T, spark, 1, true).children[0]; halo.renderOrder = 2; P.mercury.add(halo);   // the heat glowing round the figure

    // Venus: thick yellow-orange haze, dim light from everywhere, dark flat rock slabs
    P.venus = new T.Group();
    P.venus.add(sky(T, { top: [0.1, 0.035, 0.005], hor: [0.3, 0.12, 0.02], sun: [0.2, 0.9, 0.3], sunR: 0, glow: 0.1, sunC: [1, 0.8, 0.5] }));
    P.venus.add(ground(T, groundTex(T, false), 0x3a2414), rocks(T, 70, 0x24160c, 40, 3));
    P.venus.userData = { fog: [0x5a2c08, 6, 45], key: [0xffc070, 1.1, [0.2, 0.9, -0.3]], fill: [0xd08040, 0.6], hemi: [0xffc080, 0x603010, 0.7], env: [0.2, 0.9, -0.3] };
    const haze = sprites(T, puff, 30, false); P.venus.add(haze);

    // Mars: butterscotch sky, rusty ground with stones, a small pale Sun; dust drifting
    P.mars = new T.Group();
    P.mars.add(sky(T, { top: [0.08, 0.03, 0.012], hor: [0.42, 0.18, 0.07], sun: [-0.5, 0.3, 1], sunR: 0.5 * D, glow: 0.6, sunC: [1, 0.95, 0.88] }));
    P.mars.add(ground(T, groundTex(T, false), 0x8a3a1c), rocks(T, 90, 0x4a1e0e, 60, 3));
    P.mars.userData = { fog: [0x8a4a26, 25, 220], key: [0xffe6cc, 2.4, [0.6, 0.35, -0.7]], fill: [0xc07a50, 0.35], hemi: [0xe0a070, 0x502010, 0.35], env: [0.6, 0.35, -0.7] };
    const dust = sprites(T, puff, 24, false); P.mars.add(dust);

    // Jupiter: no ground — bands of cloud rushing up past the falling figure, a glowing depth below, lightning
    P.jupiter = new T.Group();
    P.jupiter.add(sky(T, { top: [0.42, 0.3, 0.18], hor: [0.3, 0.18, 0.09], low: [0.15, 0.05, 0.015], sun: [0.3, 1, -0.2], sunR: 0, glow: 0 }));
    P.jupiter.userData = { fog: null, key: [0xfff0dc, 1.8, [0.3, 1, -0.2]], fill: [0xff7a30, 0.5], hemi: [0xf0d8b0, 0x7a3010, 0.5], env: [0.3, 1, -0.2] };
    const clouds = sprites(T, puff, 110, false); P.jupiter.add(clouds);
    const bolt = new T.PointLight(0xc8d8ff, 0, 30); P.jupiter.add(bolt);

    // Neptune: deep blue air high above the cloud deck, thin white streaks of cloud racing past
    P.neptune = new T.Group();
    P.neptune.add(sky(T, { top: [0.02, 0.05, 0.16], hor: [0.12, 0.3, 0.62], low: [0.05, 0.14, 0.4], sun: [-0.4, 0.5, 1], sunR: 0.05 * D, glow: 0.35, sunC: [0.9, 0.95, 1], stars: 0.3 }));
    P.neptune.userData = { fog: null, key: [0xd8e8ff, 1.3, [0.4, 0.5, -0.8]], fill: [0x3060c0, 0.5], hemi: [0x6090e0, 0x10204a, 0.5], env: [0.4, 0.5, -0.8] };
    const streaks = sprites(T, puff, 70, false); P.neptune.add(streaks);

    for (const k in P) { P[k].visible = false; scene.add(P[k]); P[k].userData.envMap = window.__astronautEnv(T, ren, { warm: new T.Vector3(...P[k].userData.env) }); }

    // the visor overlays: cracks (Venus) and frost (Neptune), on a shell just over the visor
    const [cc, cg] = canvas(512), crackT = new T.CanvasTexture(cc);
    const [fc, fg] = canvas(512), frostT = new T.CanvasTexture(fc);
    const P0 = 1.13 * Math.PI, PL = 0.74 * Math.PI, T0 = 0.2 * Math.PI, TL = 0.46 * Math.PI;
    const shell = (tex) => {
      const m = new T.Mesh(new T.SphereGeometry(a.visor ? a.visor.r + 0.0025 : 0.1792, 48, 32, P0 - 0.06, PL + 0.12, T0 - 0.05, TL + 0.1),
        new T.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0.9 }));
      if (a.visor) m.position.copy(a.visor.center); else m.position.set(0, 0.16, 0);
      m.scale.set(1, 1.03, 1.06); m.renderOrder = 3; a.joints.head.add(m); return m;
    };
    const crack = shell(crackT), frost = shell(frostT);

    // a full-screen flash in front of the camera (the heat flash, lightning)
    const cam = new T.PerspectiveCamera(32, 720 / 1280, 0.05, 2000);
    const flash = new T.Mesh(new T.PlaneGeometry(10, 10), new T.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthTest: false, depthWrite: false, toneMapped: false, fog: false }));
    flash.position.z = -1; flash.renderOrder = 999; cam.add(flash); scene.add(cam);

    // the astronaut's feet: where the lowest point of the standing figure is
    S = { T, scene, a, cam, key, fill, hemi, P, embers, halo, haze, dust, clouds, bolt, streaks, crack, crackT, cg, frost, frostT, fg, flash, lastCrack: -1, lastFrost: -1 };
  };

  // ---- poses: set joint angles (on top of the free-fall idle) ----
  function setJ(J, p) {
    for (const k in p) {
      if (k === 'body') J.body.rotation.set(...p.body);
      else J[k].rotation.set(...p[k]);
    }
  }
  const stand = (t, s = 1) => ({
    body: [0.02, 0, 0], head: [-0.05 + 0.02 * Math.sin(t * 0.7), 0.06 * Math.sin(t * 0.5), 0],
    shoulderL: [0.08, 0, -0.22], shoulderR: [0.08, 0, 0.22], elbowL: [0.35, 0, 0], elbowR: [0.35, 0, 0],
    wristL: [0.1, 0, 0], wristR: [0.1, 0, 0],
    hipL: [0.04, 0, -0.06], hipR: [0.04, 0, 0.06], kneeL: [-0.08, 0, 0], kneeR: [-0.08, 0, 0], ankleL: [0.04, 0, 0], ankleR: [0.04, 0, 0],
  });
  const mix = (p, q, k) => { const o = {}; for (const key in p) o[key] = p[key].map((v, i) => v + ((q[key] || p[key])[i] - v) * k); return o; };

  function placeOnGround(a) {
    a.group.position.y = 0; a.group.updateMatrixWorld(true);
    const b = new S.T.Box3().setFromObject(a.group);
    a.group.position.y = -b.min.y;
  }
  function look(env, T) {
    const u = env.userData, s = S;
    s.scene.fog = u.fog ? new T.Fog(u.fog[0], u.fog[1], u.fog[2]) : null;
    s.key.color.set(u.key[0]); s.key.intensity = u.key[1]; s.key.userData.dir.set(...u.key[2]).normalize();
    s.fill.color.set(u.fill[0]); s.fill.intensity = u.fill[1]; s.fill.userData.dir.set(-0.5, 0.3, -0.8).normalize();
    s.hemi.color.set(u.hemi[0]); s.hemi.groundColor.set(u.hemi[1]); s.hemi.intensity = u.hemi[2];
    s.scene.environment = u.envMap;
  }
  function heat(a, k, c) {   // the suit glowing: k 0..1, colour c
    for (const m of a.materials) if (m.emissive) m.emissive.setRGB(c[0] * k, c[1] * k, c[2] * k);
  }

  window.__recCam = () => {};
  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer;
    if (!S) { ren.render(r.scene, r.camera); return; }
    const { T, scene, a, cam, P, flash } = S, t = window.__vt() - (window.__t0 || 0), J = a.joints;
    let i = 0; while (i < SEG.length - 1 && t >= SEG[i + 1][0]) i++;
    const name = SEG[i][1] === 'end' ? 'mars' : SEG[i][1], lt = t - SEG[i][0];
    for (const k in P) P[k].visible = k === name;
    look(P[name], T);
    // reset what the effects change
    a.pose(t * 0.6); a.setTint(1, 1, 1); a.setOpacity(1); heat(a, 0, [0, 0, 0]);
    a.group.rotation.set(0, 0, 0); a.group.position.set(0, 0, 0); a.group.scale.setScalar(1);
    a.rim.color.value.setRGB(0, 0, 0);
    flash.material.opacity = 0; S.crack.visible = false; S.frost.visible = false; S.halo.visible = false;
    let camPos = [0.6, 1.35, 6.8], camAt = [0, 1.55, 0], shake = 0;

    if (name === 'mercury') {
      // stands, looks at the huge Sun; the suit heats: dull red, orange, white-yellow; a flash; only sparks left
      const h = smooth((lt - 1.4) / 3.9);
      setJ(J, mix(stand(lt), { head: [0.15, 0.5, 0], shoulderR: [0.5, 0, 0.4], elbowR: [1.4, 0, 0] }, smooth((lt - 0.3) / 1.2) * (1 - smooth((lt - 3.5) / 1))));
      placeOnGround(a);
      a.group.rotation.y = 0.45;
      heat(a, 0.75 * h, [1.0, 0.1 + 0.35 * Math.pow(h, 4), 0.02 + 0.08 * Math.pow(h, 6)]);
      a.setTint(1 - 0.55 * h, 1 - 0.8 * h, 1 - 0.88 * h);
      a.rim.color.value.setRGB(1.2 * h, 0.5 * h, 0.1 * h);
      const boom = 5.4, gone = smooth((lt - boom) / 0.35);
      S.halo.visible = true; S.halo.position.set(0, 0.95, 0); S.halo.scale.set(2.6 + 0.6 * h, 3.4 + 0.6 * h, 1); S.halo.material.opacity = 0.55 * h * (1 - gone); S.halo.material.color.setRGB(1, 0.3 + 0.25 * h, 0.08);
      a.setOpacity(1 - gone);
      flash.material.color.setRGB(1, 0.55, 0.2);
      flash.material.opacity = 0.95 * smooth((lt - boom + 0.25) / 0.25) * (1 - smooth((lt - boom - 0.1) / 0.9));
      shake = 0.012 * h * (1 - gone);
      // sparks: a few rise off the hot suit, then a burst at the flash that drifts up and dims
      S.embers.children.forEach((s, j) => {
        const burst = j > 40, t0 = burst ? boom : 2.2 + hash(j) * 3, age = lt - t0, life = burst ? 2.2 + hash(j + 7) * 0.8 : 1.2;
        if (age < 0 || age > life) { s.visible = false; return; }
        s.visible = true;
        const dir = new T.Vector3(hash(j + 1) - 0.5, hash(j + 2) * 0.6 + (burst ? 0.1 : 0.5), hash(j + 3) - 0.5).normalize();
        const sp = burst ? 0.8 + hash(j + 4) * 1.6 : 0.3, d = sp * (1 - Math.exp(-age * 1.6)) / 1.6 * 1.6;
        s.position.set(dir.x * d + (hash(j + 5) - 0.5) * 0.5, 0.9 + (hash(j + 6) - 0.5) * 1.4 + dir.y * d + age * 0.25, dir.z * d);
        const f = 1 - age / life, sz = (burst ? 0.05 : 0.035) * (0.6 + hash(j + 8));
        s.scale.setScalar(sz); s.material.color.setRGB(1, 0.55 + 0.35 * f, 0.2 * f); s.material.opacity = f;
      });
      camPos = [0.9 - 0.3 * lt / 8, 1.35, 7.0 - 0.6 * lt / 8];
    }

    if (name === 'venus') {
      // the haze presses in; a crack in the visor, it drops to its knees, the yellow murk swallows it
      const ck = smooth((lt - 1.6) / 0.5) * 0.55 + 0.45 * smooth((lt - 3.2) / 1.2);
      const kneel = smooth((lt - 2.6) / 1.4);
      setJ(J, mix(mix(stand(lt), { head: [0.25, -0.3, 0], shoulderL: [0.6, 0, -0.5], elbowL: [1.8, 0, 0] }, smooth((lt - 1.6) / 0.6)),
        { body: [-0.55 - 0.3 * smooth((lt - 4.2) / 1.5), 0, 0.05], head: [0.35, 0, 0], shoulderL: [1.05, 0, -0.2], shoulderR: [1.05, 0, 0.2], elbowL: [0.2, 0, 0], elbowR: [0.2, 0, 0],
          hipL: [0.65, 0, -0.1], hipR: [0.65, 0, 0.1], kneeL: [-1.6, 0, 0], kneeR: [-1.6, 0, 0], ankleL: [0.6, 0, 0], ankleR: [0.6, 0, 0] }, kneel));
      placeOnGround(a);
      a.group.rotation.y = -0.35;
      a.group.scale.set(1 + 0.04 * kneel, 1 - 0.06 * kneel, 1 + 0.04 * kneel);   // pressed down
      a.setTint(1, 0.9, 0.75);
      S.crack.visible = ck > 0;
      const q = Math.round(ck * 30);
      if (q !== S.lastCrack) { crackDraw(S.cg, q / 30); S.crackT.needsUpdate = true; S.lastCrack = q; }
      shake = 0.02 * Math.exp(-Math.max(0, lt - 1.6) * 4) * (lt > 1.6 ? 1 : 0) + 0.006 * kneel;
      // fog: from a heavy haze to a wall of murk
      const f = smooth((lt - 4.2) / 2.6);
      scene.fog.near = lerp(6, 0.5, f); scene.fog.far = lerp(45, 5.0, f);
      S.haze.children.forEach((s, j) => {
        const x = ((hash(j) * 16 + lt * (0.4 + hash(j + 1) * 0.5)) % 16) - 8, z = hash(j + 2) * 10 - 2;
        s.position.set(x, 0.3 + hash(j + 3) * 2.4, z); s.scale.setScalar(3 + hash(j + 4) * 3);
        s.material.color.setRGB(0.45, 0.2, 0.04); s.material.opacity = 0.12 + 0.4 * f;
      });
      camPos = [0.5, 1.35 - 0.15 * kneel, 6.6 - 0.8 * lt / 7.5]; camAt = [0, 1.55 - 0.3 * kneel, 0];
    }

    if (name === 'mars') {
      // survives: looks round, then waves at you; dust drifting past
      const end = SEG[i][1] === 'end', lw = end ? lt + 6 : lt;
      const w = Math.sin(2 * Math.PI * 1.4 * lw);
      const waveK = smooth((lw - 2.6) / 0.8);
      setJ(J, mix(mix(stand(lw), { head: [0.05, 0.6 * Math.sin(lw * 0.8), 0] }, 1 - waveK),
        { head: [-0.05, 0, 0.12], shoulderR: [0.5, 0, 2.3], elbowR: [0.55 + 0.45 * w, 0, 0], wristR: [0, 0, 0.2 * w], shoulderL: [0.1, 0, -0.3] }, waveK));
      placeOnGround(a);
      a.group.rotation.y = 0.25;
      a.rim.color.value.setRGB(0.25, 0.15, 0.08);
      S.dust.children.forEach((s, j) => {
        const x = ((hash(j) * 20 + lw * (0.8 + hash(j + 1))) % 20) - 10;
        s.position.set(x, 0.1 + hash(j + 3) * 1.2, hash(j + 2) * 12 - 2); s.scale.setScalar(1.5 + hash(j + 4) * 2.5);
        s.material.color.setRGB(0.6, 0.28, 0.12); s.material.opacity = 0.1;
      });
      camPos = end ? [0.3, 1.3, 8.0] : [0.9 - 0.4 * lt / 7.5, 1.35, 7.0 - 0.8 * lt / 7.5];
      if (end) camAt = [0, 1.3, 0];
    }

    if (name === 'jupiter') {
      // falls: the clouds rush up faster and faster, it gets darker and hotter below; lightning; it glows and is gone
      a.pose(lt * 1.3);
      a.group.position.set(0, 0, 0);
      a.group.rotation.set(-0.5 + 0.1 * Math.sin(lt), 0.4 * Math.sin(lt * 0.4), 0.2 * Math.sin(lt * 0.7));
      const v = 3 + lt * 2.2, fallen = 3 * lt + 1.1 * lt * lt;   // the clouds' speed and how far they have come
      const deep = smooth((lt - 1) / 6);
      const sk = P.jupiter.children[0].userData.u;
      sk.top.value.setRGB(lerp(0.42, 0.12, deep), lerp(0.3, 0.05, deep), lerp(0.18, 0.02, deep));
      sk.hor.value.setRGB(lerp(0.3, 0.3, deep), lerp(0.18, 0.08, deep), lerp(0.09, 0.02, deep));
      sk.low.value.setRGB(lerp(0.15, 1.6, deep), lerp(0.05, 0.4, deep), lerp(0.015, 0.05, deep));
      const BAND = [[0.85, 0.62, 0.38], [0.5, 0.22, 0.08], [0.28, 0.1, 0.03], [0.9, 0.78, 0.6], [0.62, 0.3, 0.1]];
      S.clouds.children.forEach((s, j) => {
        const ang = hash(j) * 6.283, rad = 1.6 + hash(j + 1) * 7, span = 40;
        const y = ((hash(j + 2) * span + fallen) % span) - span * 0.6;
        s.position.set(Math.cos(ang) * rad, y, Math.sin(ang) * rad + 1);
        const b = BAND[Math.floor(hash(j + 3) * 5)], dk = lerp(0.6, 0.25, deep);
        s.material.color.setRGB(b[0] * dk + 0.3 * deep, b[1] * dk + 0.04 * deep, b[2] * dk);
        s.scale.set(3 + hash(j + 4) * 4, (3 + hash(j + 4) * 4) * (1 + v * 0.06), 1);
        s.material.opacity = 0.7;
      });
      // lightning deep in the clouds: two quick flickers each
      let L = 0;
      for (const [t0, x, y] of [[2.1, -2, -6], [3.9, 3, -9], [5.2, -1, -5]]) { const d = lt - t0; if (d > 0 && d < 0.35) L = Math.max(L, (d < 0.06 || (d > 0.14 && d < 0.22)) ? 1 : 0.15); if (d > 0 && d < 0.35) S.bolt.position.set(x, y, 2); }
      S.bolt.intensity = 25 * L; flash.material.color.setRGB(0.85, 0.9, 1); flash.material.opacity = 0.25 * L;
      // heat from below: the suit glows, then fades into the depths
      const h = smooth((lt - 4) / 2.5);
      heat(a, h * 1.2, [1, 0.35, 0.08]); a.rim.color.value.setRGB(0.9 * deep, 0.35 * deep, 0.1 * deep);
      a.setOpacity(1 - smooth((lt - 6.2) / 1.0));
      S.fill.intensity = 0.5 + 2 * deep; S.fill.userData.dir.set(0, -1, 0.2).normalize();
      shake = 0.008 + 0.012 * deep;
      camPos = [1.4, 2.8, 6.2]; camAt = [0, 0.35, 0];
    }

    if (name === 'neptune') {
      // floats in the blue; frost grows over the visor and the suit whitens; a gust sweeps it away, tumbling
      a.pose(lt * 0.8);
      const fr = smooth((lt - 0.8) / 3.2), gust = smooth((lt - 3.8) / 1.0), away = Math.max(0, lt - 4.0);
      S.frost.visible = fr > 0;
      const q = Math.round(fr * 30);
      if (q !== S.lastFrost) { frostDraw(S.fg, q / 30); S.frostT.needsUpdate = true; S.lastFrost = q; }
      a.setTint(lerp(1, 0.85, fr), lerp(1, 0.93, fr), lerp(1, 1.1, fr));
      a.rim.color.value.setRGB(0.3 * fr, 0.5 * fr, 0.8 * fr);
      a.group.position.set(-0.9 * away * away - 0.4 * away, 0.2 * Math.sin(lt * 1.3) + 0.3 * away, 1.2 * away * away);
      a.group.rotation.set(0.1 + 1.0 * away * away, 0.3 * Math.sin(lt * 0.5) - 1.2 * away, 0.15 * Math.sin(lt * 0.9) + 2.0 * away * away);
      const sp = 6 + 60 * gust;
      S.streaks.children.forEach((s, j) => {
        const span = 60, x = span * 0.5 - ((hash(j) * span + lt * sp * (0.7 + 0.6 * hash(j + 1))) % span);
        s.position.set(x, -4 + hash(j + 2) * 8, 3 + hash(j + 3) * 20);
        s.scale.set(6 + 10 * hash(j + 4) + 10 * gust, 0.25 + 0.4 * hash(j + 5), 1);
        s.material.color.setRGB(0.85, 0.92, 1); s.material.opacity = 0.35 + 0.3 * gust;
      });
      shake = 0.004 + 0.02 * gust;
      camPos = [0.4, 0.7, 6.4]; camAt = [0, 0.65, 0];
    }

    // a push-in on the helmet: k 0..1 between the wide shot and a close-up of the visor
    const closeK = name === 'venus' ? smooth((lt - 1.2) / 0.6) * (1 - smooth((lt - 3.0) / 0.8)) : name === 'neptune' ? smooth((lt - 1.2) / 0.8) * (1 - smooth((lt - 3.3) / 0.6)) : 0;
    if (closeK > 0) {
      a.group.updateMatrixWorld(true);
      const hp = J.head.localToWorld(new T.Vector3(0, 0.16, 0)), fw = J.head.localToWorld(new T.Vector3(0, 0.16, -1)).sub(hp).normalize();
      const cp = hp.clone().addScaledVector(fw, 0.85).add(new T.Vector3(0.12, 0.05, 0));
      camPos = camPos.map((v, k) => lerp(v, [cp.x, cp.y, -cp.z][k], closeK));
      camAt = camAt.map((v, k) => lerp(v, [hp.x, hp.y, -hp.z][k], closeK));
    }
    // camera, with a small shake (a function of time)
    const sx = shake * (Math.sin(t * 61) + Math.sin(t * 37)), sy = shake * (Math.sin(t * 53 + 1) + Math.sin(t * 29));
    cam.position.set(camPos[0] + sx, camPos[1] + sy, -camPos[2]);
    cam.lookAt(camAt[0] + sx * 0.5, camAt[1] + sy * 0.5, -camAt[2]);
    a.aim();
    const tm = ren.toneMapping, te = ren.toneMappingExposure, sm = ren.shadowMap.enabled, st = ren.shadowMap.type;
    ren.toneMapping = T.ACESFilmicToneMapping; ren.toneMappingExposure = 1.0; ren.shadowMap.enabled = true; ren.shadowMap.type = T.PCFSoftShadowMap;
    ren.setRenderTarget(null); ren.render(scene, cam);
    ren.toneMapping = tm; ren.toneMappingExposure = te; ren.shadowMap.enabled = sm; ren.shadowMap.type = st;
  };
})();
