// Небозвід — surface and atmosphere effects: Earth, Mars, Venus, Titan, Io, eclipses, the giants, the living Sun.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

// Living Earth: shared uniforms for the surface, the cloud deck, the atmosphere and the aurora.
// Clouds are two drifting copies of one map blended with a slowly moving weight, so they change shape without new textures.
const earthU = {
  time: { value: 0 },
  drift: { value: new THREE.Vector2(0, 0.37) },
  cloudOpacity: { value: 0.85 },
  sunPos: { value: new THREE.Vector3(0, 0, 0) },
};
const CLOUDS_GLSL = `
  uniform sampler2D cloudMap; uniform vec2 drift; uniform float time;
  float cloudAt(vec2 uv) {
    float a = texture2D(cloudMap, vec2(uv.x - drift.x, uv.y)).r;
    float b = texture2D(cloudMap, vec2(uv.x - drift.y, 1.0 - uv.y * 0.985 - 0.0075)).r;
    float w = 0.5 + 0.5 * sin(time * 0.045 + uv.x * 18.85 + uv.y * 9.0);
    return clamp(mix(a, b, w) * 1.15, 0.0, 1.0);
  }
`;
const EARTH_VERT = `
  varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
  void main() {
    vUv = uv; vObj = normalize(position);
    vN = normalize(mat3(modelMatrix) * normal);
    vec4 w = modelMatrix * vec4(position, 1.0);
    vW = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;

function earthMaterial(tex) {
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({
      dayMap: { value: tex.earth }, nightMap: { value: tex.earthNight }, specMap: { value: tex.earthSpec }, cloudMap: { value: tex.earthClouds },
    }, earthU, detailU),
    vertexShader: EARTH_VERT,
    fragmentShader: NOISE_GLSL + CLOUDS_GLSL + SOLAR_GLSL + `
      uniform sampler2D dayMap; uniform sampler2D nightMap; uniform sampler2D specMap; uniform vec3 sunPos;
      uniform sampler2D detailMap; uniform vec4 detailBox; uniform float detailMix;
      uniform sampler2D nightDetailMap; uniform vec4 nightBox; uniform float nightMix;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      // Weight of a streamed patch at this point: 0 outside its box, fading out towards the box edges.
      float patchWeight(vec4 box, float mixv, out vec2 d) {
        d = vec2(fract(vUv.x - box.x) / box.z, (vUv.y - box.y) / box.w);
        vec2 edge = min(d, 1.0 - d);
        return mixv * smoothstep(0.0, 0.06, min(edge.x, edge.y));
      }
      void main() {
        vec3 N = normalize(vN);
        vec3 L = normalize(sunPos - vW);
        vec3 V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);
        float mu = clamp(dot(N, V), 0.0, 1.0);
        vec3 day = pow(texture2D(dayMap, vUv).rgb, vec3(2.2));
        vec3 night = pow(texture2D(nightMap, vUv).rgb, vec3(2.2));
        // Blurred mask (mip bias) so JPEG blocks and hard coastlines don't show under the glint.
        float ocean = smoothstep(0.35, 0.85, texture2D(specMap, vUv, 2.0).r);
        // Detailed patches around the point under the camera (streamed in). Water on the day patch is one flat ocean
        // tone, so it doubles as a sharp water mask for the Sun's glint.
        vec2 d;
        float w = detailMix > 0.0 ? patchWeight(detailBox, detailMix, d) : 0.0;
        if (w > 0.0) {
          vec3 t = texture2D(detailMap, d).rgb;
          day = mix(day, pow(t, vec3(2.2)), w);
          ocean = mix(ocean, smoothstep(0.05, 0.1, t.b - max(t.r, t.g)), w);
        }
        float wn = nightMix > 0.0 ? patchWeight(nightBox, nightMix, d) : 0.0;
        if (wn > 0.0) night = mix(night, pow(texture2D(nightDetailMap, d).rgb, vec3(2.2)), wn);
        // Solar eclipse: the Moon's shadow dims the daylight.
        // Perceptual curve: the screen is non-linear, so a linear dimming would barely show.
        float eclipseLit = pow(1.0 - solarShadow(N), 2.2);
        float lit = smoothstep(-0.08, 0.25, ndl) * eclipseLit;

        // Cloud shadows on the ground (sampled a little towards the Sun).
        vec2 sh = vec2(-dot(L, cross(vec3(0.0, 1.0, 0.0), N)) * 0.0015, 0.0);
        float shadow = cloudAt(vUv + sh) * 0.45 * lit;

        // Warm light near the day–night line.
        vec3 sunTint = mix(vec3(1.0, 0.55, 0.32), vec3(1.0), smoothstep(0.0, 0.28, ndl));
        vec3 col = day * (0.03 + 1.25 * max(ndl, 0.0) * eclipseLit) * sunTint * (1.0 - shadow);
        col += night * vec3(1.0, 0.8, 0.55) * 2.2 * (1.0 - smoothstep(-0.2, 0.08, ndl)) * (1.0 - cloudAt(vUv) * 0.7);

        // Sun glint on the sea, shimmering as if on waves.
        vec3 H = normalize(L + V);
        float waves = 0.82 + 0.18 * snoise(vObj * 70.0 + vec3(0.0, time * 0.25, time * 0.18));
        float glint = pow(max(dot(N, H), 0.0), 260.0) * 0.45 + pow(max(dot(N, H), 0.0), 1400.0) * 0.35;
        col += vec3(1.0, 0.92, 0.78) * glint * ocean * 0.16 * waves * lit * (1.0 - shadow);

        // Blue haze of the atmosphere towards the edge of the day side.
        col += vec3(0.18, 0.38, 0.85) * pow(1.0 - mu, 2.5) * lit * 0.55;
        gl_FragColor = vec4(col, 1.0);
        #include <encodings_fragment>
      }`,
  });
}

/* ---------- Detailed Earth ---------- */
// NASA Blue Marble cut into a pyramid of 2048 px chunks (planetarium/tools/earth_detail.py): level 1 ≈ 4.9 km per pixel,
// level 2 ≈ 2.4 km, level 3 ≈ 1.2 km, level 4 ≈ 600 m (land only), plus Black Marble city lights on the level-3 grid.
// As the camera nears the Earth, the chunks around the point below it are drawn into a canvas texture (one for the day,
// one for the night) that the surface shader blends over the base maps. Each patch is centred under the camera and
// follows it in quarter-chunk steps; it spans 2 × 2 chunks, or one in economy mode (phones), to stay at 2048 px there.
const detailU = {
  detailMap: { value: null }, detailBox: { value: new THREE.Vector4(0, 0, 1, 1) }, detailMix: { value: 0 },
  nightDetailMap: { value: null }, nightBox: { value: new THREE.Vector4(0, 0, 1, 1) }, nightMix: { value: 0 },
};
const DETAIL_GRID = { 1: [4, 2], 2: [8, 4], 3: [16, 8], 4: [32, 16], n3: [16, 8] };
const detailImages = new Map();
function detailImage(dir, x, y) {
  const k = `${dir}/${x}_${y}`;
  let e = detailImages.get(k);
  if (!e) {
    e = { img: new Image(), ready: false, failed: false };
    // Decode off the main thread before use, so drawing the patch doesn't stall a frame.
    e.img.onload = () => { (e.img.decode ? e.img.decode() : Promise.resolve()).catch(() => {}).then(() => { e.ready = true; }); };
    e.img.onerror = () => { e.failed = true; };          // e.g. open ocean on level 4: the level below is used
    e.img.src = `textures/earth/${k}.jpg`;
    detailImages.set(k, e);
  } else { detailImages.delete(k); detailImages.set(k, e); }   // most recently used last
  if (detailImages.size > 24) for (const [kk, ee] of detailImages) { if (ee.ready) { detailImages.delete(kk); break; } }   // missing chunks stay remembered
  return e;
}
const patches = {
  day: { key: "", dir: "", canvas: null, ctx: null, tex: null, map: detailU.detailMap, box: detailU.detailBox },
  night: { key: "", dir: "", canvas: null, ctx: null, tex: null, map: detailU.nightDetailMap, box: detailU.nightBox },
};
// Bring patch P to the chunks of `dir` around map point (u, v). Returns "same", "new", "loading" or "failed".
function drawPatch(P, dir, u, v, span, maxSize) {
  const [nx, ny] = DETAIL_GRID[dir], q = 0.25;
  // Stay put while the point under the camera is near the patch centre: moving means redrawing and re-uploading a big
  // texture, so small camera movements (and the damped controls settling) must not make the patch jump back and forth.
  if (P.dir === dir && P.span === span) {
    const dx = ((u * nx - (P.ox + span / 2)) % nx + nx * 1.5) % nx - nx / 2;
    const dy = v * ny - (P.oy + span / 2);
    const atPole = (dy < 0 && P.oy === 0) || (dy > 0 && P.oy === ny - span);
    if (Math.abs(dx) < 0.3 * span && (Math.abs(dy) < 0.3 * span || atPole)) return "same";
  }
  const ox = Math.round((u * nx - span / 2) / q) * q;
  const oy = Math.max(0, Math.min(ny - span, Math.round((v * ny - span / 2) / q) * q));
  const key = `${dir}:${ox}:${oy}:${span}`;
  if (key === P.key) return "same";
  const parts = [];
  for (let cy = Math.floor(oy); cy < oy + span; cy++)
    for (let cx = Math.floor(ox); cx < ox + span; cx++) parts.push({ cx, cy, e: detailImage(dir, ((cx % nx) + nx) % nx, cy) });
  if (parts.some(p => p.e.failed)) return "failed";
  if (!parts.every(p => p.e.ready)) return "loading";
  const size = Math.min(2048 * span, maxSize, renderer.capabilities.maxTextureSize);
  if (!P.canvas || P.canvas.width !== size) {
    if (P.tex) P.tex.dispose();
    P.canvas = document.createElement("canvas");
    P.canvas.width = P.canvas.height = size;
    P.ctx = P.canvas.getContext("2d");
    P.tex = new THREE.CanvasTexture(P.canvas);
    P.tex.encoding = THREE.sRGBEncoding;
    // No mipmaps: the level is chosen to match the screen, and rebuilding them on every update is what stalls phones.
    P.tex.generateMipmaps = false;
    P.tex.minFilter = THREE.LinearFilter;
    P.map.value = P.tex;
  }
  const h = size / span;
  for (const p of parts) P.ctx.drawImage(p.e.img, (p.cx - ox) * h, (p.cy - oy) * h, h, h);
  P.tex.needsUpdate = true;
  P.key = key; P.dir = dir; P.ox = ox; P.oy = oy; P.span = span;
  P.box.value.set((((ox % nx) + nx) % nx) / nx, 1 - (oy + span) / ny, span / nx, span / ny);
  return "new";
}
function updateEarthDetail() {
  const E = byId.earth;
  let dayOn = false, nightOn = false;
  if (E.mesh) {
    // Height above the surface (Earth radii) → the level whose pixels match the screen.
    const alt = camera.position.distanceTo(E.world) / E.radius - 1;
    const need = innerHeight * renderer.getPixelRatio() / (2 * Math.tan(camera.fov * DEG / 2) * Math.max(alt, 0.01));
    const level = need > 6200 ? 4 : need > 3100 ? 3 : need > 1550 ? 2 : need > 780 ? 1 : 0;
    // Only while the Earth is in view (from the Moon it can be close behind the camera).
    if (level && discOf("earth").inView) {
      // Map position of the point under the camera (v counted from the north pole).
      const l = tmp.copy(camera.position).sub(E.world).applyQuaternion(tmpQ.copy(E.mesh.getWorldQuaternion(tmpQ)).invert()).normalize();
      const u = (Math.atan2(-l.z, l.x) / TAU + 1.5) % 1, v = 0.5 - Math.asin(Math.max(-1, Math.min(1, l.y))) / PI;
      const span = eco ? 1 : 2;
      // Finest level first; where its chunks don't exist (open ocean on level 4), the next one down.
      let r = "";
      for (let lv = level; lv >= 1; lv--) if ((r = drawPatch(patches.day, String(lv), u, v, span, 4096)) !== "failed") break;
      dayOn = !!patches.day.key;                           // keep the current patch while the next one loads
      // City lights: only when the night side is below (the patch reaches ~22° around the point), never in the same
      // frame as a day update, and in a smaller texture (lights don't need more).
      const sunUp = tmp2.copy(camera.position).sub(E.world).normalize().dot(tA.copy(E.world).negate().normalize());
      if (level >= 2 && sunUp < 0.5 && r !== "new") {
        if (drawPatch(patches.night, "n3", u, v, span, 2048) !== "failed") nightOn = !!patches.night.key;
      } else nightOn = level >= 2 && sunUp < 0.5 && !!patches.night.key;
    }
  }
  for (const [m, on] of [[detailU.detailMix, dayOn], [detailU.nightMix, nightOn]]) {
    m.value += ((on ? 1 : 0) - m.value) * 0.08;
    if (m.value < 0.002) m.value = 0;
  }
}

function earthCloudMaterial(tex) {
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({ cloudMap: { value: tex.earthClouds } }, earthU),
    vertexShader: EARTH_VERT,
    fragmentShader: CLOUDS_GLSL + SOLAR_GLSL + `
      uniform vec3 sunPos; uniform float cloudOpacity;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      void main() {
        vec3 N = normalize(vN);
        vec3 L = normalize(sunPos - vW);
        float ndl = dot(N, L);
        float c = cloudAt(vUv);
        vec3 tint = mix(vec3(1.0, 0.5, 0.28), vec3(1.0), smoothstep(0.0, 0.3, ndl));
        vec3 col = tint * (0.03 + 1.1 * max(ndl, 0.0) * pow(1.0 - solarShadow(N), 2.2));
        float night = 1.0 - smoothstep(-0.15, 0.05, ndl);

        // Lightning: rare flickering flashes inside thick clouds on the night side, mostly in the tropics.
        vec2 g = vUv * vec2(110.0, 55.0);
        vec2 cell = floor(g), f = fract(g) - 0.5;
        float h = hash(cell);
        float t = time * (0.7 + h) + h * 50.0;
        float beat = hash(cell + floor(t));
        float flash = step(0.965, beat) * exp(-fract(t) * 5.0) * (0.55 + 0.45 * sin(fract(t) * 55.0)) * exp(-dot(f, f) * 9.0);
        float storms = smoothstep(0.22, 0.45, c) * (1.0 - smoothstep(0.4, 0.65, abs(vObj.y)));
        col += vec3(0.75, 0.82, 1.0) * flash * storms * night * 4.0;

        float bolt = flash * storms * night;
        gl_FragColor = vec4(col, clamp(c * cloudOpacity + bolt * 1.6, 0.0, 1.0));
        #include <encodings_fragment>
      }`,
    transparent: true, depthWrite: false,
  });
}

// Atmosphere shell that knows where the Sun is: blue on the day side, orange-red at sunrise and sunset, nothing at night.
function earthAtmosphere(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 96, 64), new THREE.ShaderMaterial({
    uniforms: { sunPos: earthU.sunPos },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);
        float rim = pow(1.0 - abs(dot(N, V)), 3.0);
        float dayside = smoothstep(-0.3, 0.25, ndl);
        vec3 col = mix(vec3(1.0, 0.42, 0.15), vec3(0.3, 0.58, 1.0), smoothstep(-0.05, 0.3, ndl));
        gl_FragColor = vec4(col, rim * dayside * 1.3);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}

// Mercury: no atmosphere, so no scattered light — the night is black, the terminator sharp, and low sunlight
// throws long crater shadows. Relief comes from the map's brightness via screen-space bump mapping.
function mercuryMaterial(tex) {
  return new THREE.ShaderMaterial({
    uniforms: { map: { value: tex.mercury }, sunPos: earthU.sunPos, bump: { value: 0.02 } },
    extensions: { derivatives: true },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform sampler2D map; uniform vec3 sunPos; uniform float bump;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW);
        vec3 albedo = pow(texture2D(map, vUv).rgb, vec3(2.2));
        float h = dot(albedo, vec3(0.3, 0.59, 0.11));
        vec3 dpdx = dFdx(vW), dpdy = dFdy(vW);
        float hx = dFdx(h), hy = dFdy(h);
        vec3 r1 = cross(dpdy, N), r2 = cross(N, dpdx);
        float det = dot(dpdx, r1);
        vec3 Nb = normalize(abs(det) * N - sign(det) * (hx * r1 + hy * r2) * bump);
        float ndl = max(dot(Nb, L), 0.0) * smoothstep(-0.02, 0.02, dot(N, L));
        gl_FragColor = vec4(albedo * (0.004 + 1.3 * ndl), 1.0);
        #include <encodings_fragment>
      }`,
  });
}

// Sun-aware haze for thick atmospheres: dayCol on the lit limb, edgeCol towards the terminator, dark at night.
function hazeAtmosphere(radius, dayCol, edgeCol, strength) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 96, 64), new THREE.ShaderMaterial({
    uniforms: { sunPos: earthU.sunPos, dayCol: { value: new THREE.Vector3(...dayCol) }, edgeCol: { value: new THREE.Vector3(...edgeCol) }, k: { value: strength } },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos; uniform vec3 dayCol; uniform vec3 edgeCol; uniform float k;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);
        float rim = pow(1.0 - abs(dot(N, V)), 3.0);
        vec3 col = mix(edgeCol, dayCol, smoothstep(-0.05, 0.3, ndl));
        gl_FragColor = vec4(col, rim * smoothstep(-0.3, 0.2, ndl) * k);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}

// Aurora: waving green-violet curtains around both poles, visible on the night side.
function earthAurora(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 128, 64), new THREE.ShaderMaterial({
    uniforms: { sunPos: earthU.sunPos, time: earthU.time },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos; uniform float time;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float lat = asin(clamp(vObj.y, -1.0, 1.0));
        float lon = atan(vObj.z, vObj.x);
        float wave = 0.045 * sin(lon * 5.0 + time * 0.25) + 0.02 * sin(lon * 11.0 - time * 0.4);
        float band = exp(-pow((abs(lat) - 1.16 + wave) / 0.045, 2.0));
        float rays = 0.45 + 0.55 * pow(0.5 + 0.5 * sin(lon * 60.0 + time * 1.2 + 3.0 * sin(lon * 7.0 + time * 0.35)), 2.0);
        float pulse = 0.75 + 0.25 * sin(time * 0.6 + lon * 3.0);
        float night = 1.0 - smoothstep(-0.25, 0.05, dot(N, L));
        float edge = 0.4 + 1.6 * pow(1.0 - abs(dot(N, V)), 2.0);
        vec3 col = mix(vec3(0.15, 1.0, 0.45), vec3(0.65, 0.3, 1.0), smoothstep(0.0, 1.0, pow(1.0 - band, 3.0)));
        gl_FragColor = vec4(col, band * rays * pulse * night * edge * 0.9);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}

// Mars weather, kept deliberately subtle: dust storms, water-ice clouds, seasonal CO2 frost, a thin atmosphere and patchy aurora.
// ls = areocentric solar longitude (Mars season, rad) from the real date; globalDust = 0..1 inside known planet-wide storms.
const marsU = {
  time: { value: 0 },
  flow: { value: 0 },
  ls: { value: 0 },
  globalDust: { value: 0 },
  sunPos: { value: new THREE.Vector3(0, 0, 0) },
};
// Planet-wide dust storms observed from orbit or the ground (approximate start/end, UTC).
const GLOBAL_DUST = [["1971-09-22", "1972-01-10"], ["1977-02-15", "1977-04-10"], ["1977-05-25", "1977-08-01"], ["2001-06-20", "2001-10-15"], ["2007-06-20", "2007-09-15"], ["2018-05-30", "2018-09-15"]].map(([a, b]) => [Date.parse(a), Date.parse(b)]);
function globalDustAt(ms) {
  const ramp = 20 * 86400000;
  let v = 0;
  for (const [a, b] of GLOBAL_DUST) {
    if (ms > a - ramp && ms < b + ramp) v = Math.max(v, Math.min(1, (ms - a + ramp) / ramp, (b + ramp - ms) / ramp));
  }
  return clamp01(v);
}
// Mars season from its heliocentric ecliptic longitude: Ls ≈ λ − 85.06°.
function marsLs(auVec) {
  const lambda = Math.atan2(-auVec.z, auVec.x) / DEG;
  return (((lambda - 85.06) % 360) + 360) % 360;
}

function marsWeather(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 96, 64), new THREE.ShaderMaterial({
    uniforms: marsU,
    vertexShader: EARTH_VERT,
    fragmentShader: NOISE_GLSL + `
      uniform float time; uniform float flow; uniform float ls; uniform float globalDust; uniform vec3 sunPos;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      // Gaussian bump around a surface point given as (lat, east longitude) in degrees.
      float spot(float lat, float lon, float cLat, float cLon, float sLat, float sLon) {
        float dl = mod(lon - cLon + 540.0, 360.0) - 180.0;
        return exp(-pow((lat - cLat) / sLat, 2.0) - pow(dl / sLon, 2.0));
      }
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW);
        float ndl = dot(N, L);
        vec3 p = normalize(vObj);
        float lat = degrees(asin(clamp(p.y, -1.0, 1.0)));
        float lon = degrees(atan(-p.z, p.x));
        float s = sin(ls);

        // Dust: more storms in southern spring/summer (Ls ≈ 180–330), plus rare planet-wide events.
        float season = exp(-pow((degrees(ls) - 255.0) / 55.0, 2.0));
        vec3 q = p * 2.6 + vec3(flow, 0.0, flow * 0.6);
        #ifdef ECO
          float n = fbm(q) * 0.5 + 0.5;
        #else
          float n = fbm(q + fbm(q * 1.7 + 3.1) * 0.8) * 0.5 + 0.5;
        #endif
        float local = smoothstep(0.78 - season * 0.1, 0.95, n) * (0.28 + 0.2 * season);
        float dust = max(local, globalDust * (0.55 + 0.2 * n));

        // Water-ice clouds: the aphelion equatorial belt (Ls ≈ 40–140), clouds over the Tharsis volcanoes, winter polar hoods.
        float wisps = fbm(p * 7.0 + vec3(0.0, flow * 1.3, 0.0)) * 0.5 + 0.5;
        float belt = exp(-pow((degrees(ls) - 90.0) / 45.0, 2.0)) * exp(-pow((lat - 10.0) / 14.0, 2.0)) * smoothstep(0.5, 0.8, wisps) * 0.22;
        float volcanoes = spot(lat, lon, 18.6, 226.2, 5.0, 9.0) + spot(lat, lon, -8.3, 239.9, 4.0, 8.0) + spot(lat, lon, 1.5, 247.0, 4.0, 7.0) + spot(lat, lon, 11.9, 255.5, 4.0, 7.0);
        float oro = volcanoes * smoothstep(0.35, 0.75, wisps) * 0.35 * (0.5 + 0.5 * exp(-pow((degrees(ls) - 90.0) / 60.0, 2.0)));
        float winterN = max(0.0, -s), winterS = max(0.0, s);
        float hood = (smoothstep(48.0, 62.0, lat) * winterN + smoothstep(48.0, 62.0, -lat) * winterS) * smoothstep(0.45, 0.75, wisps) * 0.25;
        float ice = max(max(belt, oro), hood);

        // Seasonal CO2 frost reaching lower latitudes in the winter hemisphere.
        float ragged = snoise(p * 9.0) * 3.0;
        float frost = (smoothstep(88.0 - 30.0 * winterN, 92.0 - 30.0 * winterN, lat + ragged) * winterN
                     + smoothstep(88.0 - 30.0 * winterS, 92.0 - 30.0 * winterS, -lat + ragged) * winterS) * 0.33;

        float light = 0.04 + 1.05 * max(ndl, 0.0);
        // Composite back to front (premultiplied): frost, dust, ice clouds.
        vec3 pc = vec3(0.95, 0.95, 0.97) * frost; float a = frost;
        pc = vec3(0.78, 0.52, 0.32) * dust + pc * (1.0 - dust); a = dust + a * (1.0 - dust);
        pc = vec3(0.97, 0.97, 1.0) * ice + pc * (1.0 - ice); a = ice + a * (1.0 - ice);
        pc *= light;

        // Aurora: faint, patchy glow over the crustal magnetic fields of the southern highlands, on the night side, coming and going.
        float night = 1.0 - smoothstep(-0.2, 0.02, ndl);
        float crust = spot(lat, lon, -48.0, 180.0, 20.0, 45.0);
        float flicker = smoothstep(0.1, 0.9, 0.5 + 0.5 * sin(time * 0.07)) * (0.6 + 0.4 * snoise(p * 12.0 + time * 0.1));
        float aur = crust * night * flicker * smoothstep(0.2, 0.7, snoise(p * 6.0 - time * 0.03) * 0.5 + 0.5) * 0.35;
        pc += vec3(0.25, 0.95, 0.5) * aur;
        a = max(a, aur);

        gl_FragColor = vec4(pc / max(a, 0.001), clamp(a, 0.0, 0.8));
        #include <encodings_fragment>
      }`,
    transparent: true, depthWrite: false,
  }));
}

// Thin atmosphere: pale butterscotch haze on the day limb, a blue tint along the terminator (Martian sunsets are blue).
function marsAtmosphere(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 96, 64), new THREE.ShaderMaterial({
    uniforms: { sunPos: marsU.sunPos, globalDust: marsU.globalDust },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos; uniform float globalDust;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);
        float rim = pow(1.0 - abs(dot(N, V)), 3.2);
        float dayside = smoothstep(-0.25, 0.2, ndl);
        vec3 col = mix(vec3(0.35, 0.55, 1.0), vec3(0.95, 0.68, 0.45), smoothstep(-0.05, 0.3, ndl));
        gl_FragColor = vec4(col, rim * dayside * (0.55 + globalDust * 0.4));
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}

// Venus: super-rotating cloud deck, light wrapping past the terminator through the thick atmosphere,
// a faint infrared glow of the hot surface on the night side, and an optional Magellan radar view of the surface.
const venusU = {
  time: { value: 0 },
  drift: { value: new THREE.Vector2(0, 0.41) },
  surface: { value: 0 },
  surfMap: { value: null },
  sunPos: { value: new THREE.Vector3(0, 0, 0) },
};
function venusMaterial(tex) {
  tex.venus.wrapS = THREE.RepeatWrapping;
  tex.venus.needsUpdate = true;
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({ cloudMap: { value: tex.venus } }, venusU),
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform sampler2D cloudMap; uniform sampler2D surfMap; uniform vec2 drift; uniform float time; uniform float surface; uniform vec3 sunPos;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);

        // Clouds: two copies drifting at slightly different rates, blended with a slowly moving weight.
        vec3 a = pow(texture2D(cloudMap, vec2(vUv.x + drift.x, vUv.y)).rgb, vec3(2.2));
        vec3 b = pow(texture2D(cloudMap, vec2(vUv.x + drift.y, vUv.y)).rgb, vec3(2.2));
        float w = 0.5 + 0.5 * sin(time * 0.04 + vUv.x * 12.566 + vUv.y * 6.0);
        vec3 clouds = mix(a, b, w);

        // Thick atmosphere scatters light well past the terminator; it warms towards the edge of the day.
        float wrap = clamp((ndl + 0.12) / 1.12, 0.0, 1.0);
        vec3 tint = mix(vec3(1.0, 0.72, 0.42), vec3(1.0), smoothstep(0.0, 0.5, ndl));
        vec3 col = clouds * (0.008 + 1.2 * pow(wrap, 1.6)) * tint;

        // Night side: the ~464 °C surface glows in the near infrared; thick clouds show as dark silhouettes.
        float night = 1.0 - smoothstep(-0.25, 0.05, ndl);
        float thick = smoothstep(0.25, 0.75, dot(clouds, vec3(0.3, 0.55, 0.15)) * 1.6);
        col += vec3(0.5, 0.1, 0.025) * (1.0 - thick) * night * 0.06;

        // Radar view (Magellan): the surface under the clouds, lit plainly.
        if (surface > 0.001) {
          vec3 ground = pow(texture2D(surfMap, vUv).rgb, vec3(2.2)) * (0.04 + 1.15 * max(ndl, 0.0));
          col = mix(col, ground, surface);
        }
        gl_FragColor = vec4(col, 1.0);
        #include <encodings_fragment>
      }`,
  });
}
// Yellowish haze on the day limb that fades slowly into the night.
function venusAtmosphere(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 96, 64), new THREE.ShaderMaterial({
    uniforms: { sunPos: venusU.sunPos, surface: venusU.surface },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos; uniform float surface;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L);
        float rim = pow(1.0 - abs(dot(N, V)), 2.4);
        float dayside = smoothstep(-0.45, 0.2, ndl);
        vec3 col = mix(vec3(1.0, 0.55, 0.25), vec3(1.0, 0.86, 0.6), smoothstep(-0.1, 0.4, ndl));
        gl_FragColor = vec4(col, rim * dayside * 0.9 * (1.0 - 0.6 * surface));
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}
/* ---------- Titan: the orange smog and what lies under it ---------- */
// In visible light Titan is a smooth orange ball: the haze hides the ground. A detached haze layer shows as a thin blue band
// on the limb, and when the Sun is behind Titan the whole atmosphere lights up in a ring. "Look under the haze" fades in the
// Cassini VIMS/ISS infrared map (Seignovert et al. 2019), with the northern methane seas glinting in the Sun.
const titanU = {
  surface: { value: 0 },
  surfMap: { value: null },
  lakeMap: { value: null },
  sunPos: { value: new THREE.Vector3(0, 0, 0) },
};
function titanMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: titanU,
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform sampler2D surfMap; uniform sampler2D lakeMap; uniform float surface; uniform vec3 sunPos;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndl = dot(N, L), ndv = max(dot(N, V), 0.0);
        float lat = vObj.y;

        // Haze: warm orange, a touch darker and browner towards the north (the seasonal hemispheric contrast),
        // faint broad banding, light wrapping well past the terminator, mild darkening towards the limb.
        vec3 haze = vec3(0.78, 0.43, 0.13);
        haze *= 1.0 - 0.1 * smoothstep(0.1, 0.9, lat) + 0.03 * sin(lat * 9.0);
        haze = mix(haze, vec3(0.62, 0.36, 0.14), 0.35 * smoothstep(0.75, 0.95, lat));
        float wrap = clamp((ndl + 0.18) / 1.18, 0.0, 1.0);
        vec3 col = haze * (0.004 + 1.15 * pow(wrap, 1.5)) * (0.72 + 0.28 * pow(ndv, 0.35));

        // Under the haze: the infrared map lit plainly, seas dark and glassy with the Sun's glint on them.
        if (surface > 0.001) {
          vec3 ground = pow(texture2D(surfMap, vUv).rgb, vec3(1.7));   // the published map is pale; deepen it
          float lake = texture2D(lakeMap, vUv).r;
          ground = mix(ground, vec3(0.03, 0.035, 0.05), lake * 0.85);
          vec3 lit = ground * (0.03 + 1.1 * max(ndl, 0.0));
          vec3 H = normalize(L + V);
          float nh = max(dot(N, H), 0.0);
          float glint = (pow(nh, 900.0) * 6.0 + pow(nh, 60.0) * 0.25) * lake * step(0.0, ndl);
          lit += vec3(1.0, 0.86, 0.62) * glint;
          col = mix(col, lit, surface * 0.9);
        }
        gl_FragColor = vec4(col, 1.0);
        #include <encodings_fragment>
      }`,
  });
}
// Titan's tall atmosphere, drawn on a shell 1.18× Titan's radius. For each pixel the shader finds how high above the surface
// the line of sight passes: the orange haze fades with height, a thin blue detached-haze layer sits ~350 km up (0.13 R),
// and when the Sun is behind Titan the whole ring lights up (forward scattering), as Cassini saw it backlit.
const TITAN_SHELL = 1.18;
function titanAtmosphere(radius) {
  return new THREE.Mesh(new THREE.SphereGeometry(radius * TITAN_SHELL, 128, 96), new THREE.ShaderMaterial({
    uniforms: titanU,
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform vec3 sunPos; uniform float surface;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW), V = normalize(cameraPosition - vW);
        float ndv = abs(dot(N, V));
        float x = ${TITAN_SHELL.toFixed(2)} * sqrt(max(0.0, 1.0 - ndv * ndv));   // impact parameter in Titan radii
        float h = x - 1.0;
        float orange = h > 0.0 ? exp(-h / 0.035) : 0.55 * exp(h / 0.018);
        float bz = (h - 0.13) / 0.009, blue = exp(-bz * bz);   // no pow() of a negative base: undefined in GLSL, breaks on some GPUs
        float day = smoothstep(-0.35, 0.3, dot(N, L)), dayHigh = smoothstep(-0.1, 0.35, dot(N, L));
        float back = pow(max(-dot(L, V), 0.0), 3.0);
        vec3 col = vec3(1.0, 0.6, 0.26) * orange * (day * 0.9 + back * 2.2)
                 + vec3(0.5, 0.72, 1.0) * blue * (dayHigh * 0.3 + back * 1.6);
        gl_FragColor = vec4(col * (1.0 - 0.5 * surface), 1.0);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
}
/* ---------- Surface views under the clouds (Venus radar, Titan infrared) ---------- */
// Their maps load on demand, and quietly in the background a few seconds after start so the button responds at once.
// A request that hangs is given up after 12 s and retried (up to three tries); clicks while loading are ignored.
const lazyMaps = {};
function lazyMap(file, key) {
  if (!lazyMaps[key]) {
    const attempt = n => new Promise((resolve, reject) => {
      let settled = false;
      const timer = setTimeout(() => { if (!settled) { settled = true; reject(new Error("timeout: " + file)); } }, 12000);
      loader.load("textures/" + file + (n ? "?retry=" + n : ""), t => {
        if (settled) return;
        settled = true; clearTimeout(timer);
        if (!DATA_MAPS.has(key)) t.encoding = THREE.sRGBEncoding;
        t.anisotropy = maxAniso; t.wrapS = THREE.RepeatWrapping;
        resolve(t);
      }, undefined, () => { if (!settled) { settled = true; clearTimeout(timer); reject(new Error(file)); } });
    });
    lazyMaps[key] = attempt(0).catch(() => attempt(1)).catch(() => attempt(2));
    lazyMaps[key].catch(() => { delete lazyMaps[key]; });   // after a failure, the next click starts afresh
  }
  return lazyMaps[key];
}
const SURFACES = {
  venus: {
    u: venusU, labels: ["Показати поверхню (радар Magellan)", "Сховати поверхню"], wait: "Завантажуємо радарну карту…",
    load: () => lazyMap("venus_surface.jpg", "venusSurface").then(t => { venusU.surfMap.value = t; }),
  },
  titan: {
    u: titanU, labels: ["Зазирнути під серпанок (інфрачервоний Cassini)", "Повернути серпанок"], wait: "Завантажуємо карту Cassini…",
    load: () => Promise.all([lazyMap("titan_surface.jpg", "titanSurface"), lazyMap("titan_lakes.png", "titanLakes")])
      .then(([t, l]) => { titanU.surfMap.value = t; titanU.lakeMap.value = l; }),
  },
};
for (const k in SURFACES) Object.assign(SURFACES[k], { on: false, loading: false, failed: false, target: 0 });
function surfaceLabel(sv) { return sv.loading ? sv.wait : sv.failed ? "Не вдалося завантажити карту. Спробувати ще раз" : sv.labels[sv.on ? 1 : 0]; }
// The button may be rebuilt while a map loads (switching bodies), so it is looked up by id when the text changes.
function refreshSurfaceButton(id) { const btn = document.getElementById("surface-" + id); if (btn) btn.textContent = surfaceLabel(SURFACES[id]); }
function toggleSurface(id) {
  const sv = SURFACES[id];
  if (sv.loading) return;
  sv.on = !sv.on; sv.failed = false;
  if (sv.on && !sv.ready) {
    sv.loading = true; refreshSurfaceButton(id);
    sv.load().then(() => { sv.ready = true; sv.loading = false; sv.target = sv.on ? 1 : 0; refreshSurfaceButton(id); })
      .catch(() => { sv.loading = false; sv.on = false; sv.failed = true; refreshSurfaceButton(id); });
    return;
  }
  sv.target = sv.on ? 1 : 0;
  refreshSurfaceButton(id);
}
// Background preload, unless the visitor asked the browser to save data.
function preloadSurfaces() {
  const c = navigator.connection;
  if (c && (c.saveData || /2g/.test(c.effectiveType || ""))) return;
  for (const k in SURFACES) SURFACES[k].load().then(() => { SURFACES[k].ready = true; }).catch(() => {});
}

/* ---------- Io: volcanic plumes and hot lava ---------- */
// Real vents (lat, east longitude); plume heights relative to Io's radius (1821 km). Io has almost no air,
// so the ejecta fly on ballistic arcs and fall back in an umbrella, as Voyager and Galileo saw.
const IO_PLUMES = [
  { lat: -18.7, lon: 104.7, h: 0.19, spread: 0.62, col: [0.55, 0.68, 1.0], n: 700 },   // Pele, ~350 km, faint and bluish
  { lat: 62.8, lon: -123.0, h: 0.18, spread: 0.55, col: [0.6, 0.7, 1.0], n: 600 },     // Tvashtar, ~330 km
  { lat: -1.5, lon: -153.1, h: 0.055, spread: 0.5, col: [0.95, 0.92, 0.82], n: 300 },  // Prometheus, ~100 km, dusty white
  { lat: -45.3, lon: -55.5, h: 0.045, spread: 0.45, col: [0.9, 0.88, 0.8], n: 200 },   // Masubi
];
// Hot spots that glow on the night side: Loki (the brightest), Pele, Amirani, Marduk, Tvashtar.
const IO_HOTSPOTS = [[12.6, 51.2, 1.0], [-18.7, 104.7, 0.7], [24.5, -114.7, 0.5], [-27.5, 150.3, 0.45], [62.8, -123.0, 0.55]];
// Direction on Io's sphere for a map position (u = 0.5 + east longitude / 360), matching SphereGeometry's UVs.
function ioDir(lat, lonE) {
  const phi = (0.5 + lonE / 360) * TAU, c = Math.cos(lat * DEG);
  return new THREE.Vector3(-Math.cos(phi) * c, Math.sin(lat * DEG), Math.sin(phi) * c);
}
function createIoFx(b) {
  const R = b.radius, FLIGHT = 5;            // seconds from vent back to the ground (sped up from ~20 minutes)
  const plumes = IO_PLUMES.map(pl => {
    const up = ioDir(pl.lat, pl.lon);
    const e1 = new THREE.Vector3().crossVectors(up, Math.abs(up.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize();
    const e2 = new THREE.Vector3().crossVectors(up, e1);
    const H = pl.h * R, v0 = 4 * H / FLIGHT, g = 8 * H / (FLIGHT * FLIGHT);
    const parts = [];
    for (let i = 0; i < pl.n; i++) {
      // Most ejecta leave near the edge of the cone, which gives the umbrella shape.
      const a = pl.spread * Math.sqrt(Math.random()), t = Math.random() * TAU;
      const dir = up.clone().multiplyScalar(Math.cos(a)).addScaledVector(e1, Math.sin(a) * Math.cos(t)).addScaledVector(e2, Math.sin(a) * Math.sin(t));
      parts.push({ v: dir.multiplyScalar(v0 * (0.85 + Math.random() * 0.15)), age: Math.random() * FLIGHT });
    }
    return { pl, up, vent: up.clone().multiplyScalar(R * 0.995), g, parts };
  });
  const total = plumes.reduce((s, p) => s + p.parts.length, 0);
  const pos = new Float32Array(total * 3), col = new Float32Array(total * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const soft = glowSprite("255,255,255", 1, 1).material.map;
  const points = new THREE.Points(geo, new THREE.PointsMaterial({ size: R * 0.028, sizeAttenuation: true, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, map: soft }));
  points.frustumCulled = false;
  b.mesh.add(points);

  const hotPos = new Float32Array(IO_HOTSPOTS.length * 3), hotCol = new Float32Array(IO_HOTSPOTS.length * 3);
  const hotDirs = IO_HOTSPOTS.map(([lat, lon]) => ioDir(lat, lon));
  hotDirs.forEach((d, i) => { hotPos[i * 3] = d.x * R * 1.003; hotPos[i * 3 + 1] = d.y * R * 1.003; hotPos[i * 3 + 2] = d.z * R * 1.003; });
  const hotGeo = new THREE.BufferGeometry();
  hotGeo.setAttribute("position", new THREE.BufferAttribute(hotPos, 3));
  hotGeo.setAttribute("color", new THREE.BufferAttribute(hotCol, 3));
  const hot = new THREE.Points(hotGeo, new THREE.PointsMaterial({ size: R * 0.09, sizeAttenuation: true, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, map: soft }));
  hot.frustumCulled = false;
  b.mesh.add(hot);

  const q = new THREE.Quaternion(), L = new THREE.Vector3(), n = new THREE.Vector3();
  return {
    update(dt) {
      b.mesh.getWorldQuaternion(q);
      L.copy(b.world).negate().normalize();                       // towards the Sun
      let k = 0;
      for (const p of plumes) {
        // Plumes are lit by the Sun, so they fade out over the night side.
        const lit = 0.15 + 0.85 * clamp01((n.copy(p.up).applyQuaternion(q).dot(L) + 0.25) / 0.5);
        for (const part of p.parts) {
          part.age = (part.age + dt) % FLIGHT;
          const t = part.age, f = Math.pow(Math.sin(PI * t / FLIGHT), 0.6) * lit * 0.1;
          pos[k * 3] = p.vent.x + part.v.x * t - p.up.x * 0.5 * p.g * t * t;
          pos[k * 3 + 1] = p.vent.y + part.v.y * t - p.up.y * 0.5 * p.g * t * t;
          pos[k * 3 + 2] = p.vent.z + part.v.z * t - p.up.z * 0.5 * p.g * t * t;
          col[k * 3] = p.pl.col[0] * f; col[k * 3 + 1] = p.pl.col[1] * f; col[k * 3 + 2] = p.pl.col[2] * f;
          k++;
        }
      }
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;
      // Lava glows only where it is night.
      IO_HOTSPOTS.forEach(([, , s], i) => {
        const night = clamp01((-n.copy(hotDirs[i]).applyQuaternion(q).dot(L) + 0.05) / 0.3);
        const flick = 0.85 + 0.15 * Math.sin(performance.now() * 0.003 + i * 1.7);
        hotCol[i * 3] = 1.0 * s * night * flick; hotCol[i * 3 + 1] = 0.35 * s * night * flick; hotCol[i * 3 + 2] = 0.08 * s * night * flick;
      });
      hotGeo.attributes.color.needsUpdate = true;
    },
  };
}
let ioFx = null;

/* ---------- Eclipses and shadows ---------- */
// Eclipses use the real geometry (km, then Earth radii), not the stylised scene: directions match the scene axes,
// so shadows land where and when they really do. Moon shadow on Earth → earthU; Earth shadow on the Moon → lunarU.
const KM_AU = 149597870.7, R_EARTH = 6371.0, R_MOON = 1737.4, R_SUN = 696000;
earthU.eMoon = { value: new THREE.Vector3(1e6, 0, 0) };
earthU.eAxis = { value: new THREE.Vector3(1, 0, 0) };
earthU.eCone = { value: new THREE.Vector3(0, 0, 0) };
const lunarU = {
  lmCenter: { value: new THREE.Vector3(1e6, 0, 0) },
  lAnti: { value: new THREE.Vector3(1, 0, 0) },
  lCone: { value: new THREE.Vector3(0, 0, 0) },
  sunPos: earthU.sunPos,
};
const SOLAR_GLSL = `
  uniform vec3 eMoon; uniform vec3 eAxis; uniform vec3 eCone;
  // Fraction of sunlight blocked by the Moon at surface point P (Earth radii from Earth's centre).
  float solarShadow(vec3 P) {
    vec3 v = P - eMoon;
    float al = dot(v, eAxis);
    if (al <= 0.0) return 0.0;
    float perp = length(v - al * eAxis);
    float rp = eCone.x + al * eCone.y, ru = abs(eCone.x - al * eCone.z);
    float pen = 1.0 - smoothstep(ru, rp, perp);
    float core = 1.0 - smoothstep(ru * 0.8, ru * 1.2 + 0.003, perp);
    return clamp(pen * 0.92 + core * 0.08, 0.0, 1.0);
  }
`;
// Relief from the real terrain: a normal map derived from the USGS lunar DEM (Celestia), streamed in after start.
const moonRelief = { nmap: { value: null }, nOn: { value: 0 } };
function moonMaterial(tex) {
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({ map: { value: tex.moon } }, lunarU, moonRelief),
    extensions: { derivatives: true },
    vertexShader: EARTH_VERT,
    fragmentShader: `
      uniform sampler2D map; uniform vec3 sunPos; uniform vec3 lmCenter; uniform vec3 lAnti; uniform vec3 lCone;
      uniform sampler2D nmap; uniform float nOn;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW);
        vec3 albedo = pow(texture2D(map, vUv).rgb, vec3(2.2));
        // Terrain normal: the map stores east in red and south in green (its rows run north to south);
        // the surface frame comes from screen-space derivatives (no tangents on the sphere).
        vec3 Ns = N;
        if (nOn > 0.0) {
          vec3 t = texture2D(nmap, vUv).xyz * 2.0 - 1.0;
          vec3 dp1 = dFdx(vW), dp2 = dFdy(vW);
          vec2 du1 = dFdx(vUv), du2 = dFdy(vUv);
          vec3 p2 = cross(dp2, N), p1 = cross(N, dp1);
          vec3 T = p2 * du1.x + p1 * du2.x, B = p2 * du1.y + p1 * du2.y;
          float k = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-20));
          Ns = normalize(mix(N, mat3(T * k, B * k, N) * vec3(vec2(t.x, -t.y) * 2.5, t.z), nOn));   // ×2.5: slopes read at this scale
        }
        // No air: the light ends sharply at the terminator, where the relief stands out most.
        float lit = max(dot(Ns, L), 0.0) * smoothstep(-0.03, 0.03, dot(N, L));
        vec3 col = albedo * (0.02 + 1.25 * lit);
        // Earth's shadow: penumbra dims, umbra turns the Moon copper-red (sunlight bent through Earth's atmosphere).
        vec3 P = lmCenter + N * lCone.x;
        float al = dot(P, lAnti);
        if (al > 0.0) {
          float perp = length(P - al * lAnti);
          float ru = 1.02 - al * lCone.y, rp = 1.02 + al * lCone.z;
          float umbra = 1.0 - smoothstep(ru - 0.015, ru + 0.015, perp);
          float pen = 1.0 - smoothstep(ru, rp, perp);
          col *= 1.0 - 0.6 * pen * (1.0 - umbra);
          col = mix(col, albedo * vec3(0.55, 0.16, 0.07) * 0.5 * (0.35 + 0.65 * lit), umbra);
        }
        gl_FragColor = vec4(col, 1.0);
        #include <encodings_fragment>
      }`,
  });
}

// Saturn and Jupiter: plain diffuse lighting plus shadows that the stylised scene itself casts —
// the ring shadow on Saturn, and the Galilean moons' shadows on Jupiter's clouds.
const shadowU = {
  ringN: { value: new THREE.Vector3(0, 1, 0) },
  satCenter: { value: new THREE.Vector3() },
  satR: { value: 1 },
  jupMoons: { value: [new THREE.Vector4(), new THREE.Vector4(), new THREE.Vector4(), new THREE.Vector4()] },
  jFlow: { value: 0 },
  sFlow: { value: 0 },
  nFlow: { value: 0 },
  nTime: { value: 0 },
};
function giantMaterial(b, tex) {
  const saturn = b.id === "saturn";
  // The flow shifts the map sideways, so it must wrap around instead of stretching the edge column into a seam.
  tex[b.id].wrapS = THREE.RepeatWrapping;
  tex[b.id].needsUpdate = true;
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({ map: { value: tex[b.id] }, ringMap: { value: tex.saturnRing }, sunPos: earthU.sunPos }, shadowU),
    defines: { [b.id.toUpperCase()]: 1 },
    vertexShader: EARTH_VERT,
    fragmentShader: (b.id === "neptune" || b.id === "uranus" ? NOISE_GLSL : "") + `
      uniform sampler2D map; uniform sampler2D ringMap; uniform vec3 sunPos;
      uniform vec3 ringN; uniform vec3 satCenter; uniform float satR; uniform vec4 jupMoons[4]; uniform float jFlow; uniform float sFlow;
      uniform float nFlow; uniform float nTime;
      varying vec2 vUv; varying vec3 vN; varying vec3 vW; varying vec3 vObj;
      #ifdef URANUS
        // Uranus is nearly featureless: faint bands drifting on its wind profile (retrograde at the equator,
        // prograde at mid-latitudes), the bright north polar cap seen in recent years, and rare pale clouds.
        float uranusJet(float latDeg) {
          return -0.45 * exp(-pow(latDeg / 22.0, 2.0)) + 0.6 * exp(-pow((abs(latDeg) - 58.0) / 16.0, 2.0));
        }
        vec3 uranusAlbedo(vec2 uv) {
          float p1 = fract(nFlow * 0.6), p2 = fract(nFlow * 0.6 + 0.5);
          float w1 = 1.0 - abs(2.0 * p1 - 1.0);
          float latDeg = (uv.y - 0.5) * 180.0;
          vec3 a = texture2D(map, vec2(uv.x - uranusJet(latDeg) * p1 * 0.01, uv.y)).rgb;
          vec3 b = texture2D(map, vec2(uv.x - uranusJet(latDeg) * p2 * 0.01, uv.y)).rgb;
          vec3 col = pow(a * w1 + b * (1.0 - w1), vec3(2.2));
          col *= 1.0 + 0.04 * sin(radians(latDeg) * 14.0) + 0.025 * sin(radians(latDeg) * 31.0 + 1.0);
          col = mix(col, vec3(0.78, 0.92, 0.95), smoothstep(52.0, 78.0, latDeg) * 0.35);
          vec3 p = normalize(vObj);
          float lat = asin(clamp(p.y, -1.0, 1.0)), lon = atan(p.z, p.x) + uranusJet(latDeg) * p1 * 0.3;
          vec3 q = vec3(cos(lat) * cos(lon), sin(lat) * 7.0, cos(lat) * sin(lon));
          float cl = smoothstep(0.62, 0.9, snoise(q * 3.0 + vec3(0.0, 0.0, nTime * 0.015)))
                   * (exp(-pow((degrees(lat) - 32.0) / 7.0, 2.0)) + 0.7 * exp(-pow((degrees(lat) + 30.0) / 7.0, 2.0))) * 0.3;
          return mix(col, vec3(0.9, 0.97, 1.0), cl);
        }
      #endif
      #ifdef NEPTUNE
        // Real wind profile: a retrograde equatorial jet (up to ~2000 km/h) and prograde jets near ±70°.
        float neptuneJet(float latDeg) {
          return -exp(-pow(latDeg / 38.0, 2.0)) + 0.55 * exp(-pow((abs(latDeg) - 68.0) / 14.0, 2.0));
        }
        // High methane-ice clouds: thin streaks stretched along their latitude, in the belts where Voyager 2 saw them.
        // (Longitude here runs opposite to the map's u, so "+ jet" moves them the same way as the bands.)
        float neptuneClouds(vec3 p, float ph) {
          float lat = asin(clamp(p.y, -1.0, 1.0)), latDeg = degrees(lat);
          float lon = atan(p.z, p.x) + neptuneJet(latDeg) * ph * 0.35;
          vec3 q = vec3(cos(lat) * cos(lon), sin(lat) * 8.0, cos(lat) * sin(lon));
          float n = snoise(q * 3.0 + vec3(0.0, 0.0, nTime * 0.02)) * 0.6 + snoise(q * 7.0 + 4.0) * 0.4;
          float belts = exp(-pow((latDeg + 27.0) / 6.0, 2.0)) + 0.6 * exp(-pow((latDeg - 28.0) / 6.0, 2.0)) + 0.5 * exp(-pow((latDeg + 68.0) / 4.0, 2.0));
          return smoothstep(0.5, 0.85, n) * belts * 0.45;
        }
        vec3 neptuneAlbedo(vec2 uv) {
          float p1 = fract(nFlow), p2 = fract(nFlow + 0.5);
          float w1 = 1.0 - abs(2.0 * p1 - 1.0);
          float lat = (uv.y - 0.5) * 180.0;
          vec3 a = texture2D(map, vec2(uv.x - neptuneJet(lat) * p1 * 0.012, uv.y)).rgb;
          vec3 b = texture2D(map, vec2(uv.x - neptuneJet(lat) * p2 * 0.012, uv.y)).rgb;
          vec3 col = pow(a * w1 + b * (1.0 - w1), vec3(2.2));
          vec3 p = normalize(vObj);
          float cl = neptuneClouds(p, p1) * w1 + neptuneClouds(p, p2) * (1.0 - w1);
          return mix(col, vec3(0.82, 0.88, 1.0), cl);
        }
      #endif
      #ifdef SATURN
        // Gentle band drift (strongest at the equatorial jet) plus a turn of the vortex inside the polar hexagon (above ~79°N);
        // both run in two cross-faded phases, so nothing smears into rings over time.
        vec2 saturnFlow(vec2 uv, float ph) {
          float lat = (uv.y - 0.5) * 180.0;
          float jet = 0.9 * exp(-pow(lat / 18.0, 2.0)) + 0.2 * sin(radians(lat) * 9.0) * (1.0 - smoothstep(60.0, 76.0, abs(lat)));
          float polar = smoothstep(78.8, 80.0, lat);
          return vec2(uv.x - jet * ph * 0.008 * (1.0 - polar) - polar * ph * 0.025, uv.y);
        }
        vec3 saturnAlbedo(vec2 uv) {
          float p1 = fract(sFlow), p2 = fract(sFlow + 0.5);
          float w1 = 1.0 - abs(2.0 * p1 - 1.0);
          vec3 a = texture2D(map, saturnFlow(uv, p1)).rgb;
          vec3 b = texture2D(map, saturnFlow(uv, p2)).rgb;
          return pow(a * w1 + b * (1.0 - w1), vec3(2.2));
        }
      #endif
      #ifdef JUPITER
        // Where one flow phase samples the map: bands slide at latitude-dependent jet speeds,
        // and the Great Red Spot (texture centre u 0.365, v 0.3875) turns anticlockwise as a whole.
        vec2 jupiterFlow(vec2 uv, float ph) {
          float lat = (uv.y - 0.5) * 3.14159;
          float jet = 0.55 * sin(lat * 7.0) + 0.3 * sin(lat * 13.0 + 1.3) + 0.15 * cos(lat * 3.0);
          vec2 c = vec2(0.365, 0.3875), d = uv - c;
          d.x = mod(d.x + 0.5, 1.0) - 0.5;
          vec2 e = d / vec2(0.034, 0.036);
          float r = length(e);
          float inside = 1.0 - smoothstep(0.7, 1.3, r);
          float a = -ph * 1.1 * (1.0 - smoothstep(0.0, 1.3, r));
          vec2 re = vec2(cos(a) * e.x - sin(a) * e.y, sin(a) * e.x + cos(a) * e.y) * vec2(0.034, 0.036);
          vec2 banded = vec2(uv.x - jet * ph * 0.012, uv.y);
          return mix(banded, c + re, inside);
        }
        vec3 jupiterAlbedo(vec2 uv) {
          float p1 = fract(jFlow), p2 = fract(jFlow + 0.5);
          float w1 = 1.0 - abs(2.0 * p1 - 1.0);
          vec3 a = texture2D(map, jupiterFlow(uv, p1)).rgb;
          vec3 b = texture2D(map, jupiterFlow(uv, p2)).rgb;
          return pow(a * w1 + b * (1.0 - w1), vec3(2.2));
        }
      #endif
      void main() {
        vec3 N = normalize(vN), L = normalize(sunPos - vW);
        float light = 0.03 + 1.25 * max(dot(N, L), 0.0);
        #ifdef SATURN
          float dn = dot(L, ringN);
          if (abs(dn) > 1e-4) {
            float t = dot(satCenter - vW, ringN) / dn;
            if (t > 0.0) {
              float r = length(vW + L * t - satCenter) / satR;
              if (r > 1.24 && r < 2.27) light *= pow(1.0 - 0.9 * texture2D(ringMap, vec2((r - 1.24) / 1.03, 0.5)).a, 2.2);
            }
          }
          // Ringshine: the sunlit face of the rings faintly lights the night side facing it.
          vec3 litFace = ringN * sign(dot(L, ringN));
          light += 0.045 * max(dot(N, litFace), 0.0) * (1.0 - smoothstep(-0.05, 0.2, dot(N, L)));
        #endif
        #ifdef JUPITER
          for (int i = 0; i < 4; i++) {
            vec3 m = jupMoons[i].xyz - vW;
            float al = dot(m, L);
            if (al > 0.0) {
              float perp = length(m - al * L), rr = jupMoons[i].w;
              light *= mix(1.0, 0.1, 1.0 - smoothstep(rr * 0.8, rr * 1.1, perp));
            }
          }
        #endif
        #ifdef JUPITER
          vec3 albedo = jupiterAlbedo(vUv);
        #elif defined(SATURN)
          vec3 albedo = saturnAlbedo(vUv);
        #elif defined(NEPTUNE)
          vec3 albedo = neptuneAlbedo(vUv);
        #elif defined(URANUS)
          vec3 albedo = uranusAlbedo(vUv);
        #else
          vec3 albedo = pow(texture2D(map, vUv).rgb, vec3(2.2));
        #endif
        gl_FragColor = vec4(albedo * light, 1.0);
        #include <encodings_fragment>
      }`,
  });
}
// Saturn's rings, now dark where the planet blocks the Sun.
function saturnRingMaterial(tex) {
  return new THREE.ShaderMaterial({
    uniforms: Object.assign({ map: { value: tex.saturnRing }, sunPos: earthU.sunPos }, shadowU),
    vertexShader: "varying vec2 vUv; varying vec3 vW; void main(){ vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }",
    fragmentShader: `
      uniform sampler2D map; uniform vec3 sunPos; uniform vec3 satCenter; uniform float satR; uniform vec3 ringN;
      varying vec2 vUv; varying vec3 vW;
      void main() {
        vec4 t = texture2D(map, vUv);
        vec3 L = normalize(sunPos - vW), V = normalize(cameraPosition - vW), c = satCenter - vW;
        float al = dot(c, L);
        float sh = al > 0.0 ? 1.0 - smoothstep(satR * 0.97, satR * 1.03, length(c - al * L)) : 0.0;
        vec3 col = pow(t.rgb, vec3(2.2)) * (1.0 - 0.92 * sh);
        float thin = 1.0 - t.a;
        // Seen from the unlit side, dense rings go dark while thin, dusty parts glow with light passing through.
        if (dot(L, ringN) * dot(V, ringN) < 0.0) col *= 0.2 + 0.9 * thin;
        // Looking towards the Sun, dust scatters light forward and the rings brighten.
        col *= 1.0 + 1.1 * pow(max(dot(-L, V), 0.0), 6.0) * (0.35 + thin);
        gl_FragColor = vec4(col, t.a);
        #include <encodings_fragment>
      }`,
    side: THREE.DoubleSide, transparent: true, depthWrite: false,
  });
}

const tmpQ = new THREE.Quaternion();
const eclipse = { solar: "", lunar: "" };
// Update eclipse and shadow uniforms. moonKm: geocentric Moon vector in km (scene axes), or null when not on the real date.
function updateShadows(moonKm) {
  const E = byId.earth;
  const S = tA.copy(E.auVec).multiplyScalar(-KM_AU / R_EARTH);        // Earth → Sun, Earth radii
  eclipse.solar = eclipse.lunar = "";
  if (moonKm) {
    const M = tB.copy(moonKm).multiplyScalar(1 / R_EARTH);            // Earth → Moon, Earth radii
    const rs = R_SUN / R_EARTH, rm = R_MOON / R_EARTH;
    // Solar eclipse: shadow cone from the Sun through the Moon.
    const axis = earthU.eAxis.value.copy(M).sub(S);
    const dsm = axis.length();
    axis.divideScalar(dsm);
    earthU.eMoon.value.copy(M);
    earthU.eCone.value.set(rm, (rs + rm) / dsm, (rs - rm) / dsm);
    const v = tAU.copy(M).negate(), al = v.dot(axis), perp = v.addScaledVector(axis, -al).length();
    const rp = rm + al * (rs + rm) / dsm, ru = rm - al * (rs - rm) / dsm;
    if (al > 0 && perp < 1 + Math.abs(ru)) eclipse.solar = ru > 0 ? "повне сонячне затемнення" : "кільцеве сонячне затемнення";
    else if (al > 0 && perp < 1 + rp) eclipse.solar = "часткове сонячне затемнення";
    // Lunar eclipse: Earth's shadow cone pointing away from the Sun (umbra widened ~2% by the atmosphere).
    const dse = S.length(), anti = lunarU.lAnti.value.copy(S).divideScalar(-dse);
    lunarU.lmCenter.value.copy(M);
    lunarU.lCone.value.set(rm, (rs - 1) / dse, (rs + 1) / dse);
    const al2 = M.dot(anti), perp2 = tAU.copy(M).addScaledVector(anti, -al2).length();
    const ru2 = 1.02 - al2 * (rs - 1) / dse, rp2 = 1.02 + al2 * (rs + 1) / dse;
    if (al2 > 0 && perp2 < ru2 - rm) eclipse.lunar = "повне місячне затемнення";
    else if (al2 > 0 && perp2 < ru2 + rm) eclipse.lunar = "часткове місячне затемнення";
    else if (al2 > 0 && perp2 < rp2 + rm) eclipse.lunar = "півтіньове місячне затемнення";
  } else {
    earthU.eMoon.value.set(1e6, 0, 0);
    lunarU.lmCenter.value.set(1e6, 0, 0);
  }
  // Scene-cast shadows on the giants.
  const sat = byId.saturn;
  shadowU.ringN.value.set(0, 1, 0).applyQuaternion(sat.tiltGroup.getWorldQuaternion(tmpQ));
  shadowU.satCenter.value.copy(sat.world);
  shadowU.satR.value = sat.radius;
  ["io", "europa", "ganymede", "callisto"].forEach((id, i) => {
    const m = byId[id];
    shadowU.jupMoons.value[i].set(m.world.x, m.world.y, m.world.z, m.radius);
  });
}

/* ---------- The living Sun: boiling photosphere, sunspots, flares, corona, prominences ---------- */
// 3D simplex noise: Ashima Arts / Stefan Gustavson (MIT licence).
const NOISE_GLSL = `
vec3 mod289(vec3 x){ return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x){ return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x){ return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314 * r; }
float snoise(vec3 v){
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(i.z + vec4(0.0, i1.z, i2.z, 1.0)) + i.y + vec4(0.0, i1.y, i2.y, 1.0)) + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}
float fbm(vec3 p){
  float s = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++) { s += a * snoise(p); p *= 2.03; a *= 0.5; }
  return s;
}
float fbm2(vec3 p){ return 0.5 * snoise(p) + 0.25 * snoise(p * 2.03); }
`;

function createSunFx(sun, tex) {
  const R = sun.radius;
  const SPOTS = 6, FLARES = 4;
  const rnd = (a, b) => a + Math.random() * (b - a);
  const randDir = (maxLat) => {
    const lat = rnd(-maxLat, maxLat) * DEG, lon = Math.random() * TAU;
    return new THREE.Vector3(Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon));
  };

  // Sunspots sit in the "royal belts" between roughly 5° and 35° latitude.
  const spots = [];
  for (let i = 0; i < SPOTS; i++) {
    const d = randDir(35);
    if (Math.abs(d.y) < 0.09) d.y = Math.sign(d.y || 1) * 0.12;
    d.normalize();
    spots.push(new THREE.Vector4(d.x, d.y, d.z, rnd(0.025, 0.06)));
  }
  const flares = [];
  for (let i = 0; i < FLARES; i++) flares.push(new THREE.Vector4(0, 1, 0, 0));

  const surface = new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, map: { value: tex.sun }, spots: { value: spots }, flares: { value: flares } },
    extensions: { derivatives: true },
    vertexShader: `
      varying vec3 vP; varying vec3 vN; varying vec3 vW; varying vec2 vUv;
      void main() {
        vP = normalize(position); vUv = uv;
        vN = normalize(mat3(modelMatrix) * normal);
        vec4 w = modelMatrix * vec4(position, 1.0);
        vW = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: NOISE_GLSL + `
      uniform float time; uniform sampler2D map;
      uniform vec4 spots[${SPOTS}]; uniform vec4 flares[${FLARES}];
      varying vec3 vP; varying vec3 vN; varying vec3 vW; varying vec2 vUv;
      vec3 hash3(vec3 p) {
        p = vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)));
        return fract(sin(p) * 43758.5453123);
      }
      // Cellular noise: F1 and F2 distances to the nearest moving feature points.
      vec2 worley(vec3 x, float t) {
        vec3 n = floor(x), f = fract(x);
        float F1 = 8.0, F2 = 8.0;
        for (int k = -1; k <= 1; k++)
        for (int j = -1; j <= 1; j++)
        for (int i = -1; i <= 1; i++) {
          vec3 g = vec3(float(i), float(j), float(k));
          vec3 o = hash3(n + g);
          o = 0.5 + 0.38 * sin(t + 6.2831 * o);
          vec3 r = g + o - f;
          float d = dot(r, r);
          if (d < F1) { F2 = F1; F1 = d; } else if (d < F2) { F2 = d; }
        }
        return sqrt(vec2(F1, F2));
      }
      vec3 ramp(float h) {
        h = clamp(h, 0.0, 1.0);
        vec3 c1 = vec3(0.35, 0.05, 0.0), c2 = vec3(0.92, 0.3, 0.02), c3 = vec3(1.0, 0.68, 0.2), c4 = vec3(1.0, 0.93, 0.72);
        if (h < 0.4) return mix(c1, c2, h / 0.4);
        if (h < 0.75) return mix(c2, c3, (h - 0.4) / 0.35);
        return mix(c3, c4, (h - 0.75) / 0.25);
      }
      void main() {
        vec3 p = vP;
        float t = time;
        // Large convection cells, slowly churning (domain-warped noise).
        #ifdef ECO
          float big = fbm(p * 2.2 + vec3(0.0, 0.0, t * 0.03)) * 0.5 + 0.5;
        #else
          // The slow warp needs only the broad shapes: two octaves instead of four (half the noise calls).
          vec3 q = p * 2.2 + vec3(fbm2(p * 1.6 + t * 0.02), fbm2(p * 1.6 + 7.3 - t * 0.02), fbm2(p * 1.6 + 13.1 + t * 0.015));
          float big = fbm(q + vec3(0.0, 0.0, t * 0.03)) * 0.5 + 0.5;
        #endif
        // Granulation: bright cells split by dark lanes, boiling quickly.
        #ifdef ECO
          float gran = 0.6 + 0.12 * snoise(p * 55.0 + vec3(0.0, t * 0.2, t * 0.15));
        #else
          vec3 gp = p * 70.0 + snoise(p * 22.0 + t * 0.05) * 0.35;
          // Cells are only worked out where they are big enough to see (close up); further away they blur to an even tone.
          float fw = fwidth(gp.x) + fwidth(gp.y);
          float detail = 1.0 - smoothstep(0.35, 1.0, fw);
          float gran = 0.62;
          if (detail > 0.0) {
            vec2 F = worley(gp, t * 0.6);
            float lanes = smoothstep(0.0, 0.14, F.y - F.x);
            float cell = 1.0 - F.x * 0.55;
            gran = mix(0.62, lanes * cell * (0.9 + 0.2 * snoise(gp * 0.4 + t * 0.1)), detail);
          }
        #endif
        float activity = dot(texture2D(map, vUv).rgb, vec3(0.3, 0.5, 0.2));
        float heat = 0.18 + big * 0.42 + gran * 0.28 + activity * 0.3;

        // Sunspots: dark umbra, ragged penumbra, bright faculae around them.
        for (int i = 0; i < ${SPOTS}; i++) {
          float ang = acos(clamp(dot(p, spots[i].xyz), -1.0, 1.0));
          if (ang > spots[i].w * 3.6) continue;   // far from this spot: nothing to add (saves the noise below)
          float w = spots[i].w * (1.0 + 0.25 * snoise(p * 40.0 + float(i)));
          float pen = 1.0 - smoothstep(w * 0.55, w, ang);
          float umb = 1.0 - smoothstep(w * 0.2, w * 0.45, ang);
          float fac = (1.0 - smoothstep(w, w * 2.8, ang)) * (1.0 - pen);
          heat = heat * (1.0 - 0.42 * pen) * (1.0 - 0.55 * umb) + fac * 0.08;
        }
        vec3 col = ramp(heat);

        // Flares: sudden white-hot bursts.
        for (int i = 0; i < ${FLARES}; i++) {
          if (flares[i].w < 0.001) continue;      // flare not burning
          float ang = acos(clamp(dot(p, flares[i].xyz), -1.0, 1.0));
          if (ang > 0.2) continue;
          float ribbon = 0.6 + 0.4 * snoise(p * 90.0 + t * 0.8);
          col += vec3(1.0, 0.92, 0.75) * flares[i].w * (1.0 - smoothstep(0.0, 0.07, ang)) * ribbon * 1.6;
          col += vec3(1.0, 0.55, 0.2) * flares[i].w * (1.0 - smoothstep(0.0, 0.2, ang)) * 0.35;
        }

        // Limb darkening and reddening towards the edge of the disc.
        float mu = clamp(dot(normalize(vN), normalize(cameraPosition - vW)), 0.0, 1.0);
        col *= 0.6 + 0.4 * pow(mu, 0.6);
        col = mix(col * vec3(1.0, 0.72, 0.5), col, pow(mu, 0.3));
        gl_FragColor = vec4(col * 1.08, 1.0);
      }`,
  });

  if (eco) surface.defines.ECO = 1;
  ecoMaterials.push(surface);

  // Corona: camera-facing disc of glow, streamers and flickering flames that hugs the visible limb.
  const HALF = 4.5;
  const corona = new THREE.Mesh(new THREE.PlaneGeometry(R * HALF * 2, R * HALF * 2), new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 } },
    vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: NOISE_GLSL + `
      uniform float time; varying vec2 vUv;
      void main() {
        vec2 c = vUv * 2.0 - 1.0;
        float r = length(c) * ${HALF.toFixed(1)};
        if (r < 0.9) discard;
        vec2 d = normalize(c);
        float x = max(r - 1.0, 0.0);
        float base = exp(-x * 2.4) * 0.28 + exp(-x * 10.0) * 0.7;
        float streamers = pow(fbm(vec3(d * 2.4, time * 0.02)) * 0.5 + 0.5, 2.6) * exp(-x * 1.1) * 0.8;
        float flames = pow(snoise(vec3(d * 9.0, x * 4.0 - time * 0.45)) * 0.5 + 0.5, 3.0) * exp(-x * 5.5) * 2.0;
        float I = (base + streamers + flames) * smoothstep(0.96, 1.0, r) * (1.0 - smoothstep(${(HALF * 0.7).toFixed(2)}, ${(HALF * 0.98).toFixed(2)}, r));
        vec3 col = mix(vec3(1.0, 0.42, 0.08), vec3(1.0, 0.86, 0.6), clamp(1.0 - x * 0.7, 0.0, 1.0));
        gl_FragColor = vec4(col, clamp(I, 0.0, 1.0));
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  sun.group.add(corona);

  // Prominences: arches of plasma that rise from the surface, hang, and sometimes erupt.
  const promMat = () => new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, life: { value: 0 }, grow: { value: 0 }, seed: { value: Math.random() * 100 }, R: { value: R } },
    vertexShader: `
      uniform float grow; uniform float R;
      varying vec2 vUv; varying vec3 vN; varying vec3 vV;
      void main() {
        vUv = uv;
        vec3 d = normalize(position);
        vec3 p = d * (R + (length(position) - R) * grow);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        vN = normalize(normalMatrix * normal);
        vV = normalize(-mv.xyz);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: NOISE_GLSL + `
      uniform float time; uniform float life; uniform float seed;
      varying vec2 vUv; varying vec3 vN; varying vec3 vV;
      void main() {
        float core = pow(abs(dot(normalize(vN), vV)), 2.6);
        float fil = snoise(vec3(vUv.x * 6.0 - time * 0.35 + seed, sin(vUv.y * 6.2831) * 0.8, time * 0.2 + seed)) * 0.5 + 0.5;
        float env = smoothstep(0.0, 0.15, life) * (1.0 - smoothstep(0.7, 1.0, life));
        float I = core * (0.2 + 0.9 * fil * fil) * env * 0.7;
        vec3 col = mix(vec3(0.95, 0.22, 0.04), vec3(1.0, 0.55, 0.18), fil);
        gl_FragColor = vec4(col, I);
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  });
  const proms = [];
  function shapeProm(p, at, erupt) {
    const A = at ? at.clone() : randDir(50);
    const side = new THREE.Vector3().crossVectors(A, Math.abs(A.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0)).normalize();
    side.applyAxisAngle(A, Math.random() * TAU);
    const sep = rnd(0.08, 0.28), height = erupt ? rnd(0.25, 0.45) : rnd(0.12, 0.5), twist = rnd(-0.06, 0.06);
    const B = A.clone().applyAxisAngle(side, sep);
    const normal = new THREE.Vector3().crossVectors(A, B).normalize();
    const pts = [];
    for (let k = 0; k <= 24; k++) {
      const s = k / 24, dir = new THREE.Vector3().lerpVectors(A, B, s).normalize();
      dir.addScaledVector(normal, Math.sin(PI * s) * twist).normalize();
      pts.push(dir.multiplyScalar(R * (0.995 + height * Math.sin(PI * s) * (1 + 0.15 * Math.sin(3 * PI * s)))));
    }
    if (p.mesh.geometry) p.mesh.geometry.dispose();
    p.mesh.geometry = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 64, R * rnd(0.025, 0.05), 10, false);
    p.erupt = erupt;
    p.dur = erupt ? rnd(7, 11) : rnd(10, 20);
    p.age = 0;
  }
  for (let i = 0; i < 7; i++) {
    const p = { mesh: new THREE.Mesh(new THREE.BufferGeometry(), promMat()) };
    shapeProm(p, null, Math.random() < 0.2);
    p.age = Math.random() * p.dur;
    sun.mesh.add(p.mesh);
    proms.push(p);
  }

  let time = Math.random() * 100, nextFlare = rnd(2, 5);
  const flareState = flares.map(() => ({ age: 99 }));

  function update(dt, camera) {
    time += dt;
    surface.uniforms.time.value = time;
    corona.material.uniforms.time.value = time;

    // Keep the corona facing the camera; scale it so its inner edge matches the visible limb from this distance.
    corona.lookAt(camera.position);
    const D = Math.max(camera.position.distanceTo(sun.world), R * 1.001);
    const limb = D / Math.sqrt(D * D - R * R);
    corona.scale.setScalar(limb);

    // Flares: fast rise, slow fade; a big one often launches an eruptive prominence.
    nextFlare -= dt;
    if (nextFlare <= 0) {
      nextFlare = rnd(4, 10);
      const i = flareState.findIndex(f => f.age > 4) >= 0 ? flareState.findIndex(f => f.age > 4) : 0;
      const d = randDir(38);
      flares[i].set(d.x, d.y, d.z, 0);
      flareState[i] = { age: 0, peak: rnd(0.5, 1.1) };
      if (Math.random() < 0.6) {
        const oldest = proms.reduce((a, b) => (b.age / b.dur > a.age / a.dur ? b : a));
        shapeProm(oldest, d, true);
      }
    }
    flareState.forEach((f, i) => {
      f.age += dt;
      flares[i].w = f.age > 6 ? 0 : f.peak * Math.min(1, f.age / 0.35) * Math.exp(-Math.max(0, f.age - 0.35) / 1.3);
    });

    for (const p of proms) {
      p.age += dt;
      if (p.age >= p.dur) shapeProm(p, null, Math.random() < 0.22);
      const life = p.age / p.dur, u = p.mesh.material.uniforms;
      u.life.value = life; u.time.value = time;
      u.grow.value = 0.25 + 0.75 * smoothstepJS(0, 0.25, life) + (p.erupt ? 1.3 * Math.pow(smoothstepJS(0.4, 1, life), 2) : 0);
    }
  }
  const smoothstepJS = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
  return { material: surface, update };
}
