// Mercury's terrain round a site (terrain_data.py): the in-page code that builds it for terrain.js. Built like
// moon_meet/world.js — a mesh from the heights (exaggerated by meta.ex and bent to the planet's curvature), coloured
// with the MESSENGER albedo, lit with a normal map and the shadows baked for the site's Sun — plus what Mercury needs:
//   * the Sun's disc: white, sharp, 1.4° across (2.5 times what we see from the Earth; up to 1.7° at perihelion),
//     with only a faint glow (no air to scatter it);
//   * a moving Sun (meta.els): shadows baked for several elevations, blended for the elevation of the moment;
//   * ice (meta.ice): the permanently shadowed crater floors given a faint cold glow, as in the radar maps.
// Units: km, x east, y up, z south.
exports.mercuryWorld = (shot, meta) => `async function buildMercury() {
  const meta = ${JSON.stringify(meta)};
  const hb = new Float32Array(await (await fetch('/data/height.bin')).arrayBuffer());
  const N = meta.n, S = ${shot.mesh || 1536}, step = (N - 1) / (S - 1), EX = meta.ex;
  const R = meta.R / 1000, dx = meta.dx / 1000, dy = meta.dy / 1000;
  const pos = new Float32Array(S * S * 3), uv = new Float32Array(S * S * 2);
  for (let j = 0; j < S; j++) for (let i = 0; i < S; i++) {
    const gi = Math.round(i * step), gj = Math.round(j * step), k = j * S + i;
    const x = (gi - (N - 1) / 2) * dx, z = (gj - (N - 1) / 2) * dy;
    const h = hb[gj * N + gi] / 1000 * EX;
    pos[k * 3] = x; pos[k * 3 + 1] = h - (x * x + z * z) / (2 * R); pos[k * 3 + 2] = z;
    uv[k * 2] = gi / (N - 1); uv[k * 2 + 1] = 1 - gj / (N - 1);
  }
  const idx = new Uint32Array((S - 1) * (S - 1) * 6); let n = 0;
  for (let j = 0; j < S - 1; j++) for (let i = 0; i < S - 1; i++) { const a = j * S + i; idx.set([a, a + S, a + 1, a + 1, a + S, a + S + 1], n); n += 6; }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  const load = f => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }, undefined, () => r(null)));
  const ELS = meta.els || [];
  const names = ['colour.jpg', 'normal.png', 'shadow.png', meta.ice ? 'ice.png' : 'shadow.png'].concat(ELS.map((_, i) => 'shadow_' + i + '.png'));
  const tex = await Promise.all(names.map(f => load('/data/' + f)));
  const [col, nrm, shd, ice] = tex, shk = tex.slice(4);
  const sun = new THREE.Vector3(...meta.sun).normalize();
  const og = { value: 1 / 2.2 };
  // a moving Sun: the two baked elevations either side of the current one, and how far between them
  const U = { col: { value: col }, nrm: { value: nrm }, shd: { value: shd }, ice: { value: ice }, sun: { value: sun }, ex: { value: EX },
    shA: { value: shk[0] || shd }, shB: { value: shk[0] || shd }, shK: { value: 0 }, moving: { value: ELS.length ? 1 : 0 },
    iceK: { value: ${shot.ice || 0} }, expo: { value: ${shot.expo || 1} }, og };
  const mat = new THREE.ShaderMaterial({ uniforms: U,
    vertexShader: 'varying vec2 vUv; varying vec3 vW; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform sampler2D col, nrm, shd, ice, shA, shB; uniform vec3 sun; uniform float ex, shK, moving, iceK, expo, og;
      varying vec2 vUv; varying vec3 vW;
      void main() {
        vec3 c = pow(texture2D(col, vUv).rgb, vec3(2.2));
        vec3 t = texture2D(nrm, vUv).rgb * 2.0 - 1.0;                     // x east, y north, z up
        vec3 n = normalize(vec3(t.x * ex, t.z, -t.y * ex));
        // the regolith throws light back toward the Sun (as on the Moon): Lambert mixed with Lommel-Seeliger
        float mu0 = max(dot(n, sun), 0.0);
        vec3 v = normalize(cameraPosition - vW);
        float mu = max(dot(n, v), 0.05);
        float lit = mix(mu0, 2.0 * mu0 / (mu0 + mu), 0.4);
        float s = moving > 0.5 ? mix(texture2D(shA, vUv).r, texture2D(shB, vUv).r, shK) : texture2D(shd, vUv).r;
        // a soft terminator where the Sun grazes the slope (the disc is 1.4° wide, so the edge isn't a knife)
        s *= smoothstep(-0.012, 0.02, dot(n, sun));
        vec3 colr = c * (vec3(1.0, 0.985, 0.96) * 2.6 * expo * lit * s + vec3(0.006, 0.0065, 0.008));
        // ice in the permanent shadows: a faint cold glow (the radar-bright deposits)
        float ik = texture2D(ice, vUv).r * iceK * (1.0 - s);
        colr += vec3(0.30, 0.55, 0.85) * ik * 0.16;
        vec2 e2 = min(vUv, 1.0 - vUv);
        colr *= smoothstep(0.0, 0.16, min(e2.x, e2.y));
        gl_FragColor = vec4(pow(colr, vec3(og)), 1.0);
      }\`,
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(geo, mat));
  // faint stars (an exposure for the sunlit ground hardly shows them)
  const sg = new THREE.BufferGeometry(), sp = [], sc = [];
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 2200; i++) {
    const u = rnd() * 2 - 1, a = rnd() * Math.PI * 2, r = Math.sqrt(1 - u * u), b = 0.12 + 0.45 * Math.pow(rnd(), 3);
    sp.push(r * Math.cos(a) * 9000, u * 9000, r * Math.sin(a) * 9000); sc.push(b, b, b * 1.05);
  }
  sg.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.Float32BufferAttribute(sc, 3));
  const stars = new THREE.Points(sg, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);
  // the Sun's disc, on a big sphere round the camera, drawn behind the ground (the ground hides it when it is low)
  const sunSky = new THREE.Mesh(new THREE.SphereGeometry(9500, 64, 32), new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false,
    transparent: true, blending: THREE.AdditiveBlending, uniforms: { sun: { value: sun }, rad: { value: ${shot.sunRad || 0.7} * Math.PI / 180 }, og },
    vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: \`uniform vec3 sun; uniform float rad, og; varying vec3 vD;
      void main() {
        float a = acos(clamp(dot(normalize(vD), sun), -1.0, 1.0));
        float disc = 1.0 - smoothstep(rad * 0.97, rad * 1.03, a);
        float limb = mix(0.82, 1.0, sqrt(max(0.0, 1.0 - (a / rad) * (a / rad))));     // limb darkening
        float glow = exp(-(a - rad) / (rad * 0.35)) * 0.35 * step(rad, a) + exp(-(a - rad) / (rad * 2.0)) * 0.012 * step(rad, a);
        vec3 c = vec3(1.0, 0.99, 0.96) * (disc * limb * 6.0 + glow);
        gl_FragColor = vec4(pow(c, vec3(og)), 1.0);
      }\` }));
  scene.add(sunSky);
  const MARK = ${JSON.stringify(shot.marker || null)};
  if (MARK) {
    const gi = Math.round(MARK[0] / dx + (N - 1) / 2), gj = Math.round(MARK[1] / dy + (N - 1) / 2);
    const y = hb[gj * N + gi] / 1000 * EX - (MARK[0] * MARK[0] + MARK[1] * MARK[1]) / (2 * R);
    const pg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y + 0.05, MARK[1])]);
    const cv = document.createElement('canvas'); cv.width = cv.height = 64;
    const gx = cv.getContext('2d'), gr = gx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,250,235,1)'); gr.addColorStop(0.18, 'rgba(255,214,130,1)'); gr.addColorStop(0.45, 'rgba(255,190,90,0.35)'); gr.addColorStop(1, 'rgba(255,190,90,0)');
    gx.fillStyle = gr; gx.fillRect(0, 0, 64, 64);
    scene.add(new THREE.Points(pg, new THREE.PointsMaterial({ size: 26, sizeAttenuation: false, map: new THREE.CanvasTexture(cv), transparent: true, depthTest: false, depthWrite: false })));
    const lg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(MARK[0], y, MARK[1]), new THREE.Vector3(MARK[0], y + (${shot.markerH || 6}), MARK[1])]);
    scene.add(new THREE.Line(lg, new THREE.LineBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.8, depthTest: false })));
  }
  // setSun(el): the moving Sun at this elevation (degrees), its azimuth the site's
  const setSun = el => {
    const a = meta.az * Math.PI / 180, e = el * Math.PI / 180;
    sun.set(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)).normalize();
    if (!ELS.length) return;
    let i = 0; while (i < ELS.length - 2 && el > ELS[i + 1]) i++;
    U.shA.value = shk[i]; U.shB.value = shk[i + 1];
    U.shK.value = Math.min(1, Math.max(0, (el - ELS[i]) / (ELS[i + 1] - ELS[i])));
  };
  return { scene, stars, sunSky, sun, setSun, og, U };
}`;
