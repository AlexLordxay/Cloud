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
    shock: { value: new T.Vector4(1, 0, 0, 0) }, shock2: { value: new T.Vector4(0, 0, 0, 0) },
    hole: { value: new T.Vector4(1, 0, 0, 0) }, dfog: { value: new T.Vector4(0, 0, 0, 0) },
    tsu: { value: new T.Vector4(1, 0, 0, 0) }, tsu2: { value: new T.Vector4(0, 0, 0, 0) },
    fire: { value: new T.Vector4(1, 0, 0, 0) }, fire2: { value: new T.Vector4(0, 0, 0, 0) },
    dark: { value: new T.Vector4(1, 0, 0, 0) }, dark2: { value: new T.Vector4(0, 0, 0, 0) } };
  const earth = new T.Mesh(new T.SphereGeometry(ER, 768, 384), new T.ShaderMaterial({ uniforms: U, vertexShader: VS, extensions: { derivatives: true },
    fragmentShader: `uniform sampler2D color, relief, sea, clouds, pcol, prel; uniform vec4 pbox; uniform vec3 sun, C; uniform float R, bump, cloudLon, exposure, dim;
      uniform vec4 fball, shock, shock2, hole, dfog, tsu, tsu2, fire, fire2, dark, dark2; uniform float haze, atm;
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
      vec3 h33(vec3 p) { return fract(sin(vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)))) * 43758.5453); }
      // the fiery rain (fire: the impact site, the film's time; fire2: flames, the glow of the sky, smoke, when the
      // rain reaches the far side): the ejecta come back in first round the Gulf, last on the far side of the world.
      // since(q): how long ago (film seconds) the rain began over q
      float since(vec3 q) { return fire.w - fire2.w * pow(acos(clamp(dot(q, fire.xyz), -1.0, 1.0)) / 3.1416, 1.25); }
      // fires on one scale: cells of 1/K radian on a 3-D grid, and in a share p of them (clustered) a fire, caught a
      // moment after the rain arrives. It spreads as fires do: fastest downwind, slowly against the wind, its edge made
      // ragged by the ground (the time the flames take to reach a point carries noise laid on the ground, not drawn
      // round the fire, so the perimeter looks like the burn maps of real fires); the flames are the thin edge where
      // that time is now, broken into stretches; inside, black ground and a few embers. It burns out before it leaves
      // its cell (< 0.4), so the 8 nearest cells find every fire. pxc: a pixel in cells. Returns: flames, burnt share
      // is there a fire in cell cc (K: cells per radian; p: the share of cells)? If so: its random numbers, centre, age
      bool fireAt(vec3 cc, float K, float p, out vec3 h, out vec3 ctr, out float age) {
        h = h33(cc); vec3 pr = cc + 0.25 + 0.5 * h.yzx;
        if (h.x > p || abs(length(pr) - K) > 0.25) return false;
        ctr = normalize(pr);
        age = since(ctr) - 0.25 - 2.2 * h.z;                                 // seconds since it caught
        // fires come in clusters (where more burning debris fell, where the woods were drier), with empty land between
        return age >= 0.0 && h.x <= p * smoothstep(-0.4, 0.15, fb(ctr * 14.0 + 21.0));
      }
      // the wind over the region (turning slowly from place to place), along the ground
      vec3 windAt(vec3 ctr, vec3 h) {
        vec3 wv = vec3(vn(ctr * 2.0 + 1.0), vn(ctr * 2.0 + 7.0), vn(ctr * 2.0 + 13.0)) + 0.6 * (h - 0.5);
        return normalize(wv - ctr * dot(wv, ctr) + 1e-5);
      }
      // something to burn: forest and savanna (green, dark), not desert or bare rock (linear colour)
      float fuelOf(vec3 c) { float t = c.r + c.g + c.b; return smoothstep(0.25, 0.42, c.g / (t + 1e-4)) * smoothstep(0.30, 0.06, t); }
      vec2 fires(vec3 n, float K, float p, float grow, float pxc, float fill) {
        vec3 q = n * K, b = floor(q - 0.5); float fl = 0.0, burnt = 0.0;
        for (int i = 0; i < 2; i++) for (int j = 0; j < 2; j++) for (int k = 0; k < 2; k++) {
          vec3 cc = b + vec3(float(i), float(j), float(k)), h, ctr; float age;
          if (!fireAt(cc, K, p, h, ctr, age)) continue;
          vec3 wd = windAt(ctr, h);
          vec3 dv = q - ctr * K; float d = length(dv), cw = dot(dv / max(d, 1e-5), wd);
          // how far the fire has to burn to get here (downwind counts ~1/3, upwind double), plus the ground's say
          float de = d * (1.15 - 0.85 * cw) + 0.06 * fb(q * 2.2 + h * 7.0) + 0.03 * fb(q * 6.0 + h * 3.0);
          float R = age * grow * (0.5 + 0.8 * h.y), Rm = 0.1 + 0.06 * h.z;    // how far it has got; where it dies out
          float live = 1.0 - smoothstep(Rm * 0.7, Rm, R);
          float ws = max(0.02, 0.5 * pxc), amp = max(0.02 / ws, 0.5);
          float edge = exp(-pow((de - min(R, Rm)) / ws, 2.0)) * amp;
          float run = smoothstep(-0.15, 0.3, fb(q * 5.0 + h * 13.0 + age * 0.05));   // stretches burning, stretches out
          float wc = max(0.02, 0.6 * pxc), core = exp(-d * d / (wc * wc)) * max(0.02 / wc, 0.3) * 1.5 * exp(-age / 0.5);
          float inside = smoothstep(min(R, Rm), min(R, Rm) - 0.01, de);
          float ember = inside * 0.03 * smoothstep(0.4, 0.9, vn(dv * 14.0 + h * 5.0)) * smoothstep(0.0, 0.5, age);
          float glow = exp(-pow((de - min(R, Rm)) / 0.04, 2.0)) * 0.04 * live;          // its smoke, lit from below
          float hd = mix(0.2, 1.0, smoothstep(-0.4, 0.6, cw));                    // the head burns hard, the back barely
          fl += ((edge * run * 1.8 * hd + glow + inside * fill) * live + core + ember) * (0.25 + 1.5 * h.y * h.y)
                * (0.75 + 0.25 * sin(fire.w * 11.0 + h.x * 60.0 + d * 40.0));
          burnt = max(burnt, inside);
        }
        return vec2(fl, burnt);
      }
      vec2 uvOf(vec3 n, float lonOff) {
        float lat = asin(clamp(n.y, -1.0, 1.0)), lon = atan(-n.z, n.x) + lonOff;
        return vec2(fract((lon + 3.14159265) / 6.2831853), (lat + 1.5707963) / 3.14159265);
      }
      // water (1) or land (0) at a point: the detailed map inside the impact region, the global one elsewhere
      float seaAt(vec3 q) {
        vec2 pu = vec2((atan(-q.z, q.x) - pbox.z) / (pbox.w - pbox.z), (asin(clamp(q.y, -1.0, 1.0)) - pbox.x) / (pbox.y - pbox.x));
        float pw = smoothstep(0.0, 0.07, min(min(pu.x, 1.0 - pu.x), min(pu.y, 1.0 - pu.y)));
        float g = texture2D(sea, uvOf(q, 0.0)).r;
        return pw > 0.0 ? mix(g, texture2D(prel, pu).b, pw) : g;
      }
      // the smoke of the big fires (the same cells as fires() at this K): from each a plume carried downwind, faster
      // than the fire spreads, widening as it goes, in drifting billows; near the fire lit orange from below by its
      // flames. The 27 nearest cells, so a plume can run ~1 cell (~90 km at K 70) from its fire — about as far as
      // smoke drifts in the hour. Returns: cover (0–1), firelight on it
      vec2 smoke(vec3 n, float K, float p) {
        vec3 q = n * K, b = floor(q); float a = 0.0, lit = 0.0;
        for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) for (int k = -1; k <= 1; k++) {
          vec3 cc = b + vec3(float(i), float(j), float(k)), h, ctr; float age;
          if (!fireAt(cc, K, p, h, ctr, age)) continue;
          float fu = (1.0 - seaAt(ctr)) * fuelOf(pow(texture2D(color, uvOf(ctr, 0.0)).rgb, vec3(2.2)));
          if (fu < 0.05) continue;
          vec3 wd = windAt(ctr, h), dv = q - ctr * K;
          float along = dot(dv, wd); vec3 side = dv - wd * along - ctr * dot(dv, ctr);
          float L = min(0.95, age * 0.2 * (0.6 + 0.8 * h.y)), wdt = 0.04 + 0.35 * max(along, 0.0);
          float body = smoothstep(-0.06, 0.02, along) * (1.0 - smoothstep(L * 0.55, L, along)) * exp(-dot(side, side) / (wdt * wdt));
          float lump = smoothstep(-0.35, 0.45, fb(q * 3.5 - wd * fire.w * 0.35 + h * 9.0));
          float sm = body * lump * fu * (0.55 + 0.45 * h.y);
          a = 1.0 - (1.0 - a) * (1.0 - sm);
          lit += sm * exp(-max(along, 0.0) / 0.22) * (0.25 + 1.5 * h.y * h.y);
        }
        return vec2(a, lit);
      }
      void main() {
        vec3 n = normalize(vW - C), V = normalize(cameraPosition - vW);
        if (hole.w > 0.0 && length(n - hole.xyz) < hole.w) discard;            // the crater mesh is drawn here instead
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
        // the tsunami seen from space (tsu: its source and how far, as an angle, its front has run; tsu2: strength, dust
        // pall radius): rings of white water running out over the oceans, weaker as they spread, partly shadowed by the
        // land they have had to pass; behind them a brown pall of dust spreading from the Gulf
        float tsuRing = 0.0, tsuDark = 0.0, pall = 0.0, surf = 0.0;
        if (tsu2.x > 0.0) {
          float ang = acos(clamp(dot(n, tsu.xyz), -1.0, 1.0));
          float shade = 1.0;
          if (ang > 0.12 && ang < 3.0) {
            float landN = 0.0;
            for (int k = 1; k <= 10; k++) {
              float f = 0.12 / ang + (1.0 - 0.12 / ang) * float(k) / 11.0;
              vec3 q = normalize(mix(tsu.xyz, n, f));
              landN += 1.0 - texture2D(sea, uvOf(q, 0.0)).r;
            }
            shade = 1.0 - 0.55 * clamp(landN / 5.0, 0.0, 1.0);                      // waves bend round small land
          }
          float amp = tsu2.x * shade * (0.8 + 0.2 * exp(-ang / 0.6));
          float wob = fb(n * 30.0 + 2.0) * 0.012, brk = 0.55 + 0.45 * fb(n * 90.0 + 5.0);
          float rw = max(0.006, 2.2 * fwidth(ang)), rd = max(0.007, 2.4 * fwidth(ang));   // thin up close, still seen far off
          for (int k = 0; k < 3; k++) {
            float x = ang + wob - (tsu.w - float(k) * max(0.03, 6.0 * fwidth(ang)));
            tsuRing += amp * exp(-pow(x / rw, 2.0)) * (1.0 - 0.3 * float(k));
            tsuDark += amp * exp(-pow((x + 1.8 * rd) / rd, 2.0)) * (1.0 - 0.3 * float(k));
          }
          tsuRing *= step(ang, tsu.w + 0.04) * brk; tsuDark *= step(ang, tsu.w + 0.04);
          pall = (1.0 - smoothstep(tsu2.y * 0.5, tsu2.y, ang + fb(n * 12.0) * 0.1)) * 0.92 * (0.75 + 0.25 * fb(n * 40.0));
          // where it has reached a coast: the shore flashes white with surf and stays churned for hours after
          if (ang < tsu.w) {
            float d = max(0.0015, 2.0 * fwidth(ang)), s1 = seaAt(normalize(n + E * d)), s2 = seaAt(normalize(n - E * d));
            float s3 = seaAt(normalize(n + N * d)), s4 = seaAt(normalize(n - N * d));
            float coast = max(max(s1, s2), max(s3, max(s4, w))) - min(min(s1, s2), min(s3, min(s4, w)));
            float since = tsu.w - ang;
            surf = coast * amp * (exp(-since / 0.05) * 1.6 + 0.35 * exp(-since / 0.6));
          }
        }
        vec3 nb = normalize(n - bump * (s.x * E + s.y * N));
        float mu = dot(n, sun), day = smoothstep(-0.12, 0.08, mu);
        // finer than the map: fields, woods and gullies at 1–30 km, fading out where they would only shimmer
        float px = length(fwidth(vW)) / R;
        float k1 = 1.0 - smoothstep(0.0006, 0.002, px), k2 = 1.0 - smoothstep(0.00015, 0.0006, px);
        c *= 1.0 + (1.0 - w) * (0.22 * fb(n * 260.0) * k1 + 0.14 * fb(n * 2100.0) * k2);
        vec3 c0 = c;
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
        if (tsu2.x > 0.0) col = mix(col, col * 0.5, clamp(tsuDark, 0.0, 1.0) * w);
        // the water's glint: a sharp sun and a broad sheen
        vec3 Hh = normalize(sun + V);
        float g = pow(max(dot(n, Hh), 0.0), 600.0) * 0.45 + pow(max(dot(n, Hh), 0.0), 40.0) * 0.035;
        col += vec3(1.0, 0.93, 0.80) * g * w * (1.0 - cl) * day;
        float cmu = max(mu, 0.0);
        vec3 cloudCol = vec3(1.0, 0.99, 0.97) * (pow(cmu, 0.8) * 2.4) * sunT(0.01, mu + 0.03) * smoothstep(-0.05, 0.03, mu);
        col = mix(col, cloudCol, cl * 0.92);
        // the fiery rain: the sky over it glows (the upper air heated by countless meteors), brightest as it arrives, and
        // its red light falls on the land, the sea and, most, the clouds — on the night side the only light there is;
        // the land catches fire here and there where there is something to burn (forest and savanna, not desert or
        // bare rock), burning through the clouds' gaps; on the burnt ground the char shows by day
        if (fire2.x > 0.0 || fire2.y > 0.0) {
          float s0 = since(n), G = fire2.y * smoothstep(-0.1, 0.5, s0) * (0.75 + 0.25 * exp(-max(s0, 0.0) / 1.5) + 0.8 * exp(-pow((s0 - 0.25) / 0.3, 2.0)));
          G *= 0.75 + 0.5 * (fb(n * 9.0 + 4.0) * 0.5 + 0.5);                 // patchy: thicker where more debris falls
          vec3 skyL = vec3(1.0, 0.33, 0.10) * G;
          // ... and, before it comes, a little moonlight (fire2.z), cool, so the night is not quite black
          vec3 lightIn = skyL * 3.0 + vec3(0.7, 0.75, 0.9) * fire2.z;
          col += mix(c0 * (1.0 - w) * 1.3 + w * vec3(0.006, 0.006, 0.008), vec3(0.8, 0.78, 0.76), cl) * lightIn;
          float vz = dot(n, V); col += skyL * 0.012 / sqrt(vz * vz + 0.02);      // the glowing layer itself, thicker toward the limb
          float land = smoothstep(0.6, 0.2, w), fuel = land * fuelOf(c0);
          if (fuel > 0.0 && s0 > 0.0) {
            vec2 f1 = fires(n, 70.0, 0.75, 0.03, px * 70.0, 0.06), f2 = fires(n, 260.0, 0.55, 0.012, px * 260.0, 0.7);
            float flame = (f1.x + 0.6 * f2.x) * fuel * fire2.x;
            col *= 1.0 - 0.55 * max(f1.y, f2.y) * fuel * day;                     // char
            col += vec3(1.0, 0.36, 0.07) * flame * (1.0 - 0.85 * cl) + vec3(1.0, 0.45, 0.2) * flame * 0.15 * cl;
          }
          // the smoke: lit by the red sky (and the Sun, by day) from above and by the fires from below; under the clouds
          if (s0 > 0.0) {
            vec2 sm = smoke(n, 70.0, 0.75);
            float sa = sm.x * 0.75 * (1.0 - 0.7 * cl);
            col = mix(col, (lightIn + sunG * max(mu, 0.0) * 2.0) * vec3(0.55, 0.45, 0.38), sa) + vec3(1.0, 0.36, 0.1) * sm.y * fire2.x * 0.2 * (1.0 - 0.7 * cl);
          }
        }
        // the tsunami's white crests show through the gaps and, faintly, through the cloud
        if (tsu2.x > 0.0) {
          col += vec3(0.75, 0.9, 1.0) * clamp(tsuRing, 0.0, 1.5) * w * 1.6 * (1.0 - 0.5 * cl) * (0.2 + 0.8 * max(mu, 0.0));
          col += vec3(0.9, 0.97, 1.0) * clamp(surf, 0.0, 2.0) * 0.9 * (1.0 - 0.5 * cl) * (0.25 + 0.75 * max(mu, 0.0));
        }
        // the air between us and the ground: it dims what is below and adds its own sunlit blue (all of it near the
        // horizon, where we look through the most air); the light it scatters is the Sun's, reddened like the ground's
        vec3 Tv = exp(-BETA * HS * airmass(max(dot(n, V), 0.0)) * haze);
        float cs = dot(-V, sun), ph = 0.75 * (1.0 + cs * cs) + 0.5 * pow(max(cs, 0.0), 8.0);
        vec3 sunA = sunT(0.008, mu + 0.02) * smoothstep(-0.03, 0.05, mu) * mix(0.45, 1.0, smoothstep(0.0, 0.3, mu));
        col = col * Tv + (1.0 - Tv) * sunA * ph * atm * 0.75;
        // the dust and soot ride high, above the weather and most of the air: a brown veil over everything
        if (pall > 0.0) col = mix(col, vec3(0.16, 0.085, 0.035) * (0.15 + 0.85 * max(mu, 0.0)) * sunG, pall);
        // the long night (dark: the impact site, how far, as an angle, the veil has spread; dark2: how thick, how far the
        // high winds have run, how much of it is pale dust rather than soot): soot, sulphate and pulverised rock high
        // above the weather, drawn out by the winds into bands along the latitudes (the jets run at different speeds),
        // ragged at its spreading edge, thickest where it began; dark brown where the soot is, paler with the dust; lit
        // only where the Sun still shines on its top
        if (dark2.x > 0.0) {
          float lat = asin(clamp(n.y, -1.0, 1.0)), sh = dark2.y * (0.5 + 0.9 * cos(lat * 2.0) + 0.4 * sin(lat * 5.0));
          vec3 m = vec3(cos(sh) * n.x - sin(sh) * n.z, n.y, sin(sh) * n.x + cos(sh) * n.z);
          float band = fb(vec3(m.x * 3.0, m.y * 18.0, m.z * 3.0) + 5.0) * 0.5 + fb(m * 9.0 + 4.0) * 0.5, thick = fb(m * 2.2 + 2.0);
          float da = acos(clamp(dot(n, dark.xyz), -1.0, 1.0));
          float reach = 1.0 - smoothstep(dark.w - 0.3, dark.w, da + 0.4 * fb(m * 4.0 + 8.0));
          float op = clamp(dark2.x * reach * (0.8 + 0.25 * thick + 0.06 * band) * (1.0 + 0.3 * exp(-da / 0.5)), 0.0, 1.0);
          vec3 vc = mix(vec3(0.012, 0.0095, 0.0075), vec3(0.036, 0.029, 0.022), clamp(dark2.z + 0.3 * band + 0.3 * thick, 0.0, 1.0));
          // what light gets through has to come down through it and back up again
          col = col * (1.0 - op) * (1.0 - op) + vc * max(mu, 0.0) * 2.4 * sunG * op;
        }
        if (shock.w > 0.0) {
          float dn = fb(n * 900.0 + 3.0) * 0.5 + 0.5;
          col = mix(col, vec3(0.16, 0.12, 0.09) * (0.15 + 0.85 * max(mu, 0.0)) * (0.7 + 0.6 * dn), inside * shock2.w);
          float dr = fb(n * 260.0 + 5.0) * 0.5 + 0.5;
          col += ring * shock2.x * vec3(0.85, 0.72, 0.58) * (0.4 + 1.2 * dr * dr);
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
        if (dfog.a > 0.0) col = mix(col, dfog.rgb, 1.0 - exp(-length(cameraPosition - vW) * 1000.0 * dfog.a));   // dust about the crater
        col = vec3(1.0) - exp(-col * exposure);                                 // soft shoulder: bright clouds don't clip
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  // the atmosphere edge-on: the air along each line of sight that misses the Earth, by the same Rayleigh numbers —
  // the column through the tangent point, how much of it the Sun lights (none in the Earth's shadow, red light near
  // it), forward-scattering a little brighter toward the Sun. White-blue close to the limb, blue higher, then black;
  // at dusk a red-orange layer on the horizon. A hair of glow is let inside the limb, over the mesh's facet gaps.
  const halo = new T.Mesh(new T.SphereGeometry(ER * 1.035, 256, 128), new T.ShaderMaterial({ uniforms: U, vertexShader: VS,
    transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.FrontSide,
    fragmentShader: `uniform vec3 sun, C; uniform float R, dim, atm; uniform vec4 fire, fire2, dark, dark2; varying vec3 vW;
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
        if (fire2.y > 0.0) {
          // the upper air, heated by the ejecta coming back in (they glow and slow ~60–100 km up), seen edge-on round
          // the limb: an orange-red band, brightest as the rain arrives, uneven where more or less of it falls
          float a = acos(clamp(dot(up, fire.xyz), -1.0, 1.0)), s0 = fire.w - fire2.w * pow(a / 3.1416, 1.25);
          float G = smoothstep(-0.1, 0.5, s0) * (0.75 + 0.25 * exp(-max(s0, 0.0) / 1.5) + 0.8 * exp(-pow((s0 - 0.25) / 0.3, 2.0)));
          float lump = 1.0 + 0.5 * sin(dot(up, vec3(23.0, 17.0, 31.0))) * sin(dot(up, vec3(-13.0, 29.0, 7.0)) + 1.3);
          L += vec3(1.0, 0.36, 0.11) * fire2.y * 14.0 * G * mix(1.0, lump, 0.4) * exp(-pow((h - 0.08) / 0.03, 2.0));
        }
        if (dark2.x > 0.0) {
          // under the long night the blue sky is gone: a brown haze, thick and low, where the veil has reached
          float k = dark2.x * (1.0 - smoothstep(dark.w - 0.35, dark.w, acos(clamp(dot(up, dark.xyz), -1.0, 1.0))));
          vec3 hz = lit * ph * vec3(0.5, 0.34, 0.2) * 0.5 * exp(-h / 0.03) * smoothstep(0.0, 0.004, h);
          L = mix(L, hz, clamp(k, 0.0, 1.0) * 0.9);
        }
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
      litH: { value: new T.Vector2(-1, -1) }, litCol: { value: new T.Color(1.0, 0.62, 0.42) },
      shade: { value: 0 }, ldir: { value: new T.Vector2(-0.7, 0.5) } };
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
        }` : `uniform float gain, shade; uniform vec3 smoke, litCol; uniform vec2 litH, ldir; varying float vA, vSeed, vH;
        float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float n2(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
        void main() {
          vec2 d = gl_PointCoord - 0.5;
          float puff = 0.6 * n2(d * 4.0 + vSeed * 41.0) + 0.4 * n2(d * 9.0 - vSeed * 17.0);
          float r = length(d) * 2.0 * (0.7 + 0.6 * puff); if (r > 1.0) discard;
          float a = mix(exp(-r * r * 2.5), smoothstep(1.0, 0.55, r), shade) * smoothstep(0.0, 0.08, vA) * (1.0 - smoothstep(0.55, 1.0, vA)) * mix(0.12, 0.3, shade) * gain;
          vec3 c = smoke * (0.8 + 0.4 * vSeed) * (0.85 + 0.3 * d.x);
          // billows (shade 1): each puff a lumpy ball, lit on one side (ldir, on the screen), shadowed on the other
          vec3 bn = vec3(d.x * 2.0, -d.y * 2.0, sqrt(max(0.0, 1.0 - r * r)));
          float L = 0.35 + 0.75 * max(dot(bn, normalize(vec3(ldir, 0.55))), 0.0) + 0.25 * (puff - 0.5);
          c *= mix(1.0, L, shade);
          // high enough, smoke still catches the Sun that has set on the ground below (litH: from, to — in units)
          if (litH.y > 0.0) c = mix(c * 0.55, litCol * (0.8 + 0.4 * vSeed) * mix(0.8 + 0.4 * d.x, L, shade), smoothstep(litH.x, litH.y, vH));
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


  // ---- the crater ---------------------------------------------------------------------------------------------------
  // A square of ground 500 km across at the site (in its own east/north/up frame, bent to the Earth's curve), shaped in
  // the vertex shader as the crater forms over its first ten minutes (T, seconds), after the drilling of its peak ring
  // (IODP 364, Morgan et al. 2016) and models of it: a transient bowl ~100 km wide and ~28 km deep in the first minute,
  // its walls showing the layers it cut (limestone, anhydrite, then granite); the floor rebounding into a central peak
  // higher than Everest; the peak falling outward into a ring of mountains ~80 km across while the walls slump in
  // terraces to a rim ~180 km across — a basin a kilometre or two deep, its middle a lake of melt. It struck a shallow
  // sea: round the crater a blanket of ejecta, thinning outward until the churned, dark water takes over. Lit by the
  // melt (a warm light from the middle that falls on the walls facing it), by the glowing cloud above, and by
  // lightning; dust in the air. The Earth's own surface has a hole here (U.hole) so the two do not fight.
  const CU = { T: { value: 0 }, ex: { value: 1 }, C0: { value: new T.Vector3() }, eE: { value: new T.Vector3() },
    eN: { value: new T.Vector3() }, eU: { value: new T.Vector3() }, key: { value: new T.Vector3(0, 1, 0) },
    keyI: { value: 1 }, melt: { value: 1 }, fogC: { value: new T.Color(0.05, 0.021, 0.008) }, fogK: { value: 0.0011 },
    flash: { value: 0 }, vt: { value: 0 }, Rw: { value: 0 }, Aw: { value: 0 }, Lin: { value: -100 }, dbg: { value: 0 }, sun: U.sun };
  const CRATER_GLSL = `
    uniform float T, ex, Rw, Aw, Lin; uniform vec3 C0, eE, eN, eU;
    float ch(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float cn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(ch(i), ch(i + vec2(1, 0)), f.x), mix(ch(i + vec2(0, 1)), ch(i + vec2(1, 1)), f.x), f.y) * 2.0 - 1.0; }
    float cf(vec2 p) { return 0.5 * cn(p) + 0.25 * cn(p * 2.07) + 0.13 * cn(p * 4.13) + 0.07 * cn(p * 8.3) + 0.04 * cn(p * 16.7); }
    // ridged noise: sharp crests and gullies, for broken rock
    float rf(vec2 p) { float s = 0.0, a = 0.5; for (int i = 0; i < 5; i++) { float v = 1.0 - abs(cn(p)); s += a * v * v; p *= 2.11; a *= 0.5; } return s; }
    // stages (0…1): the bowl growing, the floor rebounding, the collapse into the final form
    float sGrow() { float g = clamp(T / 70.0, 0.0, 1.0); return 1.0 - (1.0 - g) * (1.0 - g); }
    float sRise() { return smoothstep(70.0, 190.0, T); }
    float sColl() { return smoothstep(200.0, 560.0, T); }
    float rimR() { return mix(50.0 * sqrt(sGrow()) + 0.5, 92.0, sColl()); }
    // height in km at p (km east, north of the centre); the old sea floor ~150 m down
    float craterH(vec2 p) {
      float r = length(p), a = atan(p.y, p.x);
      float g = sGrow(), Rt = 50.0 * sqrt(g) + 0.5, Dt = 28.0 * g;
      float bowl = r < Rt ? -Dt * (1.0 - r * r / (Rt * Rt)) : 0.0;
      float rim = (r < Rt ? pow(r / Rt, 8.0) : pow(Rt / r, 3.0)) * 2.4 * g;
      float wallZone = exp(-pow((r - Rt * 0.75) / (Rt * 0.45), 2.0));
      float wall = (rf(p * 0.07 + 3.0) - 0.45) * 3.2 * g * wallZone;
      // the rebound: the bowl shallows and a central peak rises past the old ground, then spreads and falls
      float rise = sRise(), coll = sColl();
      float pk = 15.0 * rise * (1.0 - smoothstep(190.0, 420.0, T)), pkS = 13.0 + 18.0 * smoothstep(190.0, 420.0, T);
      float peak = pk * exp(-r * r / (pkS * pkS)) * (0.85 + 0.35 * rf(p * 0.12));
      float mid = (bowl + wall) * (1.0 - 0.75 * rise) + rim + peak;
      // the final crater: a melt-filled middle, the peak ring, a trough, walls in slumped blocks up to the rim
      float rr = r / (1.0 + 0.035 * sin(3.0 * a + 1.0) + 0.025 * sin(7.0 * a + 2.0) + 0.02 * cf(p * 0.02));
      float ring = 1.9 * exp(-pow((rr - 40.0) / 6.0, 2.0)) * (0.6 + 0.8 * rf(p * 0.09 + 7.0));
      float s = clamp((rr - 50.0) / 42.0, 0.0, 1.0), st = (floor(s * 5.0) + smoothstep(0.0, 0.65, fract(s * 5.0))) / 5.0;
      float fin = rr < 92.0 ? mix(-1.3, mix(-1.7, 0.7, st), smoothstep(46.0, 54.0, rr)) + ring
                            : 0.75 * pow(92.0 / rr, 12.0);
      fin += (rf(p * 0.1 + 11.0) - 0.4) * 0.35 * smoothstep(40.0, 70.0, rr) * (1.0 - smoothstep(90.0, 100.0, rr));
      float h = mix(mid, fin, coll);
      // outside: the sea floor, under a blanket of ejecta that thins away from the rim, rubbly
      // (most of the ejecta fell into the sea: only the rim and a band just outside it stand above the water)
      float R = rimR(), ej = r > R ? 0.5 * pow(R / r, 14.0) * (0.8 + 0.4 * rf(p * 0.05)) : 0.0;
      return h + (r > R ? -0.15 + ej : 0.0) * smoothstep(0.0, 0.05, g);
    }
    // the tsunami (Rw: how far its crest has got, km; Aw: its height, km): a steep front, a long back, a trough behind;
    // over water only, outside the rim; never exaggerated (the crater's relief is, inside ~100 km)
    float waveH(vec2 p) {
      if (Aw <= 0.0) return -100.0;
      float r = length(p), a = atan(p.y, p.x), x = r - Rw;
      float A = Aw * (1.0 + 0.18 * cf(vec2(a * 14.0, 2.0)) + 0.08 * cf(p * 0.05));
      return A * (x > 0.0 ? exp(-pow(x / 3.5, 2.0)) : exp(-pow(x / 7.0, 2.0))) - 0.3 * Aw * exp(-pow((x + 16.0) / 6.0, 2.0))
             + 0.03 * cf(p * 0.8 + vec2(T * 0.01, 0.0));
    }
    float surfH(vec2 p, out float isWater) {
      float r = length(p), hc = craterH(p), g = hc * (hc > 0.0 ? mix(ex, 1.0, smoothstep(86.0, 94.0, r)) : mix(ex, 1.0, smoothstep(95.0, 110.0, r)));
      // the sea coming back in over the rim (Lin: its level inside, km as drawn; -100 = still dry)
      float w = r > rimR() + 2.0 ? waveH(p) : (Lin > -50.0 ? Lin + 0.02 * cf(p * 0.7 + vec2(T * 0.002, 0.0)) : -100.0);
      isWater = w > g ? 1.0 : 0.0; return max(g, w);
    }
    vec3 cpos(vec2 p) {                     // world position: km in the site frame → units, bent to the curve
      float iw; float h = surfH(p, iw); vec2 u = p / 1000.0;
      return C0 + eE * u.x + eN * u.y + eU * (h / 1000.0 - dot(u, u) / (2.0 * 6.371));
    }`;
  const crater = new T.Mesh(new T.PlaneGeometry(500, 500, 700, 700), new T.ShaderMaterial({ uniforms: CU,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
    vertexShader: CRATER_GLSL + `
      varying vec2 vP; varying vec3 vW, vN; varying float vH, vWet;
      void main() {
        vec2 p = position.xy; vP = p;
        vec3 w = cpos(p), wx = cpos(p + vec2(0.5, 0.0)), wy = cpos(p + vec2(0.0, 0.5));
        vN = normalize(cross(wx - w, wy - w)); vW = w; vH = surfH(p, vWet);
        gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
      }`,
    fragmentShader: CRATER_GLSL + `
      uniform vec3 key, sun, fogC; uniform float keyI, melt, fogK, flash, vt, dbg;
      varying vec2 vP; varying vec3 vW, vN; varying float vH, vWet;
      void main() {
        float r = length(vP); if (r > 245.0) discard;
        vec3 n = normalize(vN); vec3 V = normalize(cameraPosition - vW);
        float g = sGrow(), coll = sColl(), rise = sRise(), R = rimR();
        float a = atan(vP.y, vP.x), ray = 0.5 + 0.5 * cn(vec2(a * 9.0, 0.3)) * cn(vec2(a * 23.0, 1.7));
        // rock and ejecta: dark grey-browns, broken up — pale shattered limestone in patches, darker rubble in hollows
        float rub = rf(vP * 0.4 + 2.0), pal = smoothstep(0.15, 0.45, cf(vP * 0.03 + 9.0));
        vec3 c = mix(vec3(0.10, 0.085, 0.07), vec3(0.30, 0.27, 0.23), pal * 0.7) * (0.7 + 0.5 * rub) * (0.85 + 0.3 * ray);
        // the cut layers on the bowl's walls: limestone and anhydrite pale, then pinkish granite below ~4 km
        float dep = -vH;
        if (dep > 0.3 && coll < 0.9 && r < R + 2.0) {
          float band = 0.5 + 0.5 * cn(vec2(dep * 1.1 + cf(vP * 0.04) * 1.8, 0.37) + vP * 0.004);
          vec3 lay = dep < 4.0 ? mix(vec3(0.34, 0.32, 0.28), vec3(0.52, 0.50, 0.45), band) : vec3(0.32, 0.24, 0.22) * (0.8 + 0.3 * band);
          lay *= 0.6 + 0.6 * rub;
          c = mix(c, lay, smoothstep(0.3, 1.5, dep) * (1.0 - coll));
        }
        // the sea: churned, dark and muddy, foam at the edge of the ejecta and in streaks
        bool water = (vH < 0.0 && r > R + 1.0) || vWet > 0.5;
        float inner = (vWet > 0.5 && r < R + 2.0) ? 1.0 : 0.0;          // the water flooding into the crater
        float wv = cf(vP * 0.6 + vec2(vt * 0.7, -vt * 0.4)) * 0.5 + 0.5;
        // the sea's surface: swell and chop (big and small waves), so the glow breaks up on it in glints
        vec2 sw = vec2(cf(vP * 0.25 + vec2(vt * 0.3, 0.0)), cf(vP * 0.25 + vec2(4.0, -vt * 0.25))) * 0.16
                + vec2(cn(vP * 1.6 + vt), cn(vP * 1.6 - vt + 4.0)) * 0.07;
        vec3 nw = normalize(n + eE * sw.x + eN * sw.y);                  // the mesh's own slope (the wave) plus the chop
        // light: the melt's glow from the middle (on whatever faces it), the cloud above, a flicker of lightning
        vec3 L = (C0 + eU * 0.004) - vW; float dl = length(L) * 1000.0; L = normalize(L);
        float meltI = melt * (0.6 + 0.6 * (1.0 - coll * 0.4)) * smoothstep(0.0, 0.2, g);
        vec3 nn = water ? nw : n;
        vec3 Lm = vec3(1.0, 0.42, 0.10) * meltI * 4.0 / (1.0 + pow(dl / 55.0, 2.0)) * max(dot(nn, L), 0.0);
        vec3 Lk = vec3(1.0, 0.50, 0.22) * keyI * max(dot(nn, key), 0.0) * 0.8;
        vec3 Lf = vec3(0.7, 0.75, 1.0) * flash * (0.4 + 0.6 * max(dot(nn, eU), 0.0));
        vec3 amb = vec3(0.035, 0.02, 0.015) * (0.6 + 0.4 * dot(nn, eU));
        vec3 col = c * (Lm + Lk + Lf + amb);
        if (water) {
          vec3 wc = vec3(0.006, 0.018, 0.03) * (0.7 + 0.6 * wv);
          float fr = 0.03 + 0.97 * pow(1.0 - max(dot(nw, V), 0.0), 5.0);
          // what the sea mirrors: the dark underside of the dust cloud, the glow low on the horizon only at a grazing look
          float graze = 1.0 - max(dot(nw, V), 0.0);
          vec3 sky = fogC * (0.15 + 0.6 * keyI) * mix(0.35, 1.0, pow(graze, 6.0)) + vec3(0.6, 0.7, 1.0) * flash * 0.6;
          // the melt and the glowing cloud mirrored on the water: a long broken path of light toward us
          vec3 Hm = normalize(L + V); float hm = max(dot(nw, Hm), 0.0);
          float spec = (pow(hm, 120.0) * 6.0 + pow(hm, 20.0) * 0.6) * meltI / (1.0 + pow(dl / 160.0, 2.0));
          col = wc * (Lk + amb * 3.0 + 0.05) + sky * fr * 0.9 + vec3(1.0, 0.55, 0.2) * spec * 2.0;
          float foam = smoothstep(-0.06, 0.0, vH) * (0.5 + 0.5 * wv) * (1.0 - vWet) + smoothstep(0.7, 0.85, wv) * 0.08;
          // flooding in: churned and muddy, white where it pours and boils against the hot rock and the melt
          if (inner > 0.5) foam += 0.25 + 0.45 * smoothstep(0.55, 0.8, wv) + 0.6 * (1.0 - smoothstep(30.0, 45.0, r));
          if (Aw > 0.0) {
            // the wave: white water on its crest and streaked down its face, the glow behind showing through the crest
            float x = r - Rw;
            float crest = exp(-pow((x + 0.6) / 1.8, 2.0)), face = smoothstep(-1.0, 3.0, x) * (1.0 - smoothstep(3.0, 7.0, x));
            float streak = smoothstep(0.35, 0.8, cf(vec2(atan(vP.y, vP.x) * 70.0, x * 0.6)) * 0.5 + 0.5);
            float toe = exp(-pow((x - 4.0) / 2.5, 2.0)) * (0.6 + 0.4 * cf(vP * 0.7 + vt));      // white water at its foot
            foam += crest * 0.9 + face * streak * 0.3 + toe * 0.7;
            col += vec3(1.0, 0.45, 0.12) * meltI * crest * 0.25 / (1.0 + pow(dl / 120.0, 2.0));
          }
          col = mix(col, vec3(0.62, 0.58, 0.54) * (Lm + Lk + amb * 5.0 + Lf + 0.04), clamp(foam, 0.0, 1.0) * 0.85);
        }
        // melt: the floor of the bowl at first, then the low ground of the final crater (the middle and the trough), the
        // peak ring standing out of it; a churning, glowing surface
        float lowf = 1.0 - smoothstep(-1.15, -0.75, vH);
        float mz = mix(1.0 - smoothstep(0.0, 0.5, r / (50.0 * sqrt(g) + 1.0)), lowf * (1.0 - smoothstep(48.0, 60.0, r)), coll);
        float tb = cf(vP * 0.08 + 5.0 + vt * 0.05) * 0.5 + 0.5, tf = cf(vP * 0.5 - 3.0 - vt * 0.2) * 0.5 + 0.5;
        float crust = smoothstep(0.35, 0.7, cf(vP * 0.18 + 1.0 + vt * 0.03) * 0.5 + 0.5) * smoothstep(200.0, 600.0, T);
        float hot = melt * mz * (0.4 + 0.6 * tb) * (0.75 + 0.5 * tf) * (1.0 - 0.7 * crust) * (vWet > 0.5 ? 0.22 : 1.0);   // under water: a dull glow
        col = mix(col, col * 0.25, mz);
        col += hot * mix(vec3(0.6, 0.07, 0.01), vec3(1.0, 0.55, 0.12), tb * tf) * 1.4;
        // dust in the air: the far ground sinks into the glowing haze, thicker low down
        float dist = length(cameraPosition - vW) * 1000.0;
        vec3 fc = fogC * (0.5 + keyI * 0.7) + vec3(0.5, 0.55, 0.7) * flash * 0.4;
        col = mix(col, fc, 1.0 - exp(-dist * fogK));
        col = vec3(1.0) - exp(-col * 1.7);
        if (dbg > 0.5) col = water ? vec3(0.0, 0.3, 1.0) * (0.5 + 0.5 * fract(r / 20.0)) : vec3(1.0, 0.2, 0.0) * (0.5 + 0.5 * fract(r / 20.0));   // check: water blue, land red
        gl_FragColor = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
      }` }));
  crater.frustumCulled = false; crater.visible = false; scene.add(crater);
  // the sky over the crater: the underside of the dust cloud, glowing from below near the horizon, dark and lumpy
  // overhead, lit up now and then by lightning (flash: direction, strength)
  const SKY = { up: CU.eU, fogC: CU.fogC, keyI: CU.keyI, vt: CU.vt, fl: { value: new T.Vector4(0, 1, 0, 0) } };
  const skydome = new T.Mesh(new T.SphereGeometry(1, 64, 32), new T.ShaderMaterial({ uniforms: SKY, side: T.BackSide,
    depthWrite: false, depthTest: false,
    vertexShader: 'varying vec3 vD; void main() { vD = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 up, fogC; uniform float keyI, vt; uniform vec4 fl; varying vec3 vD;
      float h3(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
      float vn(vec3 p) { vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z); }
      void main() {
        vec3 d = normalize(vD); float el = dot(d, up);
        float b = 0.5 * vn(d * 5.0 + vt * 0.04) + 0.3 * vn(d * 13.0 - vt * 0.06) + 0.2 * vn(d * 31.0);
        vec3 hor = fogC * (0.5 + keyI * 0.7);
        vec3 c = mix(hor * vec3(1.2, 0.9, 0.7), vec3(0.004, 0.003, 0.002), smoothstep(-0.03, 0.12, el)) * (0.35 + 1.3 * b);
        float fa = max(dot(d, normalize(fl.xyz)), 0.0);
        c += vec3(0.75, 0.8, 1.0) * fl.w * (0.15 * b + 1.2 * pow(fa, 40.0) + 0.3 * pow(fa, 6.0));
        c = vec3(1.0) - exp(-c * 1.7);
        gl_FragColor = vec4(pow(c, vec3(1.0 / 2.2)), 1.0);
      }` }));
  skydome.renderOrder = -10; skydome.visible = false; skydome.scale.setScalar(2); scene.add(skydome);

  // ---- meteors: the ejecta coming back into the air, each a streak — a white-hot head, a tail cooling through orange
  // to deep red — drawn on the GPU from its birth time (like fx(), any frame stands alone). On the screen at least
  // ~1.6 px wide, so far ones still show as sparks; dimmer the farther off (ref: the distance at which gain is as set).
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
          // a meteor brightens as it plunges into thicker air, then burns out
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

  window.X = { T, D, W, H, ER, renderer, scene, camera, earth, halo, U, asteroid, AU, stars, dirLL, fx, head, rnd, dome, crater, CU, skydome, SKY, streaks };
  window.WORLD_READY = 1;

  window.startShot = async (name) => {
    const s = window.SHOTS[name]; earth.visible = halo.visible = true; asteroid.visible = false; stars.visible = true;
    U.dim.value = 0; U.exposure.value = 1; AU.exposure.value = 1; AU.heat.value = 0; U.fball.value.set(0, 0, 0, 0); U.haze.value = 1; U.atm.value = 1.2; U.shock.value.set(1, 0, 0, 0); U.shock2.value.set(0, 0, 0, 0); U.hole.value.set(1, 0, 0, 0); crater.visible = false; skydome.visible = false; U.dfog.value.set(0, 0, 0, 0); U.tsu.value.set(1, 0, 0, 0); U.tsu2.value.set(0, 0, 0, 0); U.fire.value.set(1, 0, 0, 0); U.fire2.value.set(0, 0, 0, 0); U.dark.value.set(1, 0, 0, 0); U.dark2.value.set(0, 0, 0, 0);
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
