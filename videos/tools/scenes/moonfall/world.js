// The world of «Що, якби Місяць упав на Землю?» (runs in the page; render.js serves it). Units: 1 = 1000 km.
//   the Earth of today (maps.py): day map, city lights, clouds and the height of every place, so the sea can rise and
//     fall with the tide over the real ground; a thin glowing atmosphere (Rayleigh + ozone, as in the dinosaur video);
//     later the fires, the melt and the dust
//   the Moon: the site's map and relief, stretched by the tides as it nears, cracking, shedding a stream of rubble from
//     its near side, glowing where it ploughs into the air
//   the debris: thousands of rocks on their own falls (Earth's gravity, integrated in advance), meteors in the air
//   we are the astronaut: the camera is our eyes inside the helmet (its visor's rim is drawn over the frame, captions.py)
// The world is inertial: the Moon falls along a fixed line, the Sun is fixed, the Earth turns (shots set its angle).
(async () => {
  const T = THREE, D = Math.PI / 180, W = 720, H = 1280, ER = 6.371, RM = 1.7374;
  const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.getContext().getExtension('OES_standard_derivatives');
  renderer.setSize(W, H); renderer.setPixelRatio(1); renderer.autoClear = false;
  document.body.appendChild(renderer.domElement);
  const scene = new T.Scene(), camera = new T.PerspectiveCamera(90, W / H, 0.005, 3000);
  const dirLL = (lat, lon) => new T.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
  const load = url => new Promise((res, rej) => new T.TextureLoader().load(url, t => { t.anisotropy = 8; res(t); }, undefined, rej));
  const [color, night, clouds, hgt, moonTex, moonNrm] = await Promise.all(['/maps/color.jpg', '/maps/night.jpg', '/maps/clouds.jpg',
    '/maps/hgt.png', '/tex/moon.jpg', '/tex/moon_normal.jpg'].map(load));
  for (const t of [color, night, clouds, hgt, moonTex, moonNrm]) { t.wrapS = T.RepeatWrapping; t.minFilter = T.LinearMipmapLinearFilter; }

  const NOISE = `
    float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
    float vn(vec3 p) {
      vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                 mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z) * 2.0 - 1.0;
    }
    float fb(vec3 p) { return 0.5 * vn(p) + 0.27 * vn(p * 2.03) + 0.15 * vn(p * 4.1) + 0.08 * vn(p * 8.3); }`;
  const AIR = `
    // the air (Rayleigh): extinction per unit (1000 km) at sea level for red, green, blue; scale height 8 km; the air
    // mass along a slant (Kasten–Young); ozone (Chappuis band) so that twilight goes pink-violet
    const vec3 BETA = vec3(5.8, 13.5, 33.1); const float HS = 0.008;
    const vec3 OZ = vec3(0.65, 1.881, 0.085) * 0.015;
    float airmass(float mu) { float z = degrees(acos(clamp(mu, -1.0, 1.0))); return 1.0 / max(mu + 0.15 * pow(max(93.885 - z, 0.4), -1.253), 0.026); }
    vec3 sunT(float h, float mu) { return exp(-(BETA * HS * exp(-h / HS) + OZ) * airmass(mu)); }`;

  // ---- the Earth ----------------------------------------------------------------------------------------------------
  const VS = 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }';
  const U = { color: { value: color }, night: { value: night }, clouds: { value: clouds }, hgt: { value: hgt },
    sun: { value: new T.Vector3(1, 0, 0) }, C: { value: new T.Vector3() }, R: { value: ER }, toBody: { value: new T.Matrix3() },
    moonDir: { value: new T.Vector3(1, 0, 0) }, zeta: { value: 0 }, cloudLon: { value: 0 }, exposure: { value: 1.0 },
    haze: { value: 1 }, atm: { value: 1.2 }, lights: { value: 1 }, cloudK: { value: 1 },
    moonL: { value: new T.Vector4(1, 0, 0, 0) },        // moonlight on the night side: direction, strength
    flash: { value: new T.Vector4(0, 0, 0, 0) },        // a light above the ground (the impact): position, strength
    flashR: { value: 2.0 },                              // its reach (units)
    fire: { value: new T.Vector4(1, 0, 0, 0) },         // the impact point (direction) and how far the fire has spread (angle)
    fire2: { value: new T.Vector4(0, 0, 0, 0) },        // burning front strength, glow of the air, melt, smoke
    hits: { value: Array.from({ length: 8 }, () => new T.Vector4(1, 0, 0, -1)) },
    shk: { value: new T.Vector2(0, 0) },               // the air's shock wave from the impact: its angle, strength
    pre: { value: new T.Vector2(0, 0.35) } };          // the air glowing under the Moon before it touches: strength, reach (rad)   // small impacts: direction, age (s)
  const earth = new T.Mesh(new T.SphereGeometry(ER, 768, 384), new T.ShaderMaterial({ uniforms: U, vertexShader: VS, extensions: { derivatives: true },
    fragmentShader: `uniform sampler2D color, night, clouds, hgt; uniform vec3 sun, C, moonDir; uniform mat3 toBody;
      uniform float R, zeta, cloudLon, exposure, haze, atm, lights, flashR, cloudK; uniform vec4 moonL, flash, fire, fire2; uniform vec4 hits[8]; uniform vec2 shk;
      varying vec3 vW;
      ${NOISE}
      ${AIR}
      vec2 uvOf(vec3 b, float lonOff) {
        float lat = asin(clamp(b.y, -1.0, 1.0)), lon = atan(-b.z, b.x) + lonOff;
        return vec2(fract((lon + 3.14159265) / 6.2831853), (lat + 1.5707963) / 3.14159265);
      }
      void main() {
        vec3 n = normalize(vW - C), V = normalize(cameraPosition - vW), b = toBody * n;
        vec2 uv = uvOf(b, 0.0);
        vec3 c = pow(texture2D(color, uv).rgb, vec3(2.2));
        vec3 hq = texture2D(hgt, uv).rgb * 255.0;
        float h = 64.0 * (hq.r - 128.0) + (hq.g - 128.0) * 0.25;
        float sea0 = smoothstep(100.0, 160.0, hq.b);                         // the sea as the day map shows it
        float px = length(fwidth(vW)) / R;                                     // radians per pixel
        // finer than the 5 km grid: the ground's own unevenness, so a rising sea creeps up valleys, not along contours
        // (never across the coast: the noise scales with the height, so the shore at sea level stays where it is)
        float kd = 1.0 - smoothstep(0.0003, 0.0012, px);
        float nz = fb(b * 260.0) * 0.7 + fb(b * 900.0) * 0.3 * kd;
        h += nz * clamp(abs(h), 0.0, 80.0) * 0.45;
        // the tide: the sea surface lifted toward the Moon and on the far side, lowered round the middle (equilibrium
        // tide, zeta = its height under the Moon, metres)
        float mm = dot(n, moonDir), zt = zeta * 0.5 * (3.0 * mm * mm - 1.0);
        float wd = zt - h, ew = max(fwidth(wd) * 0.7, 0.4);
        float flooded = (1.0 - sea0) * smoothstep(-ew, ew, wd) * step(0.5, abs(zeta));
        float exposed = sea0 * smoothstep(-ew, ew, -wd) * step(0.5, abs(zeta));
        vec3 floodC = mix(vec3(0.060, 0.052, 0.030), vec3(0.010, 0.032, 0.050), smoothstep(3.0, 120.0, wd));   // muddy, then deep
        floodC *= 0.9 + 0.2 * fb(b * 400.0 + 3.0);
        vec3 bedC = mix(vec3(0.075, 0.068, 0.056), vec3(0.11, 0.10, 0.085), 0.5 + 0.5 * fb(b * 900.0)) * (0.8 + 0.25 * smoothstep(0.0, 300.0, -wd));
        vec3 cs = mix(c, floodC, flooded);
        cs = mix(cs, bedC, exposed);
        float water = clamp(sea0 * (1.0 - exposed) + flooded, 0.0, 1.0);
        // white water where the flood is still arriving (a few metres deep at its edge)
        float foam = 0.45 * (1.0 - sea0) * exp(-pow(wd / max(ew * 1.5, 1.5), 2.0)) * smoothstep(5.0, 40.0, zeta) * (0.5 + 0.5 * fb(b * 1500.0));
        float mu = dot(n, sun), day = smoothstep(-0.12, 0.08, mu);
        vec3 sunG = sunT(0.0, mu) * smoothstep(-0.03, 0.04, mu);
        float lit = max(mu, 0.0) * smoothstep(-0.05, 0.12, mu);
        vec3 col = cs * lit * 2.6 * sunG + vec3(0.55, 0.6, 0.62) * foam * lit * 1.4 * sunG;
        // clouds (drifting by cloudLon) and their shadows; frayed by finer noise up close
        float cl = texture2D(clouds, uvOf(b, cloudLon)).r;
        float k1 = 1.0 - smoothstep(0.0006, 0.002, px);
        cl = clamp(cl + (fb(b * 1400.0 + 7.0) * 0.7 + fb(b * 5200.0) * 0.3) * k1 * 0.9 * cl * (1.0 - cl) * 4.0 - 0.06 * k1 * (1.0 - cl), 0.0, 1.0);
        cl = mix(cl, smoothstep(0.35, 0.95, cl), 1.0 - cloudK) * mix(0.55, 1.0, cloudK);      // thinned: the thin haze goes first
        // the impact's shock wave racing out through the air: it sweeps the clouds away behind it
        float fa0 = acos(clamp(dot(n, fire.xyz), -1.0, 1.0)), shkIn = 0.0, shkRing = 0.0;
        if (shk.y > 0.0) {
          float sw = fa0 + 0.015 * fb(n * 40.0);
          shkIn = 1.0 - smoothstep(shk.x - 0.04, shk.x, sw);
          shkRing = exp(-pow((sw - shk.x) / 0.01, 2.0)) * shk.y;
          cl *= 1.0 - 0.85 * shkIn * shk.y;
        }
        vec3 ns = normalize(b + (toBody * sun) * 0.0018 / max(mu, 0.15));
        col *= 1.0 - 0.55 * texture2D(clouds, uvOf(ns, cloudLon)).r * cloudK * (1.0 - 0.85 * shkIn * shk.y);
        vec3 Hh = normalize(sun + V);
        float g = pow(max(dot(n, Hh), 0.0), 600.0) * 0.45 + pow(max(dot(n, Hh), 0.0), 40.0) * 0.035;
        col += vec3(1.0, 0.93, 0.80) * g * water * (1.0 - cl) * day;
        // new water mirrors the sky: a pale blue sheen, strongest at a slant (the old sea already has it in the map)
        float fr = 0.02 + 0.98 * pow(1.0 - max(dot(n, V), 0.0), 5.0);
        col += vec3(0.20, 0.30, 0.45) * (0.35 + fr) * flooded * lit * sunG * 0.5 * (1.0 - cl);
        vec3 cloudCol = vec3(1.0, 0.99, 0.97) * (pow(max(mu, 0.0), 0.8) * 2.4) * sunT(0.01, mu + 0.03) * smoothstep(-0.05, 0.03, mu);
        // moonlight: on the night side, on the ground and the clouds (it grows as the Moon nears)
        vec3 mL = vec3(0.75, 0.78, 0.85) * moonL.w * max(dot(n, moonL.xyz), 0.0) * (1.0 - day);
        col += cs * mL; cloudCol += vec3(0.8) * mL;
        col = mix(col, cloudCol, cl * 0.92);
        // city lights at night: out where the sea has come in, dimmed under cloud, out altogether as the end comes
        vec3 L = pow(texture2D(night, uv).rgb, vec3(2.2)) * vec3(1.0, 0.85, 0.65);
        col += L * (1.0 - day) * (1.0 - flooded) * (1.0 - 0.6 * cl) * lights * 1.6;
        // the impact: the light of the fireball over everything that faces it
        if (flash.w > 0.0) {
          vec3 Lf = flash.xyz - vW; float dl = length(Lf);
          float f = flash.w * max(dot(n, Lf / dl), 0.0) / (1.0 + dl * dl / (flashR * flashR));
          col += vec3(1.0, 0.62, 0.32) * f * mix(cs * 3.0 + 0.02, vec3(0.9), cl);
        }
        // rubble already down: each a glowing spot that spreads and dims
        for (int i = 0; i < 8; i++) {
          if (hits[i].w < 0.0) continue;
          float a = acos(clamp(dot(n, hits[i].xyz), -1.0, 1.0)), age = hits[i].w;
          float r = 0.004 + 0.0006 * age, k = exp(-age / 90.0);
          col += vec3(1.0, 0.55, 0.2) * exp(-a * a / (r * r)) * k * 3.0 + vec3(1.0, 0.3, 0.08) * exp(-a / (r * 4.0)) * k * 0.3;
        }
        // the aftermath (fire: where it struck, the front's angle; fire2: the front's glow, the air's glow, melt, smoke):
        // a ragged front of falling ejecta and fire runs out over the world; behind it the ground burns black, then the
        // crust melts — dark plates over cracks of glowing rock, hottest where it struck — under drifting smoke
        if (fire2.x > 0.0 || fire2.z > 0.0) {
          float fa = acos(clamp(dot(n, fire.xyz), -1.0, 1.0));
          float edge = fire.w * (1.0 + 0.1 * fb(n * 6.0 + 2.0)) + 0.025 * fb(n * 40.0);
          float inside = 1.0 - smoothstep(edge - 0.03, edge, fa);
          float front = exp(-pow((fa - edge + 0.02) / 0.05, 2.0)) * (0.6 + 0.8 * smoothstep(-0.3, 0.5, fb(n * 30.0 + 9.0)));
          float since = clamp((edge - fa) / 0.4, 0.0, 1.0);                      // how long ago the front passed here (0..1)
          float near = exp(-fa / 0.35);                                           // hottest where it struck
          // burning: scattered fires, then the whole ground black
          float fires = smoothstep(0.35, 0.75, fb(b * 180.0 + 3.0) * 0.5 + 0.5) * (0.5 + 0.5 * fb(b * 700.0));
          col = mix(col, col * 0.06, inside * fire2.x);
          col += vec3(1.0, 0.42, 0.10) * fires * inside * fire2.x * (1.0 - since * 0.6) * 0.9;
          // the melt: plates of dark crust, the glowing rock showing in the cracks between them
          float m = clamp(inside * fire2.z * (0.25 + 0.75 * near + 0.5 * since), 0.0, 1.0);
          float plates = abs(fb(b * 38.0 + 1.0)) + 0.6 * abs(fb(b * 140.0 + 7.0));
          float crack = 1.0 - smoothstep(0.02, 0.09 + 0.12 * near, plates);
          vec3 hot = mix(vec3(0.75, 0.10, 0.01), vec3(1.0, 0.62, 0.20), clamp(near * 1.2 + crack * 0.3, 0.0, 1.0));
          col = mix(col, vec3(0.012, 0.008, 0.006) + hot * (0.05 + 0.25 * near), m);
          col += hot * crack * m * (2.2 + 3.0 * near) * (0.7 + 0.6 * fb(b * 9.0 + vec3(fire.w)));
          // pools of melt where the plates have gone under
          col += hot * smoothstep(0.62, 0.9, fb(b * 14.0 + 4.0) * 0.5 + 0.5) * m * 1.4;
          col += vec3(1.0, 0.5, 0.18) * front * fire2.x * 2.2;
          // smoke: drifting billows, lit orange from below
          float sm = inside * fire2.w * smoothstep(-0.15, 0.45, fb(n * 9.0 + 4.0 + vec3(fire.w * 2.0)) + 0.25 * fb(n * 30.0));
          col = mix(col, vec3(0.03, 0.022, 0.018) * (0.4 + 0.6 * max(mu, 0.0)) + hot * m * 0.12, sm * 0.7);
        }
        // the shock front itself: a thin bright wall of compressed, glowing air and dust running over the ground
        col += vec3(1.0, 0.82, 0.62) * shkRing * (0.6 + 0.6 * fb(n * 90.0)) * 1.6;
        // the air between us and the ground: it dims what is below and adds its own sunlit blue
        vec3 Tv = exp(-BETA * HS * airmass(max(dot(n, V), 0.0)) * haze);
        float cs2 = dot(-V, sun), ph = 0.75 * (1.0 + cs2 * cs2) + 0.5 * pow(max(cs2, 0.0), 8.0);
        vec3 sunA = sunT(0.008, mu + 0.02) * smoothstep(-0.03, 0.05, mu) * mix(0.45, 1.0, smoothstep(0.0, 0.3, mu));
        // after the impact the air is full of ash and smoke: brown, lit orange from below, not blue
        sunA *= mix(vec3(1.0), vec3(0.55, 0.32, 0.18), clamp(fire2.w * 1.2, 0.0, 1.0));
        col = col * Tv + (1.0 - Tv) * (sunA * ph * atm * 0.75 + vec3(1.0, 0.35, 0.1) * fire2.z * 0.25);
        col = vec3(1.0) - exp(-col * exposure);
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  // the atmosphere edge-on (as in the dinosaur video), with the air glowing orange where the rubble comes down
  const halo = new T.Mesh(new T.SphereGeometry(ER * 1.035, 256, 128), new T.ShaderMaterial({ uniforms: U, vertexShader: VS,
    transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.FrontSide,
    fragmentShader: `uniform vec3 sun, C, moonDir; uniform float R, atm; uniform vec4 fire, fire2, flash; uniform float flashR; uniform vec2 pre; varying vec3 vW;
      ${AIR}
      void main() {
        vec3 d = normalize(vW - cameraPosition), oc = C - cameraPosition;
        vec3 near = cameraPosition + d * dot(oc, d);
        float b = length(near - C);
        if (b < R - 0.0004) discard;
        float h = max(b - R, 0.0);
        vec3 up = normalize(near - C);
        vec3 tauV = BETA * exp(-h / HS) * sqrt(6.2831853 * R * HS);
        float ms = dot(up, sun) + sqrt(2.0 * h / R);
        vec3 lit = sunT(h, ms) * smoothstep(-0.02, 0.01, ms);
        float cs = dot(d, sun), ph = 0.75 * (1.0 + cs * cs) + 0.5 * pow(max(cs, 0.0), 8.0);
        vec3 L = (1.0 - exp(-tauV)) * lit * ph * atm;
        // the impact's light in the air round the limb, and the upper air heated where the rubble falls
        if (flash.w > 0.0) {
          float dl = length(flash.xyz - near);
          L += vec3(1.0, 0.6, 0.3) * (1.0 - exp(-tauV.g)) * flash.w * 0.6 / (1.0 + dl * dl / (flashR * flashR));
        }
        if (pre.x > 0.0) {
          // before the touch: the rubble already pouring in and the Moon's front pushing into the air make the sky over
          // the place glow, a dome of light rising behind our horizon
          float a = acos(clamp(dot(up, moonDir), -1.0, 1.0));
          L += vec3(1.0, 0.55, 0.25) * pre.x * exp(-a * a / (pre.y * pre.y)) * exp(-pow((h - 0.05) / 0.045, 2.0)) * 6.0;
        }
        if (fire2.y > 0.0) {
          float a = acos(clamp(dot(up, fire.xyz), -1.0, 1.0));
          float G = 1.0 - smoothstep(fire.w * 0.8, fire.w * 1.15 + 0.05, a);
          L += vec3(1.0, 0.36, 0.11) * fire2.y * 10.0 * G * exp(-pow((h - 0.06) / 0.035, 2.0));
        }
        gl_FragColor = vec4(L, 1.0);
      }` }));
  earth.renderOrder = 0; halo.renderOrder = 6;
  scene.add(earth, halo);

  // ---- the Moon -----------------------------------------------------------------------------------------------------
  // A unit sphere scaled to the Moon; its local +x looks at the Earth (the near side's middle). In the vertex shader it
  // is stretched along that axis by the tides (stretch: 0 = round) with its near end a little pointed.
  const MU = { map: { value: moonTex }, nrm: { value: moonNrm }, sun: U.sun, exposure: { value: 1.0 },
    stretch: { value: 0 }, crack: { value: 0 }, heat: { value: 0 }, spin: { value: 0 }, earthLit: { value: 0.3 }, melt: { value: 0 },
    toEarth: { value: new T.Vector3(-1, 0, 0) }, ER: { value: ER } };
  const moon = new T.Mesh(new T.SphereGeometry(1, 256, 128), new T.ShaderMaterial({ uniforms: MU, extensions: { derivatives: true },
    vertexShader: `uniform float stretch; varying vec3 vP, vW, vN; varying vec2 vUv;
      void main() {
        vec3 p = position;
        float e = stretch, ax = p.x;
        p.x = ax * (1.0 + e) + e * 0.25 * pow(max(ax, 0.0), 4.0);
        p.yz *= inversesqrt(1.0 + e);
        vP = position; vUv = uv;
        vec4 w = modelMatrix * vec4(p, 1.0); vW = w.xyz;
        vN = normalize(mat3(modelMatrix) * vec3(position.x / (1.0 + e), position.yz * sqrt(1.0 + e)));
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: `uniform sampler2D map, nrm; uniform vec3 sun, toEarth; uniform float exposure, crack, heat, spin, earthLit, ER, melt;
      varying vec3 vP, vW, vN; varying vec2 vUv;
      ${NOISE}
      // cracks: the edges of cells on the sphere (3-D Voronoi), more and wider on the side facing the Earth
      vec2 vor(vec3 p) {
        vec3 i = floor(p); float d1 = 9.0, d2 = 9.0;
        for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++) {
          vec3 c = i + vec3(x, y, z); vec3 o = c + vec3(h3(c), h3(c + 17.3), h3(c + 31.7));
          float d = length(p - o);
          if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) d2 = d;
        }
        return vec2(d1, d2);
      }
      void main() {
        vec2 uv = vec2(vUv.x + spin, vUv.y);
        vec3 n = normalize(vN), V = normalize(cameraPosition - vW);
        // relief from the site's normal map (tangent space: east = increasing u, north = increasing v)
        vec3 E = normalize(cross(vec3(0.0, 1.0, 0.0), n) + 1e-5), N = cross(n, E);
        vec3 tn = texture2D(nrm, uv).rgb * 2.0 - 1.0;
        vec3 nb = normalize(E * tn.x * 1.4 + N * tn.y * 1.4 + n * tn.z);
        vec3 alb = pow(texture2D(map, uv).rgb, vec3(2.2)) * 1.25;
        float mu0 = max(dot(nb, sun), 0.0), mu = max(dot(n, V), 0.0), m0 = max(dot(n, sun), 0.0);
        float ls = m0 / (m0 + mu + 1e-4) * 2.0;
        vec3 col = alb * (0.6 * ls * mu0 / max(m0, 0.05) + 0.4 * mu0) * 2.3;
        col += alb * earthLit * max(dot(nb, toEarth), 0.0) * 0.08;          // earthshine on the night side
        // the cracks: dark gaps opening, their walls glowing faintly (fresh, shattered rock heated by the strain)
        if (crack > 0.0) {
          float side = dot(normalize(vP), vec3(1.0, 0.0, 0.0));
          float k = crack * smoothstep(-0.6, 0.6, side + 0.6 * crack);
          // the cells warped so they are not a net: long jagged faults, branching finer cracks near the Earth-facing side
          vec3 q = vP + 0.35 * vec3(fb(vP * 2.0 + 1.0), fb(vP * 2.0 + 5.0), fb(vP * 2.0 + 9.0));
          vec2 v1 = vor(q * 3.2 + 3.0), v2 = vor(q * 9.0 + 7.0);
          float w1 = 0.045 * k, w2 = 0.028 * k * smoothstep(0.3, 1.0, crack);
          float c1 = (1.0 - smoothstep(0.0, w1 + 1e-4, v1.y - v1.x)) * smoothstep(-0.1, 0.35, fb(q * 1.7 + 2.0) + 0.5 * crack);
          float c2 = (1.0 - smoothstep(0.0, w2 + 1e-4, v2.y - v2.x)) * smoothstep(0.15, 0.6, fb(q * 3.0) + crack * 0.4 + 0.3 * side);
          float cc = max(c1, c2 * 0.8) * step(0.001, k);
          col *= 1.0 - 0.8 * cc;
          col += vec3(1.0, 0.33, 0.07) * cc * k * k * 0.35 * (0.5 + 0.5 * fb(vP * 20.0)) * (0.35 + 0.65 * smoothstep(0.0, 0.3, m0)) * (1.0 + 7.0 * melt);
          // going in: the whole body splits along its faults, the cracks running with molten rock, its lower half glowing
          if (melt > 0.0) col += vec3(1.0, 0.38, 0.09) * melt * smoothstep(-0.2, 0.9, side) * (0.25 + 0.5 * cc + 0.25 * fb(vP * 8.0));
        }
        // ploughing into the air: what is low glows white-hot, the rest orange
        float hgt = length(vW) - ER;
        if (heat > 0.0) {
          float hh = 1.0 - smoothstep(0.0, 0.4, hgt);
          col += heat * (vec3(1.0, 0.85, 0.6) * pow(hh, 3.0) * 6.0 + vec3(1.0, 0.4, 0.1) * hh * 1.2);
        }
        col = vec3(1.0) - exp(-col * exposure);
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  moon.renderOrder = 1; scene.add(moon);

  // ---- rubble: rocks big enough to have a shape (instanced), and a cloud of small stuff (points) -------------------
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const rock = new T.IcosahedronGeometry(1, 3);
  { const p = rock.attributes.position, v = new T.Vector3();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i);
      const k = 1 + 0.28 * Math.sin(v.x * 3.1 + 1) * Math.sin(v.y * 2.7 + 2) + 0.18 * Math.sin(v.z * 5.3 + v.x * 2.1) + 0.08 * Math.sin(v.y * 11 + v.z * 9);
      v.multiplyScalar(k); p.setXYZ(i, v.x, v.y, v.z);
    }
    rock.computeVertexNormals(); }
  const NR = 2000;
  const rocks = new T.InstancedMesh(rock, new T.ShaderMaterial({ uniforms: { sun: U.sun, glowK: { value: 0 }, ER: { value: ER } },
    vertexShader: `attribute float tint, hot; varying vec3 vN, vW; varying float vT, vHot;
      void main() { vec4 w = modelMatrix * instanceMatrix * vec4(position, 1.0); vW = w.xyz; vT = tint; vHot = hot;
        vN = normalize(mat3(modelMatrix) * mat3(instanceMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: `uniform vec3 sun; uniform float glowK, ER; varying vec3 vN, vW; varying float vT, vHot;
      void main() {
        vec3 n = normalize(vN), V = normalize(cameraPosition - vW);
        float m0 = max(dot(n, sun), 0.0), mu = max(dot(n, V), 0.0);
        vec3 col = vec3(0.16, 0.15, 0.14) * vT * (m0 / (m0 + mu + 1e-4) * 1.4 + 0.5 * m0) * 2.4;
        float hgt = length(vW) - ER, hh = 1.0 - smoothstep(0.0, 0.15, hgt);
        col += vec3(1.0, 0.45, 0.12) * (glowK * 0.25 * pow(1.0 - mu, 2.0) + hh * 4.0) + vec3(1.0, 0.5, 0.15) * vHot * (0.6 + 1.4 * pow(1.0 - mu, 1.5));
        col = vec3(1.0) - exp(-col);
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }), NR);
  rocks.geometry = rock.clone(); rocks.geometry.setAttribute('tint', new T.InstancedBufferAttribute(new Float32Array(NR).map(() => 0.7 + 0.6 * rnd()), 1));
  rocks.geometry.setAttribute('hot', new T.InstancedBufferAttribute(new Float32Array(NR), 1));
  rocks.frustumCulled = false; rocks.count = 0; rocks.renderOrder = 2; scene.add(rocks);

  const ND = 16000;
  const dg = new T.BufferGeometry();
  dg.setAttribute('position', new T.BufferAttribute(new Float32Array(ND * 3), 3));
  dg.setAttribute('sz', new T.BufferAttribute(new Float32Array(ND).map(() => 0.6 + 2.2 * Math.pow(rnd(), 3)), 1));
  dg.setAttribute('alpha', new T.BufferAttribute(new Float32Array(ND), 1));
  const dust = new T.Points(dg, new T.ShaderMaterial({ uniforms: { sun: U.sun, gain: { value: 1 }, ER: { value: ER } },
    transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    vertexShader: `attribute float sz, alpha; uniform float ER; varying float vA, vHot;
      void main() { vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
        gl_PointSize = sz * clamp(8.0 / -mv.z, 0.8, 3.0); vA = alpha; vHot = 1.0 - smoothstep(0.0, 0.12, length(position) - ER); }`,
    fragmentShader: `uniform float gain; varying float vA, vHot;
      void main() { vec2 q = gl_PointCoord - 0.5; float r = length(q) * 2.0; if (r > 1.0) discard;
        vec3 c = mix(vec3(0.75, 0.72, 0.68) * 0.5, vec3(1.0, 0.6, 0.25) * 3.0, vHot);
        gl_FragColor = vec4(c * exp(-r * r * 3.0) * vA * gain, 1.0); }` }));
  dust.frustumCulled = false; dust.renderOrder = 3; scene.add(dust);

  // ---- fire and smoke particles laid out in advance with birth times (as in the dinosaur video) ----------------------
  const MAXPT = renderer.getContext().getParameter(renderer.getContext().ALIASED_POINT_SIZE_RANGE)[1];
  const FXV = `attribute vec3 vel; attribute float tb, life, s0, s1, seed;
    uniform float time, scale, maxPt; uniform vec3 grav;
    varying float vA, vSeed;
    void main() {
      float age = time - tb, a = age / life;
      if (age < 0.0 || a > 1.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
      vec3 p = position + vel * age + 0.5 * grav * age * age;
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      gl_PointSize = clamp(mix(s0, s1, sqrt(a)) * scale / max(-mv.z, 1e-5), 1.0, maxPt);
      gl_Position = projectionMatrix * mv; vA = a; vSeed = seed;
    }`;
  function fx(n, glow) {
    const g = new T.BufferGeometry(), A = {};
    for (const [k, m] of [['position', 3], ['vel', 3], ['tb', 1], ['life', 1], ['s0', 1], ['s1', 1], ['seed', 1]])
      g.setAttribute(k, A[k] = new T.BufferAttribute(new Float32Array(n * m), m));
    const u = { time: { value: 0 }, scale: { value: H / 2 }, maxPt: { value: MAXPT }, grav: { value: new T.Vector3() },
      heat: { value: 3 }, gain: { value: 1 }, smoke: { value: new T.Color(0.10, 0.08, 0.07) } };
    const m = new T.ShaderMaterial({ uniforms: u, vertexShader: FXV, transparent: true, depthWrite: false,
      blending: glow ? T.AdditiveBlending : T.NormalBlending,
      fragmentShader: glow ? `uniform float heat, gain; varying float vA, vSeed;
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
        }` : `uniform float gain; uniform vec3 smoke; varying float vA, vSeed;
        float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
        void main() {
          vec2 d = gl_PointCoord - 0.5;
          float puff = 0.6 * n2(d * 4.0 + vSeed * 41.0) + 0.4 * n2(d * 9.0 - vSeed * 17.0);
          float r = length(d) * 2.0 * (0.7 + 0.6 * puff); if (r > 1.0) discard;
          float a = exp(-r * r * 2.5) * smoothstep(0.0, 0.08, vA) * (1.0 - smoothstep(0.55, 1.0, vA)) * 0.3 * gain;
          gl_FragColor = vec4(smoke * (0.8 + 0.4 * vSeed), a);
        }` });
    const p = new T.Points(g, m); p.frustumCulled = false; p.visible = false; p.renderOrder = glow ? 5 : 4; scene.add(p);
    return { points: p, u, A, n,
      set(i, pos, vel, tb, life, s0, s1, seed) {
        A.position.setXYZ(i, pos.x, pos.y, pos.z); A.vel.setXYZ(i, vel.x, vel.y, vel.z);
        A.tb.setX(i, tb); A.life.setX(i, life); A.s0.setX(i, s0); A.s1.setX(i, s1); A.seed.setX(i, seed);
      },
      done() { for (const a of Object.values(A)) a.needsUpdate = true; } };
  }

  // ---- meteors: streaks with a white head and a cooling tail (as in the dinosaur video) ------------------------------
  function streaks(n) {
    const g = new T.InstancedBufferGeometry();
    g.setAttribute('position', new T.Float32BufferAttribute([0, -1, 0, 0, 1, 0, 1, -1, 0, 1, 1, 0], 3));
    g.setIndex([0, 2, 1, 1, 2, 3]);
    const A = {};
    for (const [k, m] of [['p0', 3], ['vel', 3], ['tb', 1], ['life', 1], ['len', 1], ['bri', 1]])
      g.setAttribute(k, A[k] = new T.InstancedBufferAttribute(new Float32Array(n * m), m));
    g.instanceCount = n;
    const u = { time: { value: 0 }, res: { value: new T.Vector2(W, H) }, width: { value: 1.6 }, gain: { value: 1 }, ref: { value: 4 } };
    const mesh = new T.Mesh(g, new T.ShaderMaterial({ uniforms: u, transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
      vertexShader: `attribute vec3 p0, vel; attribute float tb, life, len, bri; uniform float time, width, ref; uniform vec2 res;
        varying vec2 vQ; varying float vL, vB;
        void main() {
          float age = time - tb, a = age / life;
          vec3 head = p0 + vel * age, tail = head - normalize(vel) * len * smoothstep(0.0, 0.35, a);
          vec4 ch = projectionMatrix * viewMatrix * vec4(head, 1.0), ct = projectionMatrix * viewMatrix * vec4(tail, 1.0);
          if (age < 0.0 || a > 1.0 || ch.w < 0.01 || ct.w < 0.01) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
          vec2 sh = ch.xy / ch.w * res * 0.5, st = ct.xy / ct.w * res * 0.5, ax = sh - st;
          float L = length(ax); ax = L > 1e-3 ? ax / L : vec2(1.0, 0.0);
          vec4 c = mix(ch, ct, position.x);
          vec2 off = vec2(-ax.y, ax.x) * position.y * width * 1.8 + ax * width * 1.8 * (1.0 - 2.0 * position.x);
          c.xy += off * 2.0 / res * c.w;
          gl_Position = c;
          vQ = vec2(mix(-width * 1.8, L + width * 1.8, position.x), position.y * width * 1.8); vL = L;
          vB = bri * smoothstep(0.0, 0.15, a) * (1.0 - smoothstep(0.55, 1.0, a)) * (0.6 + 0.8 * a) * clamp(ref / ch.w, 0.15, 3.0);
        }`,
      fragmentShader: `uniform float width, gain; varying vec2 vQ; varying float vL, vB;
        void main() {
          float dx = max(max(-vQ.x, vQ.x - vL), 0.0), d = length(vec2(dx, vQ.y)) / width;
          float f = clamp(vQ.x / max(vL, 1.0), 0.0, 1.0);
          float k = exp(-d * d * 1.4) * (pow(1.0 - f, 1.6) * 0.8 + 1.6 * exp(-vQ.x * vQ.x / (width * width * 4.0)));
          vec3 col = mix(vec3(1.0, 0.92, 0.75), vec3(1.0, 0.45, 0.10), smoothstep(0.0, 0.3, f));
          col = mix(col, vec3(0.55, 0.07, 0.01), smoothstep(0.3, 1.0, f));
          gl_FragColor = vec4(col * k * vB * gain, 1.0);
        }` }));
    mesh.frustumCulled = false; mesh.visible = false; mesh.renderOrder = 5; scene.add(mesh);
    return { mesh, u, A, n,
      set(i, p0, vel, tb, life, len, bri) {
        A.p0.setXYZ(i, p0.x, p0.y, p0.z); A.vel.setXYZ(i, vel.x, vel.y, vel.z);
        A.tb.setX(i, tb); A.life.setX(i, life); A.len.setX(i, len); A.bri.setX(i, bri);
      },
      done() { for (const a of Object.values(A)) a.needsUpdate = true; } };
  }

  // soft round glows that keep their size in the world (the impact's fireball, seen over the limb)
  function glowTex(stops) {
    const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    for (const [o, col] of stops) gr.addColorStop(o, col);
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256); return new T.CanvasTexture(c);
  }
  function glow(stops, depthTest = true) {
    const s = new T.Sprite(new T.SpriteMaterial({ map: glowTex(stops), blending: T.AdditiveBlending, transparent: true, depthWrite: false, depthTest }));
    s.visible = false; s.renderOrder = 7; scene.add(s); return s;
  }
  const fireball = {
    core: glow([[0, 'rgba(255,255,245,1)'], [0.3, 'rgba(255,235,190,0.85)'], [0.65, 'rgba(255,160,70,0.25)'], [1, 'rgba(255,110,40,0)']]),
    halo: glow([[0, 'rgba(255,190,110,0.5)'], [0.35, 'rgba(255,130,50,0.2)'], [0.7, 'rgba(190,60,20,0.05)'], [1, 'rgba(120,30,10,0)']]),
  };

  // ---- stars --------------------------------------------------------------------------------------------------------
  const sp = [], sc = [];
  for (let i = 0; i < 9000; i++) {
    const z = rnd() * 2 - 1, p = rnd() * Math.PI * 2, r = Math.sqrt(1 - z * z), m = Math.pow(rnd(), 3.5);
    sp.push(r * Math.cos(p) * 1500, z * 1500, r * Math.sin(p) * 1500);
    const t = rnd(), b = 0.25 + 0.75 * m; sc.push(b * (0.85 + 0.15 * t), b * 0.9, b * (1.05 - 0.2 * t));
  }
  const sg = new T.BufferGeometry(); sg.setAttribute('position', new T.Float32BufferAttribute(sp, 3)); sg.setAttribute('color', new T.Float32BufferAttribute(sc, 3));
  const starMat = new T.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true, depthWrite: false, transparent: true, opacity: 1 });
  const stars = new T.Points(sg, starMat); stars.renderOrder = -1;
  scene.add(stars);

  window.X = { T, D, W, H, ER, RM, renderer, scene, camera, earth, halo, U, moon, MU, rocks, dust, fx, streaks, fireball,
    stars, starMat, dirLL, rnd, glow };
  window.WORLD_READY = 1;

  window.startShot = async (name) => {
    const s = window.SHOTS[name];
    if (s.setup) await s.setup(window.X);
  };
  window.renderShot = (name, t) => {
    window.SHOTS[name].frame(window.X, t);
    stars.position.copy(camera.position);
    renderer.setClearColor(0x000000, 1); renderer.clear();
    renderer.render(scene, camera);
    return renderer.domElement.toDataURL('image/jpeg', 0.93);
  };
})();
