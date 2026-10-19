// The world of "Що сталося з Землею, коли вимерли динозаври" (runs in the page; render.js serves it). Units: 1 = 1000 km.
//   the Earth 66 million years ago (maps.py): its lands and seas lit by the Sun with their relief, clouds that cast
//     shadows, the glint on the water, a blue haze thickening to the rim and a thin glowing atmosphere round the edge,
//     the dusk turning orange at the terminator; no lights on the night side — nobody to switch them on
//   the asteroid: about 10 km, dark (a carbonaceous body from beyond Jupiter, as the ruthenium in the boundary clay
//     says, Fischer-Gödde et al. 2024), an elongated rubble lump covered with craters, its surface lit as dark dust is
//   stars
// The Earth stays fixed (its axis up, y); shots place the camera and the Sun.
(async () => {
  const T = THREE, D = Math.PI / 180, W = 720, H = 1280, ER = 6.371;
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.getContext().getExtension('OES_standard_derivatives');
  renderer.setSize(W, H); renderer.setPixelRatio(1); document.body.appendChild(renderer.domElement);
  const scene = new T.Scene(), camera = new T.PerspectiveCamera(30, W / H, 0.01, 3000);
  const dirLL = (lat, lon) => new T.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
  const load = url => new Promise((res, rej) => new T.TextureLoader().load(url, t => { t.anisotropy = 8; res(t); }, undefined, rej));
  const [color, relief, sea, clouds] = await Promise.all(['color.jpg', 'relief.png', 'sea.png', 'clouds.png'].map(f => load('/maps/' + f)));
  for (const t of [color, relief, clouds]) { t.wrapS = T.RepeatWrapping; t.minFilter = T.LinearMipmapLinearFilter; }

  const VS = 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }';
  const U = { color: { value: color }, relief: { value: relief }, sea: { value: sea }, clouds: { value: clouds },
    sun: { value: new T.Vector3(1, 0, 0) }, C: { value: new T.Vector3() }, R: { value: ER },
    bump: { value: 7.0 }, cloudLon: { value: 0 }, exposure: { value: 1.0 }, dim: { value: 0 } };
  const earth = new T.Mesh(new T.SphereGeometry(ER, 256, 128), new T.ShaderMaterial({ uniforms: U, vertexShader: VS, extensions: { derivatives: true },
    fragmentShader: `uniform sampler2D color, relief, sea, clouds; uniform vec3 sun, C; uniform float R, bump, cloudLon, exposure, dim;
      varying vec3 vW;
      float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float vn(vec3 p) {
        vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z) * 2.0 - 1.0;
      }
      float fb(vec3 p) { return 0.5 * vn(p) + 0.27 * vn(p * 2.03) + 0.15 * vn(p * 4.1) + 0.08 * vn(p * 8.3); }
      vec2 uvOf(vec3 n, float lonOff) {
        float lat = asin(clamp(n.y, -1.0, 1.0)), lon = atan(-n.z, n.x) + lonOff;
        return vec2(fract((lon + 3.14159265) / 6.2831853), (lat + 1.5707963) / 3.14159265);
      }
      void main() {
        vec3 n = normalize(vW - C), V = normalize(cameraPosition - vW);
        vec2 uv = uvOf(n, 0.0);
        // relief: the land's slopes tilt the normal (east and north at this point)
        vec3 E = normalize(vec3(n.z, 0.0, -n.x) + 1e-6), N = normalize(vec3(-n.y * n.x, 1.0 - n.y * n.y, -n.y * n.z) + 1e-6);
        vec2 s = (texture2D(relief, uv).rg * 255.0 - 128.0) / 635.0;
        vec3 nb = normalize(n - bump * (s.x * E + s.y * N));
        float mu = dot(n, sun), day = smoothstep(-0.12, 0.08, mu);
        vec3 c = pow(texture2D(color, uv).rgb, vec3(2.2));
        float w = texture2D(sea, uv).r;
        // finer than the map: fields, woods and gullies at 1–30 km, fading out where they would only shimmer
        float px = length(fwidth(vW)) / R;
        float k1 = 1.0 - smoothstep(0.0006, 0.002, px), k2 = 1.0 - smoothstep(0.00015, 0.0006, px);
        c *= 1.0 + (1.0 - w) * (0.22 * fb(n * 260.0) * k1 + 0.14 * fb(n * 2100.0) * k2);
        float lit = max(dot(nb, sun), 0.0) * smoothstep(-0.05, 0.12, mu) + 0.0;
        vec3 col = c * lit * 2.6;
        // clouds (drifting by cloudLon) and their shadows, cast away from the Sun from ~10 km up
        float cl = texture2D(clouds, uvOf(n, cloudLon)).r;
        vec3 ns = normalize(n + sun * 0.0018 / max(mu, 0.15));
        float sh = texture2D(clouds, uvOf(ns, cloudLon)).r;
        col *= 1.0 - 0.55 * sh;
        // the water's glint: a sharp sun and a broad sheen
        vec3 Hh = normalize(sun + V);
        float g = pow(max(dot(n, Hh), 0.0), 420.0) * 1.3 + pow(max(dot(n, Hh), 0.0), 30.0) * 0.05;
        col += vec3(1.0, 0.93, 0.80) * g * w * (1.0 - cl) * day;
        float cmu = max(mu, 0.0);
        vec3 cloudCol = vec3(1.0, 0.99, 0.97) * (pow(cmu, 0.8) * 2.4) * mix(vec3(1.0, 0.55, 0.30), vec3(1.0), smoothstep(0.0, 0.25, mu));
        col = mix(col, cloudCol, cl * 0.92);
        // the air: blue haze thickening toward the rim, orange where the light grazes
        float rim = pow(1.0 - max(dot(n, V), 0.0), 2.2);
        vec3 sky = mix(vec3(0.9, 0.42, 0.15), vec3(0.28, 0.50, 1.0), smoothstep(0.0, 0.22, mu));
        col = mix(col, sky * smoothstep(-0.06, 0.35, mu) * 1.2, clamp(0.06 + 0.7 * rim, 0.0, 1.0) * smoothstep(-0.1, 0.05, mu));
        col *= 1.0 - dim;
        col = vec3(1.0) - exp(-col * exposure);                                 // soft shoulder: bright clouds don't clip
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  // the atmosphere edge-on: a thin glow just outside the limb on the lit side, orange toward the terminator
  const halo = new T.Mesh(new T.SphereGeometry(ER * 1.035, 128, 64), new T.ShaderMaterial({ uniforms: U, vertexShader: VS,
    transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.FrontSide,
    fragmentShader: `uniform vec3 sun, C; uniform float R, dim; varying vec3 vW;
      void main() {
        vec3 d = normalize(vW - cameraPosition), oc = C - cameraPosition;
        vec3 near = cameraPosition + d * dot(oc, d);
        float b = length(near - C) / R;
        if (b < 1.0) discard;
        float mu = dot(normalize(near - C), sun);
        float gl = exp(-(b - 1.0) / 0.006) * smoothstep(-0.3, 0.2, mu);
        vec3 c = mix(vec3(1.0, 0.45, 0.15), vec3(0.35, 0.6, 1.0), smoothstep(-0.05, 0.35, mu));
        gl_FragColor = vec4(c * gl * 1.1 * (1.0 - dim), 1.0);
      }` }));
  scene.add(earth, halo);

  // ---- the asteroid: an elongated lump, its shape a sum of broad lumps and craters of all sizes -------------------
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const hash = (x, y, z) => { const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return s - Math.floor(s); };
  function vnoise(x, y, z) {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = x - xi, yf = y - yi, zf = z - zi;
    const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf), w = zf * zf * (3 - 2 * zf);
    const L = (a, b, k) => a + (b - a) * k;
    return L(L(L(hash(xi, yi, zi), hash(xi + 1, yi, zi), u), L(hash(xi, yi + 1, zi), hash(xi + 1, yi + 1, zi), u), v),
             L(L(hash(xi, yi, zi + 1), hash(xi + 1, yi, zi + 1), u), L(hash(xi, yi + 1, zi + 1), hash(xi + 1, yi + 1, zi + 1), u), v), w) * 2 - 1;
  }
  const fbm = (x, y, z, o, g = 0.5) => { let s = 0, a = 1, n = 0, f = 1; for (let i = 0; i < o; i++) { s += a * vnoise(x * f, y * f, z * f); n += a; a *= g; f *= 2.03; } return s / n; };
  const craters = [];
  for (let i = 0; i < 420; i++) {
    const z = rnd() * 2 - 1, p = rnd() * Math.PI * 2, r = Math.sqrt(1 - z * z);
    const rad = 0.035 * Math.pow(rnd(), -0.55); if (rad > 0.45) continue;
    craters.push({ c: new T.Vector3(r * Math.cos(p), z, r * Math.sin(p)), rad, depth: rad * (0.22 + 0.12 * rnd()), fresh: rnd() });
  }
  const AX = [1.0, 0.80, 0.70];
  function radius(d) {
    let r = 1 / Math.sqrt((d.x / AX[0]) ** 2 + (d.y / AX[1]) ** 2 + (d.z / AX[2]) ** 2);
    r *= 1 + 0.24 * fbm(d.x * 1.1 + 3, d.y * 1.1, d.z * 1.1, 3) + 0.035 * fbm(d.x * 5, d.y * 5, d.z * 5 + 9, 4);
    for (const k of craters) {
      const th = Math.acos(Math.min(1, d.dot(k.c))), x = th / k.rad;
      if (x > 1.6) continue;
      r += x < 1 ? k.depth * (x * x - 1) * 0.9 + k.depth * 0.18 : k.depth * 0.18 * Math.exp(-(((x - 1) / 0.22) ** 2));
    }
    // boulders and rubble
    r += 0.006 * fbm(d.x * 40, d.y * 40, d.z * 40, 3) + 0.010 * Math.max(0, fbm(d.x * 22 + 5, d.y * 22, d.z * 22, 2) - 0.35);
    return r;
  }
  const ag = new T.SphereGeometry(1, 400, 200), pa = ag.attributes.position, na = ag.attributes.normal;
  const cols = new Float32Array(pa.count * 3), d = new T.Vector3(), t1 = new T.Vector3(), t2 = new T.Vector3();
  const P0 = new T.Vector3(), P1 = new T.Vector3(), P2 = new T.Vector3(), e = 0.004;
  for (let i = 0; i < pa.count; i++) {
    d.fromBufferAttribute(pa, i).normalize();
    t1.set(0, 1, 0).cross(d); if (t1.lengthSq() < 1e-6) t1.set(1, 0, 0).cross(d); t1.normalize(); t2.crossVectors(d, t1);
    P0.copy(d).multiplyScalar(radius(d));
    const d1 = d.clone().addScaledVector(t1, e).normalize(), d2 = d.clone().addScaledVector(t2, e).normalize();
    P1.copy(d1).multiplyScalar(radius(d1)); P2.copy(d2).multiplyScalar(radius(d2));
    const nrm = P1.sub(P0).cross(P2.sub(P0)).normalize(); if (nrm.dot(d) < 0) nrm.negate();
    pa.setXYZ(i, P0.x, P0.y, P0.z); na.setXYZ(i, nrm.x, nrm.y, nrm.z);
    // albedo: very dark, a little warmer and lighter in patches, fresh crater floors slightly brighter
    const a = 0.055 * (1 + 0.25 * fbm(d.x * 3 + 1, d.y * 3, d.z * 3, 4) + 0.15 * fbm(d.x * 30, d.y * 30, d.z * 30, 2));
    cols[i * 3] = a * 1.06; cols[i * 3 + 1] = a; cols[i * 3 + 2] = a * 0.92;
  }
  ag.setAttribute('color', new T.BufferAttribute(cols, 3));
  const AU = { sun: U.sun, exposure: { value: 1.0 }, M3: { value: new T.Matrix3() } };
  // boulders in the shader, too small for the mesh: two sizes of domes strewn on a 3-D grid (one per cell, some cells
  // empty), each tilting the surface; the regolith darker round their feet, the boulders themselves a little varied
  const asteroid = new T.Mesh(ag, new T.ShaderMaterial({ uniforms: AU, vertexColors: true,
    vertexShader: `varying vec3 vN, vP, vW, vC; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz;
      vN = normal; vP = position; vC = color; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 sun; uniform float exposure; uniform mat3 M3; varying vec3 vN, vP, vW, vC;
      vec3 h33(vec3 p) { return fract(sin(vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)))) * 43758.5453); }
      // the tallest dome over p at this scale: its height (cell units), gradient, how near its foot, and a tint
      vec4 boulders(vec3 p, float s, out vec3 grad) {
        vec3 q = p * s, i = floor(q); float best = 0.0, foot = 0.0, tint = 0.0; grad = vec3(0.0);
        for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++) {
          vec3 c = i + vec3(x, y, z), r = h33(c);
          if (r.z < 0.35) continue;
          vec3 ctr = c + 0.15 + 0.7 * r; float rad = 0.22 + 0.33 * fract(r.x * 7.13);
          vec3 d = q - ctr; float dd = dot(d, d);
          if (dd < rad * rad) {
            float hh = sqrt(rad * rad - dd);
            if (hh > best) { best = hh; grad = -d / max(hh, 0.08 * rad); tint = fract(r.y * 13.7); }
          } else foot = max(foot, 1.0 - smoothstep(rad, rad * 1.6, sqrt(dd)));
        }
        return vec4(best, foot, tint, 0.0);
      }
      void main() {
        vec3 n = normalize(vN), g1, g2;
        vec4 b1 = boulders(vP, 45.0, g1), b2 = boulders(vP, 150.0, g2);
        vec3 g = g1 * 0.9 + g2 * 0.7 * (1.0 - step(0.001, b1.x));
        n = normalize(n - 0.85 * (g - n * dot(g, n)));          // domes: the surface tilts away from each centre
        n = normalize(M3 * n);
        vec3 V = normalize(cameraPosition - vW);
        float mu0 = max(dot(n, sun), 0.0), mu = max(dot(n, V), 0.0);
        float alb = 1.0 + 0.25 * (b1.z - 0.5) * step(0.001, b1.x) - 0.35 * b1.y * (1.0 - step(0.001, b1.x)) - 0.2 * b2.y;
        // dark dust: Lommel–Seeliger mixed with a little Lambert, so the relief reads but the limb does not go black
        float ls = mu0 / (mu0 + mu + 1e-4) * 2.0, lam = mu0;
        vec3 col = vC * alb * (0.55 * ls + 0.45 * lam) * 2.4 * exposure;
        col += vC * 0.03;                                                      // a whisper of earthshine
        col = vec3(1.0) - exp(-col);
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  asteroid.visible = false; scene.add(asteroid);

  // ---- stars ----------------------------------------------------------------------------------------------------
  const sp = [], sc = [];
  for (let i = 0; i < 9000; i++) {
    const z = rnd() * 2 - 1, p = rnd() * Math.PI * 2, r = Math.sqrt(1 - z * z), m = Math.pow(rnd(), 3.5);
    sp.push(r * Math.cos(p) * 1500, z * 1500, r * Math.sin(p) * 1500);
    const t = rnd(), b = 0.25 + 0.75 * m; sc.push(b * (0.85 + 0.15 * t), b * 0.9, b * (1.05 - 0.2 * t));
  }
  const sg = new T.BufferGeometry(); sg.setAttribute('position', new T.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new T.Float32BufferAttribute(sc, 3));
  const stars = new T.Points(sg, new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false }));
  scene.add(stars);

  window.X = { T, D, W, H, ER, renderer, scene, camera, earth, halo, U, asteroid, AU, stars, dirLL };
  window.WORLD_READY = 1;

  window.startShot = async (name) => {
    const s = window.SHOTS[name]; earth.visible = halo.visible = true; asteroid.visible = false; stars.visible = true;
    U.dim.value = 0; U.exposure.value = 1; AU.exposure.value = 1;
    if (s.setup) await s.setup(window.X);
  };
  window.renderShot = (name, t) => {
    window.SHOTS[name].frame(window.X, t);
    stars.position.copy(camera.position);
    asteroid.updateMatrixWorld(); AU.M3.value.setFromMatrix4(asteroid.matrixWorld);
    renderer.render(scene, camera);
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
})();
