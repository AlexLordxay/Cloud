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
  const [color, relief, sea, clouds, pcol, prel] = await Promise.all(['color.jpg', 'relief.png', 'sea.png', 'clouds.jpg',
    'patch_color.jpg', 'patch_rel.png'].map(f => load('/maps/' + f)));
  for (const t of [color, relief, clouds]) { t.wrapS = T.RepeatWrapping; t.minFilter = T.LinearMipmapLinearFilter; }
  // the impact region in detail (patch.py): its box in latitude and longitude (radians), the same as there
  const PBOX = [13.0, 37.0, -88.0, -56.0].map(v => v * D);

  const VS = 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }';
  const U = { color: { value: color }, relief: { value: relief }, sea: { value: sea }, clouds: { value: clouds },
    sun: { value: new T.Vector3(1, 0, 0) }, C: { value: new T.Vector3() }, R: { value: ER },
    bump: { value: 7.0 }, cloudLon: { value: 0 }, exposure: { value: 1.0 }, dim: { value: 0 },
    fball: { value: new T.Vector4(0, 0, 0, 0) }, haze: { value: 1 }, atm: { value: 1.2 },
    pcol: { value: pcol }, prel: { value: prel }, pbox: { value: new T.Vector4(...PBOX) },
    shock: { value: new T.Vector4(1, 0, 0, 0) }, shock2: { value: new T.Vector4(0, 0, 0, 0) } };
  const earth = new T.Mesh(new T.SphereGeometry(ER, 768, 384), new T.ShaderMaterial({ uniforms: U, vertexShader: VS, extensions: { derivatives: true },
    fragmentShader: `uniform sampler2D color, relief, sea, clouds, pcol, prel; uniform vec4 pbox; uniform vec3 sun, C; uniform float R, bump, cloudLon, exposure, dim;
      uniform vec4 fball, shock, shock2; uniform float haze, atm;
      varying vec3 vW;
      float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float vn(vec3 p) {
        vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z) * 2.0 - 1.0;
      }
      // the air (Rayleigh): extinction per unit (1000 km) at sea level for red, green, blue; scale height 8 km;
      // the air mass along a slant (Kasten–Young), so the Sun near the horizon shines through much more air
      const vec3 BETA = vec3(5.8, 13.5, 33.1); const float HS = 0.008;
      // ozone (Chappuis band) takes the green-orange out of long slanting light, so twilight goes pink-violet, not olive
      const vec3 OZ = vec3(0.65, 1.881, 0.085) * 0.015;
      float airmass(float mu) { float z = degrees(acos(clamp(mu, -1.0, 1.0))); return 1.0 / max(mu + 0.15 * pow(max(93.885 - z, 0.4), -1.253), 0.026); }
      vec3 sunT(float h, float mu) { return exp(-(BETA * HS * exp(-h / HS) + OZ) * airmass(mu)); }
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
        vec3 c = pow(texture2D(color, uv).rgb, vec3(2.2));
        float w = texture2D(sea, uv).r;
        // inside the impact region the detailed maps take over, fading in from the box's edges
        vec2 pu = vec2((atan(-n.z, n.x) - pbox.z) / (pbox.w - pbox.z), (asin(clamp(n.y, -1.0, 1.0)) - pbox.x) / (pbox.y - pbox.x));
        float pw = smoothstep(0.0, 0.07, min(min(pu.x, 1.0 - pu.x), min(pu.y, 1.0 - pu.y)));
        if (pw > 0.0) {
          vec3 pr = texture2D(prel, pu).rgb;
          s = mix(s, (pr.rg * 255.0 - 128.0) / 635.0, pw);
          c = mix(c, pow(texture2D(pcol, pu).rgb, vec3(2.2)), pw);
          w = mix(w, pr.b, pw);
        }
        vec3 nb = normalize(n - bump * (s.x * E + s.y * N));
        float mu = dot(n, sun), day = smoothstep(-0.12, 0.08, mu);
        // finer than the map: fields, woods and gullies at 1–30 km, fading out where they would only shimmer
        float px = length(fwidth(vW)) / R;
        float k1 = 1.0 - smoothstep(0.0006, 0.002, px), k2 = 1.0 - smoothstep(0.00015, 0.0006, px);
        c *= 1.0 + (1.0 - w) * (0.22 * fb(n * 260.0) * k1 + 0.14 * fb(n * 2100.0) * k2);
        float lit = max(dot(nb, sun), 0.0) * smoothstep(-0.05, 0.12, mu) + 0.0;
        // sunlight at the ground, reddened by the air it came through (orange near the terminator)
        vec3 sunG = sunT(0.0, mu) * smoothstep(-0.03, 0.04, mu);
        vec3 col = c * lit * 2.6 * sunG;
        // clouds (drifting by cloudLon) and their shadows, cast away from the Sun from ~10 km up
        float cl = texture2D(clouds, uvOf(n, cloudLon)).r;
        // close up the map's 5 km cells would blur: its edges are frayed by finer noise, and the fraying fades out far off
        float ce = (fb(n * 1400.0 + 7.0) * 0.7 + fb(n * 5200.0) * 0.3) * k1;
        cl = clamp(cl + ce * 0.9 * cl * (1.0 - cl) * 4.0 - 0.06 * k1 * (1.0 - cl), 0.0, 1.0);
        // the blast (shock: its centre and radius as an angle; shock2: ring brightness, crater radius, crater glow, dust):
        // inside the ring the clouds are swept away and a pall of dust lies over everything
        float ang = length(n - shock.xyz), inside = 0.0, ring = 0.0;
        if (shock.w > 0.0) {
          inside = 1.0 - smoothstep(shock.w * 0.8, shock.w, ang);
          float wob = fb(n * 700.0 + 11.0) * 0.12 * shock.w;                        // a ragged front, not a drawn circle
          ring = exp(-pow((ang + wob - shock.w) / (shock.w * 0.06 + 0.0006), 2.0));
          cl *= 1.0 - 0.9 * inside;
        }
        vec3 ns = normalize(n + sun * 0.0018 / max(mu, 0.15));
        float sh = texture2D(clouds, uvOf(ns, cloudLon)).r;
        col *= 1.0 - 0.55 * sh;
        // the water's glint: a sharp sun and a broad sheen
        vec3 Hh = normalize(sun + V);
        float g = pow(max(dot(n, Hh), 0.0), 600.0) * 0.45 + pow(max(dot(n, Hh), 0.0), 40.0) * 0.035;
        col += vec3(1.0, 0.93, 0.80) * g * w * (1.0 - cl) * day;
        float cmu = max(mu, 0.0);
        vec3 cloudCol = vec3(1.0, 0.99, 0.97) * (pow(cmu, 0.8) * 2.4) * sunT(0.01, mu + 0.03) * smoothstep(-0.05, 0.03, mu);
        col = mix(col, cloudCol, cl * 0.92);
        // the air between us and the ground: it dims what is below and adds its own sunlit blue (all of it near the
        // horizon, where we look through the most air); the light it scatters is the Sun's, reddened like the ground's
        vec3 Tv = exp(-BETA * HS * airmass(max(dot(n, V), 0.0)) * haze);
        float cs = dot(-V, sun), ph = 0.75 * (1.0 + cs * cs) + 0.5 * pow(max(cs, 0.0), 8.0);
        vec3 sunA = sunT(0.008, mu + 0.02) * smoothstep(-0.03, 0.05, mu) * mix(0.45, 1.0, smoothstep(0.0, 0.3, mu));
        col = col * Tv + (1.0 - Tv) * sunA * ph * atm * 0.75;
        if (shock.w > 0.0) {
          float dn = fb(n * 900.0 + 3.0) * 0.5 + 0.5;
          col = mix(col, vec3(0.16, 0.12, 0.09) * (0.15 + 0.85 * max(mu, 0.0)) * (0.7 + 0.6 * dn), inside * shock2.w);
          col += ring * shock2.x * vec3(1.0, 0.92, 0.82) * (0.3 + 1.4 * dn * dn);
        }
        // the crater floor: molten rock, glowing
        if (shock2.y > 0.0) {
          float cr = 1.0 - smoothstep(shock2.y * 0.7, shock2.y, ang);
          float lava = fb(n * 2600.0) * 0.5 + 0.5;
          col += cr * shock2.z * mix(vec3(0.6, 0.08, 0.01), vec3(1.0, 0.55, 0.15), lava);
        }
        col *= 1.0 - dim;
        // the fireball's own light (fb: where, how strong): warm, falling off with distance, on whatever faces it
        if (fball.w > 0.0) {
          vec3 L = fball.xyz - vW; float dl = length(L);
          float f = fball.w * max(dot(n, L / dl), 0.0) / (1.0 + dl * dl / 0.006);
          col += vec3(1.0, 0.62, 0.30) * f * mix(c * 3.0 + 0.02, vec3(0.9), cl);
        }
        col = vec3(1.0) - exp(-col * exposure);                                 // soft shoulder: bright clouds don't clip
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  // the atmosphere edge-on: the air along each line of sight that misses the Earth, by the same Rayleigh numbers —
  // the column through the tangent point, how much of it the Sun lights (none in the Earth's shadow, red light near
  // it), forward-scattering a little brighter toward the Sun. White-blue close to the limb, blue higher, then black;
  // at dusk a red-orange layer on the horizon. A hair of glow is let inside the limb, over the mesh's facet gaps.
  const halo = new T.Mesh(new T.SphereGeometry(ER * 1.035, 256, 128), new T.ShaderMaterial({ uniforms: U, vertexShader: VS,
    transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.FrontSide,
    fragmentShader: `uniform vec3 sun, C; uniform float R, dim, atm; varying vec3 vW;
      // the air (Rayleigh): extinction per unit (1000 km) at sea level for red, green, blue; scale height 8 km;
      // the air mass along a slant (Kasten–Young), so the Sun near the horizon shines through much more air
      const vec3 BETA = vec3(5.8, 13.5, 33.1); const float HS = 0.008;
      // ozone (Chappuis band) takes the green-orange out of long slanting light, so twilight goes pink-violet, not olive
      const vec3 OZ = vec3(0.65, 1.881, 0.085) * 0.015;
      float airmass(float mu) { float z = degrees(acos(clamp(mu, -1.0, 1.0))); return 1.0 / max(mu + 0.15 * pow(max(93.885 - z, 0.4), -1.253), 0.026); }
      vec3 sunT(float h, float mu) { return exp(-(BETA * HS * exp(-h / HS) + OZ) * airmass(mu)); }
      void main() {
        vec3 d = normalize(vW - cameraPosition), oc = C - cameraPosition;
        vec3 near = cameraPosition + d * dot(oc, d);
        float b = length(near - C);
        if (b < R - 0.0004) discard;
        float h = max(b - R, 0.0);
        vec3 up = normalize(near - C);
        vec3 tauV = BETA * exp(-h / HS) * sqrt(6.2831853 * R * HS);
        float ms = dot(up, sun) + sqrt(2.0 * h / R);                       // > 0: the Sun is above this point's horizon
        vec3 lit = sunT(h, ms) * smoothstep(-0.02, 0.01, ms);
        float cs = dot(d, sun), ph = 0.75 * (1.0 + cs * cs) + 0.5 * pow(max(cs, 0.0), 8.0);
        vec3 L = (1.0 - exp(-tauV)) * lit * ph * atm;
        gl_FragColor = vec4(L * (1.0 - dim), 1.0);
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
  const AU = { sun: U.sun, exposure: { value: 1.0 }, M3: { value: new T.Matrix3() }, heat: { value: 0 }, fwd: { value: new T.Vector3(1, 0, 0) } };
  // boulders in the shader, too small for the mesh: two sizes of domes strewn on a 3-D grid (one per cell, some cells
  // empty), each tilting the surface; the regolith darker round their feet, the boulders themselves a little varied
  const asteroid = new T.Mesh(ag, new T.ShaderMaterial({ uniforms: AU, vertexColors: true, extensions: { derivatives: true },
    vertexShader: `varying vec3 vN, vP, vW, vC; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz;
      vN = normal; vP = position; vC = color; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 sun, fwd; uniform float exposure, heat; uniform mat3 M3; varying vec3 vN, vP, vW, vC;
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
        float pxa = length(fwidth(vP));                                         // object units per pixel
        vec3 g = g1 * 0.9 * (1.0 - smoothstep(0.006, 0.02, pxa)) + g2 * 0.7 * (1.0 - step(0.001, b1.x)) * (1.0 - smoothstep(0.002, 0.007, pxa));
        n = normalize(n - 0.85 * (g - n * dot(g, n)));          // domes: the surface tilts away from each centre
        n = normalize(M3 * n);
        vec3 V = normalize(cameraPosition - vW);
        float mu0 = max(dot(n, sun), 0.0), mu = max(dot(n, V), 0.0);
        float alb = 1.0 + 0.25 * (b1.z - 0.5) * step(0.001, b1.x) - 0.35 * b1.y * (1.0 - step(0.001, b1.x)) - 0.2 * b2.y;
        // dark dust: Lommel–Seeliger mixed with a little Lambert, so the relief reads but the limb does not go black
        float ls = mu0 / (mu0 + mu + 1e-4) * 2.0, lam = mu0;
        vec3 col = vC * alb * (0.55 * ls + 0.45 * lam) * 2.4 * exposure;
        col += vC * 0.03;                                                      // a whisper of earthshine
        // in the air: the face it drives into glows white-hot, the sides orange
        float f = max(dot(n, fwd), 0.0);
        col += heat * (vec3(1.0, 0.85, 0.6) * pow(f, 2.0) * 3.0 + vec3(1.0, 0.4, 0.1) * f * 0.8);
        col = vec3(1.0) - exp(-col);
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  asteroid.visible = false; scene.add(asteroid);

  // ---- fire and smoke ---------------------------------------------------------------------------------------------
  // Particles laid out in advance, each with its birth time, so that any frame can be drawn on its own: born at p0 with
  // velocity vel, slowed by drag (the air) and pulled by grav, growing from size s0 to s1 (world units) over its life.
  // Glow is added: hot white, then yellow, orange, deep red as it cools (heat sets how fast). Smoke is laid over: dark,
  // brownish, lit a little on the Sun's side.
  const MAXPT = renderer.getContext().getParameter(renderer.getContext().ALIASED_POINT_SIZE_RANGE)[1];
  const FXV = `attribute vec3 vel; attribute float tb, life, s0, s1, seed;
    uniform float time, scale, drag, maxPt; uniform vec3 grav;
    varying float vA, vSeed, vH;
    void main() {
      float age = time - tb, a = age / life;
      if (age < 0.0 || a > 1.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
      vec3 p = position + vel * (1.0 - exp(-drag * age)) / drag + 0.5 * grav * age * age;
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_PointSize = clamp(mix(s0, s1, sqrt(a)) * scale / max(-mv.z, 1e-5), 1.0, maxPt);
      gl_Position = projectionMatrix * mv; vA = a; vSeed = seed; vH = length(p) - 6.371;
    }`;
  function fx(n, glow) {
    const g = new T.BufferGeometry(), A = {};
    for (const [k, m] of [['position', 3], ['vel', 3], ['tb', 1], ['life', 1], ['s0', 1], ['s1', 1], ['seed', 1]])
      g.setAttribute(k, A[k] = new T.BufferAttribute(new Float32Array(n * m), m));
    const u = { time: { value: 0 }, scale: { value: 1 }, drag: { value: 1 }, maxPt: { value: MAXPT }, grav: { value: new T.Vector3() },
      heat: { value: 3 }, gain: { value: 1 }, sun: U.sun, smoke: { value: new T.Color(0.13, 0.11, 0.10) },
      litH: { value: new T.Vector2(-1, -1) }, litCol: { value: new T.Color(1.0, 0.62, 0.42) } };
    const m = new T.ShaderMaterial({ uniforms: u, vertexShader: FXV, transparent: true, depthWrite: false,
      blending: glow ? T.AdditiveBlending : T.NormalBlending,
      fragmentShader: glow ? `uniform float heat, gain; varying float vA, vSeed, vH;
        float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
        void main() {
          vec2 q = gl_PointCoord - 0.5;
          float puff = 0.6 * n2(q * 5.0 + vSeed * 37.0) + 0.4 * n2(q * 11.0 - vSeed * 53.0);
          float r = length(q) * 2.0 * (0.75 + 0.5 * puff); if (r > 1.0) discard;
          float T = exp(-vA * heat) * (0.75 + 0.25 * vSeed);
          vec3 c = mix(vec3(0.55, 0.06, 0.01), vec3(1.0, 0.42, 0.08), smoothstep(0.08, 0.35, T));
          c = mix(c, vec3(1.0, 0.80, 0.42), smoothstep(0.35, 0.65, T)); c = mix(c, vec3(1.0, 0.97, 0.90), smoothstep(0.65, 0.95, T));
          float k = exp(-r * r * 3.0) * (1.0 - smoothstep(0.7, 1.0, vA)) * (0.25 + 1.6 * T * T);
          gl_FragColor = vec4(c * k * gain, 1.0);
        }` : `uniform float gain; uniform vec3 smoke, litCol; uniform vec2 litH; varying float vA, vSeed, vH;
        float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
        void main() {
          vec2 d = gl_PointCoord - 0.5;
          float puff = 0.6 * n2(d * 4.0 + vSeed * 41.0) + 0.4 * n2(d * 9.0 - vSeed * 17.0);
          float r = length(d) * 2.0 * (0.7 + 0.6 * puff); if (r > 1.0) discard;
          float a = exp(-r * r * 2.5) * smoothstep(0.0, 0.08, vA) * (1.0 - smoothstep(0.55, 1.0, vA)) * 0.12 * gain;
          vec3 c = smoke * (0.8 + 0.4 * vSeed) * (0.85 + 0.3 * d.x);
          // high enough, smoke still catches the Sun that has set on the ground below (litH: from, to — in units)
          if (litH.y > 0.0) c = mix(c * 0.55, litCol * (0.8 + 0.4 * vSeed) * (0.8 + 0.4 * d.x), smoothstep(litH.x, litH.y, vH));
          gl_FragColor = vec4(c, a);
        }` });
    const p = new T.Points(g, m); p.frustumCulled = false; p.visible = false; p.renderOrder = glow ? 3 : 2; scene.add(p);
    return { points: p, u, A, n,
      set(i, pos, vel, tb, life, s0, s1, seed) {
        A.position.setXYZ(i, pos.x, pos.y, pos.z); A.vel.setXYZ(i, vel.x, vel.y, vel.z);
        A.tb.setX(i, tb); A.life.setX(i, life); A.s0.setX(i, s0); A.s1.setX(i, s1); A.seed.setX(i, seed);
      },
      done() { for (const a of Object.values(A)) a.needsUpdate = true; } };
  }
  // the head of the fireball: soft round glows (canvas gradients) that stay a fixed size in the world
  function glowTex(stops) {
    const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    for (const [o, col] of stops) gr.addColorStop(o, col);
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new T.CanvasTexture(c);
  }
  function glow(stops) {
    const s = new T.Sprite(new T.SpriteMaterial({ map: glowTex(stops), blending: T.AdditiveBlending, transparent: true, depthWrite: false, depthTest: false }));
    s.visible = false; s.renderOrder = 4; scene.add(s); return s;
  }
  // the blast seen in the air: a thin ragged dome, brightest where we look along its edge (where it is thickest)
  const dome = new T.Mesh(new T.SphereGeometry(1, 128, 64, 0, Math.PI * 2, 0, Math.PI / 2), new T.ShaderMaterial({
    uniforms: { k: { value: 0 }, col: { value: new T.Color(1.0, 0.85, 0.7) } }, transparent: true, depthWrite: false,
    blending: T.AdditiveBlending, side: T.DoubleSide,
    vertexShader: `varying vec3 vN, vW, vP; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vP = position;
      vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform float k; uniform vec3 col; varying vec3 vN, vW, vP;
      float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float vn(vec3 p) { vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z); }
      void main() {
        float e = 1.0 - abs(dot(normalize(vN), normalize(cameraPosition - vW)));
        float nz = 0.55 * vn(vP * 9.0) + 0.3 * vn(vP * 23.0) + 0.15 * vn(vP * 61.0);
        float a = pow(e, 5.0) * (0.15 + 1.6 * nz * nz * nz) * smoothstep(0.0, 0.25, vP.y);
        gl_FragColor = vec4(col * a * k, 1.0);
      }` }));
  dome.visible = false; dome.renderOrder = 1; scene.add(dome);
  const head = {
    core: glow([[0, 'rgba(255,255,250,1)'], [0.25, 'rgba(255,240,200,0.9)'], [0.6, 'rgba(255,170,80,0.25)'], [1, 'rgba(255,120,40,0)']]),
    halo: glow([[0, 'rgba(255,200,120,0.55)'], [0.3, 'rgba(255,140,50,0.22)'], [0.7, 'rgba(200,70,20,0.06)'], [1, 'rgba(120,30,10,0)']]),
  };

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

  window.X = { T, D, W, H, ER, renderer, scene, camera, earth, halo, U, asteroid, AU, stars, dirLL, fx, head, rnd, dome };
  window.WORLD_READY = 1;

  window.startShot = async (name) => {
    const s = window.SHOTS[name]; earth.visible = halo.visible = true; asteroid.visible = false; stars.visible = true;
    U.dim.value = 0; U.exposure.value = 1; AU.exposure.value = 1; AU.heat.value = 0; U.fball.value.set(0, 0, 0, 0); U.haze.value = 1; U.atm.value = 1.2; U.shock.value.set(1, 0, 0, 0); U.shock2.value.set(0, 0, 0, 0);
    head.core.visible = head.halo.visible = false;
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
