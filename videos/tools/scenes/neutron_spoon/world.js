// «Ложка нейтронної зорі»: every frame of the video, drawn by three.js in headless Chromium (path.js gives the shots).
//   * the star: one full-screen shader. Light bending (Beloborodov 2002: 1 − cos α = (1 − cos ψ)(1 − r_s/R)) shows more
//     than half the surface and lenses the sky behind; the hot polar caps and the two radio beams follow the magnetic
//     axis (50° from the spin axis). Beams and caps are averaged over the shutter analytically (erf), so 716 turns a
//     second blur into the cones they really sweep. Background: the Milky Way, and the Crab Nebula (Hubble, NASA/ESA,
//     J. Hester & A. Loll) with the star at its pulsar.
//   * the dipole field lines (tubes), hidden behind the star;
//   * Kyiv from orbit (Sentinel-2 cloudless 2016, EOX) lit by the star at true size (20 km) 26 km above the city;
//   * the teaspoon (a parametric steel spoon) holding the glowing matter; the balance with a heap of little people.
//   Bloom, ACES tone mapping and a light vignette at the end.
//   node scenes/neutron_spoon/world.js stills 1,6,10     -> work/neutron_spoon/still_<t>.jpg
//   node scenes/neutron_spoon/world.js video [from to]   -> work/neutron_spoon/w3d/f_00000.jpg …
const fs = require('fs'), path = require('path'), http = require('http');
const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const TOOLS = path.resolve(__dirname, '../..'), WORK = path.join(TOOLS, 'work', 'neutron_spoon');
const P = require('./path');
const [mode = 'stills', list = '1', upto] = process.argv.slice(2);
const W = 720, H = 1280;
const EX = ['EffectComposer', 'RenderPass', 'ShaderPass', 'UnrealBloomPass', 'Pass'].map(n => '/ex/postprocessing/' + n + '.js')
  .concat(['/ex/shaders/CopyShader.js', '/ex/shaders/LuminosityHighPassShader.js', '/ex/utils/BufferGeometryUtils.js']);

const page = `<!doctype html><html><body style="margin:0;background:#000"><script src="/three.min.js"></script>
${['/ex/shaders/CopyShader.js', '/ex/shaders/LuminosityHighPassShader.js', '/ex/postprocessing/Pass.js', '/ex/postprocessing/EffectComposer.js',
   '/ex/postprocessing/ShaderPass.js', '/ex/postprocessing/UnrealBloomPass.js', '/ex/utils/BufferGeometryUtils.js'].map(s => `<script src="${s}"></script>`).join('')}
<script>
const R = ${P.R}, RS = ${P.RS}, STAR_Y = ${P.STAR_Y}, D = Math.PI / 180;
const V3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);
// spin axis and the two axes across it (the magnetic axis turns round S)
const S = new THREE.Vector3(0.22, 1, 0.12).normalize();
const E1 = new THREE.Vector3().crossVectors(S, new THREE.Vector3(0, 0, 1)).normalize(), E2 = new THREE.Vector3().crossVectors(S, E1);
const ALPHA = 50 * D;
const magAxis = phi => S.clone().multiplyScalar(Math.cos(ALPHA)).add(E1.clone().multiplyScalar(Math.sin(ALPHA) * Math.cos(phi))).add(E2.clone().multiplyScalar(Math.sin(ALPHA) * Math.sin(phi)));

const GL_BEAM = \`
const float PI = 3.14159265;
uniform vec3 S, E1, E2; uniform float alpha, phi0, dphi;
float erf_(float x) { float s = sign(x); x = abs(x); float t = 1.0 / (1.0 + 0.3275911 * x);
  return s * (1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * exp(-x * x)); }
// how much of the shutter time a beam of half-width w along the magnetic axis covers direction pn
float beamAvg(vec3 pn, float w) {
  float cb = clamp(dot(pn, S), -1.0, 1.0);
  float dB = acos(cb) - alpha;
  float g = exp(-dB * dB / (w * w));
  if (g < 2e-4) return 0.0;
  float K = max(sin(alpha) * sqrt(max(1.0 - cb * cb, 0.0)), 2e-3);
  float q = sqrt(K) / w;
  float span, I;
  if (dphi >= 6.28) { I = 2.0; span = 2.0 * PI; }
  else {
    float fp = atan(dot(pn, E2), dot(pn, E1));
    float x0 = mod(phi0 - fp + PI, 2.0 * PI) - PI, x1 = x0 + dphi;
    I = erf_(q * x1) - erf_(q * x0) + erf_(q * (x1 - 2.0 * PI)) - erf_(q * (x0 - 2.0 * PI)) + erf_(q * (x1 + 2.0 * PI)) - erf_(q * (x0 + 2.0 * PI));
    span = dphi;
  }
  return g * min(1.0, w * 0.8862269 / sqrt(K) * I / span);
}
float hash2(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float hash3(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash3(i), hash3(i + vec3(1,0,0)), f.x), mix(hash3(i + vec3(0,1,0)), hash3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash3(i + vec3(0,0,1)), hash3(i + vec3(1,0,1)), f.x), mix(hash3(i + vec3(0,1,1)), hash3(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = p * 2.03 + 1.7; a *= 0.5; } return s; }
\`;

const starFrag = GL_BEAM + \`
uniform mat4 camWorld, projInv; uniform vec3 camPos;
uniform float R, RS, lens, air, expo, bgK, crabK, crabWt, groundY, useGround, noiseK, phiMid, pxAng, beamK;
uniform sampler2D mw, crab; uniform vec2 pulsarUV;
varying vec2 vUv;
vec3 rotS(vec3 v, float a) { return v * cos(a) + cross(S, v) * sin(a) + S * dot(S, v) * (1.0 - cos(a)); }
float beamDens(vec3 p) {
  float r = length(p);
  if (r < R) return 0.0;
  vec3 pn = p / r;
  float w = 0.075 + 0.0025 * r / R;
  float c = beamAvg(pn, w) + beamAvg(-pn, w);
  float s = beamAvg(pn, w * 3.2) + beamAvg(-pn, w * 3.2);
  float hk = smoothstep(1.0, 6.28, dphi);
  return (c * (1.0 + 3.0 * hk) + 0.10 * s * (1.0 - hk)) * smoothstep(R, R * 1.3, r) * pow(2.0 * R / (r + R), 1.25 + 1.2 * hk);
}
void main() {
  vec2 ndc = vUv * 2.0 - 1.0;
  vec4 v = projInv * vec4(ndc, -1.0, 1.0);
  vec3 d = normalize((camWorld * vec4(v.xyz / v.w, 0.0)).xyz);
  vec3 o = camPos;
  float tc = -dot(o, d); vec3 pc = o + d * tc; float b = length(pc); vec3 ch = pc / max(b, 1e-6);
  float u = lens > 0.5 ? RS / R : 0.0;
  float bmax = R / sqrt(1.0 - u);
  bool front = tc > 0.0;
  vec3 col = vec3(0.0); float A = 0.0;
  // ---- the sky behind (lensed) ----
  if (bgK > 0.0) {
    vec3 dd = d;
    if (lens > 0.5 && b > bmax * 0.999) {
      float x = RS / b, defl = (2.0 * x + 2.945 * x * x + 4.177 * x * x * x) * smoothstep(-2.0 * R, 0.0, tc) * exp(-(b - bmax) / (2.5 * R));
      dd = normalize(d * cos(defl) - ch * sin(defl));
    }
    vec3 m = pow(texture2D(mw, vec2(atan(dd.x, -dd.z) / (2.0 * PI) + 0.5, acos(clamp(dd.y, -1.0, 1.0)) / PI)).rgb, vec3(2.2)) * 0.8;
    if (crabK > 0.0) {
      vec3 cd = normalize(-o), cu = normalize(cross(cd, vec3(0.0, 1.0, 0.0))), cv = cross(cu, cd);
      float z = dot(dd, cd);
      if (z > 0.0) {
        vec2 q = vec2(dot(dd, cu), dot(dd, cv)) / z / crabWt;
        vec2 uvc = pulsarUV + vec2(q.x, -q.y);
        float inside = smoothstep(0.0, 0.16, uvc.x) * smoothstep(1.0, 0.84, uvc.x) * smoothstep(0.0, 0.16, uvc.y) * smoothstep(1.0, 0.84, uvc.y);
        vec3 cc = pow(texture2D(crab, clamp(uvc, 0.0, 1.0)).rgb, vec3(2.2)) * 1.15;
        m = mix(m, cc, crabK * inside);
      }
    }
    col = m * bgK;
  }
  // ---- the surface ----
  if (front && b < bmax) {
    float sa = b / bmax, ca = sqrt(max(1.0 - sa * sa, 0.0));
    float cpsi = clamp(1.0 - (1.0 - ca) / (1.0 - u), -1.0, 1.0), spsi = sqrt(max(1.0 - cpsi * cpsi, 0.0));
    vec3 n = -d * cpsi + ch * spsi;
    vec3 nr = rotS(n, -phiMid);
    float cap = beamAvg(n, 0.30) + beamAvg(-n, 0.30);
    float hot = beamAvg(n, 0.12) + beamAvg(-n, 0.12);
    float f1 = fbm(nr * 5.0), f2 = fbm(nr * 18.0 + 3.0);
    float tex = 1.0 + noiseK * ((f1 - 0.5) * 0.55 + (f2 - 0.5) * 0.3);
    vec3 base = vec3(0.42, 0.58, 1.0) * 0.85 * tex * (0.45 + 0.55 * ca);
    col = base + vec3(0.80, 0.90, 1.0) * cap * 1.6 + vec3(1.0) * hot * 3.5;
    // a fine rim of light where the bent rays graze
    col += vec3(0.6, 0.75, 1.0) * pow(sa, 8.0) * 0.5;
    A = 1.0;
  }
  // ---- glow round it ----
  if (front || length(o) < 3.0 * R) {
    float e = max(b - bmax, 0.0);
    vec3 gc = vec3(0.55, 0.72, 1.0);
    col += gc * (exp(-e / (0.10 * R)) * 0.45 + exp(-e / (0.8 * R)) * 0.08) * (1.0 - A);
    if (air > 0.5) col += vec3(0.45, 0.62, 1.0) * (exp(-e / (2.0 * R)) * 0.12 + exp(-e / (8.0 * R)) * 0.04) * (1.0 - A);
  }
  // a point of light when the star is smaller than a pixel
  float th = acos(clamp(dot(d, normalize(-o)), -1.0, 1.0));
  col += vec3(0.7, 0.82, 1.0) * 6.0 * exp(-pow(th / (1.1 * pxAng), 2.0)) * (1.0 - A) * smoothstep(3.0 * pxAng, 0.8 * pxAng, R / length(o));
  // ---- the beams: marched along the ray, step growing with distance from the star ----
  float Rmax = 32.0 * R;
  if (b < Rmax && beamK > 0.0) {
    float h = sqrt(Rmax * Rmax - b * b), tA = max(0.0, tc - h), tB = tc + h;
    if (b < R) tB = min(tB, tc - sqrt(R * R - b * b));
    if (useGround > 0.5 && d.y < 0.0) tB = min(tB, (groundY - o.y) / d.y);
    if (tB > tA) {
      float acc = 0.0, tt = tA, jit = hash2(gl_FragCoord.xy);
      for (int i = 0; i < 44; i++) {
        float r = length(o + d * tt);
        float st = max(0.085 * r, 0.05 * R);
        acc += beamDens(o + d * (tt + st * jit)) * min(st, tB - tt);
        tt += st; if (tt > tB) break;
      }
      col += vec3(0.62, 0.78, 1.0) * acc / R * beamK * 0.55 * (1.0 + 0.6 * air);
    }
  }
  gl_FragColor = vec4(col * expo, A);
  ${process.env.DBG || ''}
}\`;

async function setup() {
  const load = (f, srgb) => new Promise(r => new THREE.TextureLoader().load(f, t => { t.anisotropy = 16; r(t); }, undefined, () => r(null)));
  const [mwTex, crabTex, groundTex] = await Promise.all(['/w/sky.jpg', '/w/dl/crab.jpg', '/w/ground.jpg'].map(f => load(f)));
  crabTex.flipY = false; crabTex.needsUpdate = true;
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  renderer.setSize(${W}, ${H}); renderer.setPixelRatio(1);
  renderer.physicallyCorrectLights = true;
  renderer.outputEncoding = THREE.LinearEncoding; renderer.toneMapping = THREE.NoToneMapping;
  renderer.autoClear = false;
  document.body.appendChild(renderer.domElement);

  // ---------- the star quad ----------
  const beamU = { S: { value: S }, E1: { value: E1 }, E2: { value: E2 }, alpha: { value: ALPHA }, phi0: { value: 0 }, dphi: { value: 0.05 } };
  const starU = Object.assign({
    camWorld: { value: new THREE.Matrix4() }, projInv: { value: new THREE.Matrix4() }, camPos: { value: new THREE.Vector3() },
    R: { value: R }, RS: { value: RS }, lens: { value: 1 }, air: { value: 0 }, expo: { value: 1 }, bgK: { value: 1 }, crabK: { value: 0 }, crabWt: { value: 1 },
    groundY: { value: -STAR_Y }, useGround: { value: 0 }, noiseK: { value: 1 }, phiMid: { value: 0 }, pxAng: { value: 0.0005 }, beamK: { value: 1 },
    mw: { value: mwTex }, crab: { value: crabTex }, pulsarUV: { value: new THREE.Vector2(1998 / 3864, 2075 / 3864) } }, beamU);
  const starMat = new THREE.ShaderMaterial({ uniforms: starU, vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: starFrag, depthTest: false, depthWrite: false, transparent: true,
    blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor });
  const quadScene = new THREE.Scene(); const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), starMat); quad.frustumCulled = false; quadScene.add(quad);
  const camS = new THREE.PerspectiveCamera(40, ${W} / ${H}, 0.01, 1e9);

  // ---------- field lines (dipole r = L sin²θ round the magnetic axis = local +y) ----------
  const linesScene = new THREE.Scene(), lines = new THREE.Group(); linesScene.add(lines);
  const lineU = { camP: { value: new THREE.Vector3() }, R: { value: R }, k: { value: 1 }, time: { value: 0 } };
  const lineMat = new THREE.ShaderMaterial({ uniforms: lineU, transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: 'varying vec3 vW; varying vec2 vUv; void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: \`uniform vec3 camP; uniform float R, k, time; varying vec3 vW; varying vec2 vUv;
      void main() {
        vec3 d = vW - camP; float L = length(d); d /= L;
        float tc = -dot(camP, d); float b2 = dot(camP, camP) - tc * tc;
        if (b2 < R * R * 1.0) { float th = tc - sqrt(R * R - b2); if (th > 0.0 && th < L) discard; }
        float s = vUv.x;
        float ends = 0.35 + 0.65 * pow(abs(s - 0.5) * 2.0, 2.0);
        float pulse = 0.55 + 0.45 * pow(0.5 + 0.5 * sin(s * 40.0 - time * 5.0), 6.0);
        gl_FragColor = vec4(vec3(0.40, 0.62, 1.0) * 0.30 * ends * pulse * k, 1.0);
      }\` });
  for (const Lr of [1.7, 2.5, 3.7, 5.6]) for (let j = 0; j < 7; j++) {
    const az = (j / 7) * 2 * Math.PI + Lr * 0.7, L = Lr * R, th0 = Math.asin(Math.sqrt(R / L)), pts = [];
    for (let i = 0; i <= 90; i++) { const th = th0 + (Math.PI - 2 * th0) * i / 90, r = L * Math.sin(th) ** 2;
      pts.push(new THREE.Vector3(r * Math.sin(th) * Math.cos(az), r * Math.cos(th), r * Math.sin(th) * Math.sin(az))); }
    const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 200, 0.010 * R * (0.7 + Lr * 0.15), 5, false);
    lines.add(new THREE.Mesh(g, lineMat));
  }

  // ---------- Kyiv ----------
  const kyiv = new THREE.Scene();
  const groundU = Object.assign({ map: { value: groundTex }, R: { value: R }, starP: { value: new THREE.Vector3(0, STAR_Y, 0) }, expo: { value: 1 } }, beamU);
  const groundMat = new THREE.ShaderMaterial({ uniforms: groundU,
    vertexShader: 'varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: GL_BEAM + \`uniform sampler2D map; uniform float R, expo; uniform vec3 starP; varying vec3 vW;
      void main() {
        vec2 uv = vec2(vW.x / 150.0 + 0.5, 0.5 - vW.z / 150.0);
        float inside = smoothstep(0.0, 0.02, uv.x) * smoothstep(1.0, 0.98, uv.x) * smoothstep(0.0, 0.02, uv.y) * smoothstep(1.0, 0.98, uv.y);
        vec3 alb = mix(vec3(0.05, 0.07, 0.05), pow(texture2D(map, clamp(uv, 0.0, 1.0)).rgb, vec3(2.2)) * 1.6, inside);
        vec3 L = starP - vW; float d = length(L); vec3 l = L / d;
        float irr = R * R / (d * d) * max(l.y, 0.0);
        vec3 pn = -l;
        float bm = beamAvg(pn, 0.09) + beamAvg(-pn, 0.09);
        vec3 col = alb * (vec3(0.62, 0.78, 1.0) * irr * 7.0 + vec3(0.7, 0.85, 1.0) * bm * 14.0 * R * R / (d * d) + vec3(0.018, 0.022, 0.032));
        float dist = length(cameraPosition - vW);
        vec3 haze = vec3(0.04, 0.06, 0.12) * (0.12 + 1.5 * R * R / (d * d + R * R));
        col = mix(col, haze, 1.0 - exp(-dist / 700.0));
        col = mix(col, vec3(0.03, 0.05, 0.10) * 0.8, smoothstep(250.0, 560.0, length(vW.xz)));
        gl_FragColor = vec4(col * expo, 1.0);
      }\` });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1200, 1200, 1, 1).rotateX(-Math.PI / 2), groundMat); kyiv.add(ground);
  const skyMat = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, uniforms: { expo: { value: 1 } },
    vertexShader: 'varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform float expo; varying vec3 vD; void main() { float h = max(vD.y, 0.0); vec3 c = mix(vec3(0.03, 0.05, 0.10), vec3(0.002, 0.003, 0.008), pow(h, 0.35)); gl_FragColor = vec4(c * expo, 1.0); }' });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(5000, 32, 16), skyMat); kyiv.add(sky);
  const camK = new THREE.PerspectiveCamera(50, ${W} / ${H}, 0.5, 20000);

  // ---------- environment for metal: dark space, the star's blue-white glare, a faint warm fill ----------
  const envScene = new THREE.Scene();
  envScene.add(new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), new THREE.MeshBasicMaterial({ color: 0x020306, side: THREE.BackSide })));
  const blob = (pos, r, c) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 12), new THREE.MeshBasicMaterial({ color: c })); m.position.set(...pos); envScene.add(m); };
  blob([-20, 26, -30], 15, new THREE.Color(0.75, 0.85, 1.0).multiplyScalar(5));
  blob([0, 45, 0], 22, new THREE.Color(0.10, 0.12, 0.18));
  blob([25, 10, -35], 12, new THREE.Color(0.45, 0.55, 0.8));
  blob([30, 6, 20], 14, new THREE.Color(0.22, 0.24, 0.30));
  blob([10, 30, 30], 10, new THREE.Color(0.35, 0.42, 0.6));
  blob([-30, -10, 30], 7, new THREE.Color(0.5, 0.45, 0.4));
  blob([0, -40, 0], 26, new THREE.Color(0.02, 0.025, 0.04));
  blob([-36, 4, 18], 8, new THREE.Color(0.25, 0.3, 0.45));
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envMap = pmrem.fromScene(envScene, 0.02).texture;

  // ---------- the spoon (cm; bowl centre at the origin, handle toward +x) ----------
  const smoothstep = (a, b, x) => { x = Math.min(1, Math.max(0, (x - a) / (b - a))); return x * x * (3 - 2 * x); };
  function spoonGeom() {
    const NU = 300, NV = 56, L = 14.2;
    const hw = x => {
      const e = x < 4.5 ? 1.36 * Math.sqrt(Math.max(0, 1 - ((x - 2.25) / 2.25) ** 2)) : 0;
      let n = x < 3.6 ? 0 : (0.22 + 0.52 * smoothstep(5.0, 12.4, x)) * smoothstep(3.6, 4.3, x);
      if (x > 12.6) n *= Math.sqrt(Math.max(0, 1 - ((x - 12.6) / 1.6) ** 2));
      const k = 0.18, h = Math.max(k - Math.abs(e - n), 0) / k; return Math.max(e, n) + h * h * k * 0.25;
    };
    const z = (x, y) => {
      const e = ((x - 2.25) / 2.25) ** 2 + (y / 1.36) ** 2;
      const dish = -0.78 * Math.pow(Math.max(0, 1 - e), 0.85);
      const lift = 1.25 * Math.pow(smoothstep(4.2, 14.2, x), 1.4) - 0.07 * Math.exp(-(((x - 4.7) / 0.6) ** 2));
      const ridge = x > 4.4 ? 0.05 * (1 - (y / Math.max(hw(x), 0.01)) ** 2) * smoothstep(4.4, 5.5, x) : 0;
      return dish + lift + ridge;
    };
    const th = x => lerp1(0.085, 0.13, smoothstep(3.8, 6, x));
    function lerp1(a, b, k) { return a + (b - a) * k; }
    const top = [], bot = [];
    for (let i = 0; i <= NU; i++) {
      const u = i / NU, x = 0.02 + u * (L - 0.04);
      const w = hw(x);
      for (let j = 0; j <= NV; j++) {
        const v = -1 + 2 * j / NV, y = v * w * 0.999, zz = z(x, y);
        top.push(x - 2.25, zz, y); bot.push(x - 2.25, zz - th(x), y);
      }
    }
    const idx = (a) => { const out = []; for (let i = 0; i < NU; i++) for (let j = 0; j < NV; j++) { const p = i * (NV + 1) + j;
      if (a) out.push(p, p + 1, p + NV + 1, p + 1, p + NV + 2, p + NV + 1); else out.push(p, p + NV + 1, p + 1, p + 1, p + NV + 1, p + NV + 2); } return out; };
    const mk = (arr, flip) => { const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3)); g.setIndex(idx(flip)); g.computeVertexNormals(); return g; };
    // the edge: a strip joining top and bottom along both sides
    const side = [], sidx = [];
    for (const j of [0, NV]) for (let i = 0; i <= NU; i++) { const p = (i * (NV + 1) + j) * 3; side.push(top[p], top[p + 1], top[p + 2], bot[p], bot[p + 1], bot[p + 2]); }
    for (let s = 0; s < 2; s++) for (let i = 0; i < NU; i++) { const p = s * (NU + 1) * 2 + i * 2;
      if (s === 0) sidx.push(p, p + 2, p + 1, p + 1, p + 2, p + 3); else sidx.push(p, p + 1, p + 2, p + 1, p + 3, p + 2); }
    const gs = new THREE.BufferGeometry(); gs.setAttribute('position', new THREE.Float32BufferAttribute(side, 3)); gs.setIndex(sidx); gs.computeVertexNormals();
    return [mk(top, true), mk(bot, false), gs];
  }
  const steel = new THREE.MeshPhysicalMaterial({ color: 0xe8ecf2, metalness: 1, roughness: 0.16, envMap, envMapIntensity: 1.0, clearcoat: 0.3, clearcoatRoughness: 0.1 });
  const matterU = { time: { value: 0 }, glow: { value: 1 } };
  const matterMat = new THREE.ShaderMaterial({ uniforms: matterU,
    vertexShader: 'varying vec3 vP; varying vec3 vN; varying vec3 vW; void main() { vP = position; vN = normalize(normalMatrix * normal); vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: GL_BEAM + \`uniform float time, glow; varying vec3 vP; varying vec3 vN; varying vec3 vW;
      void main() {
        vec3 p = vP * 2.6;
        vec3 wq = p + 0.9 * vec3(fbm(p + vec3(0.0, time * 0.25, 0.0)), fbm(p + 5.2 - time * 0.2), fbm(p + 9.1 + time * 0.15));
        float f = fbm(wq * 1.7 - time * 0.3);
        float ridge = 1.0 - abs(2.0 * fbm(wq * 3.1 + time * 0.4) - 1.0);
        float r = length(vP.xz / vec2(2.0, 1.2));
        float cells = clamp(0.25 + 0.9 * f * f + 0.55 * pow(ridge, 4.0), 0.0, 1.4);
        vec3 c = mix(vec3(0.25, 0.42, 1.0), vec3(0.95, 0.98, 1.0), clamp(cells, 0.0, 1.0));
        float I = (0.6 + 3.6 * cells * cells) * (1.0 - 0.3 * smoothstep(0.8, 1.0, r)) * (0.85 + 0.15 * sin(time * 9.0 + vP.x * 3.0));
        gl_FragColor = vec4(c * I * glow, 1.0);
      }\` });
  function makeSpoon(li) {
    const g = new THREE.Group();
    for (const geo of spoonGeom()) g.add(new THREE.Mesh(geo, steel));
    // the matter: an ellipse just under the rim, a little domed
    const mg = new THREE.RingGeometry(0.0001, 1, 128, 48); mg.rotateX(-Math.PI / 2);
    const pos = mg.attributes.position;
    for (let i = 0; i < pos.count; i++) { const x = pos.getX(i), zq = pos.getZ(i), rr = x * x + zq * zq; pos.setXYZ(i, x * 2.02, -0.12 + 0.8 * Math.sqrt(Math.max(0, 1 - rr)) * (1 - 0.25 * rr), zq * 1.22); }
    mg.computeVertexNormals();
    const m = new THREE.Mesh(mg, matterMat); g.add(m);
    const pl = new THREE.PointLight(new THREE.Color(0.7, 0.82, 1.0), li, 0, 2); pl.position.set(0, 1.2, 0); pl.distance = li < 100 ? 7 : 0; g.add(pl);
    return g;
  }
  // sparks rising off the matter
  function makeSparks(n) {
    const geo = new THREE.BufferGeometry(), a = new Float32Array(n * 3), s = new Float32Array(n);
    for (let i = 0; i < n; i++) { a[i * 3] = (Math.random() - 0.5) * 3.6; a[i * 3 + 1] = Math.random(); a[i * 3 + 2] = (Math.random() - 0.5) * 2.2; s[i] = Math.random(); }
    geo.setAttribute('position', new THREE.BufferAttribute(a, 3)); geo.setAttribute('seed', new THREE.BufferAttribute(s, 1));
    const mat = new THREE.ShaderMaterial({ uniforms: { time: { value: 0 } }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexShader: \`uniform float time; attribute float seed; varying float vA;
        void main() { float ph = fract(seed * 7.13 + time * (0.25 + 0.3 * seed)); vec3 p = position; p.y = ph * (2.5 + 2.0 * seed);
          p.x += sin(time * 1.3 + seed * 40.0) * 0.25 * ph; p.z += cos(time * 1.1 + seed * 30.0) * 0.25 * ph;
          vA = (1.0 - ph) * smoothstep(0.0, 0.08, ph); vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_PointSize = (1.0 + 2.0 * seed) * 22.0 / -mv.z; gl_Position = projectionMatrix * mv; }\`,
      fragmentShader: 'varying float vA; void main() { vec2 q = gl_PointCoord - 0.5; float r = length(q); gl_FragColor = vec4(vec3(0.7, 0.85, 1.0) * 4.0 * vA * smoothstep(0.5, 0.0, r), 1.0); }' });
    const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; return pts;
  }
  const spoonScene = new THREE.Scene();
  const spoon = makeSpoon(260); spoonScene.add(spoon);
  const sparks = makeSparks(50); spoon.add(sparks);
  const key = new THREE.DirectionalLight(new THREE.Color(0.75, 0.85, 1.0), 3.5); key.position.set(-20, 26, -30); spoonScene.add(key);
  spoonScene.add(new THREE.AmbientLight(0x30384a, 0.4));
  const fill = new THREE.DirectionalLight(new THREE.Color(0.6, 0.7, 0.9), 1.2); fill.position.set(-10, 8, 20); spoonScene.add(fill);
  const camSp = new THREE.PerspectiveCamera(38, ${W} / ${H}, 0.1, 1000);

  // ---------- the balance (cm): pivot at y 45, arms 17, pans 23 below the ends ----------
  const ARM = 13, HANG = 21, PR = 7.5;
  const panMat = new THREE.MeshPhysicalMaterial({ color: 0xa88a52, metalness: 1, roughness: 0.35, envMap, envMapIntensity: 0.35 });
  const balScene = new THREE.Scene();
  const brass = new THREE.MeshPhysicalMaterial({ color: 0xd9b46a, metalness: 1, roughness: 0.24, envMap, envMapIntensity: 1.2, clearcoat: 0.4 });
  const dark = new THREE.MeshPhysicalMaterial({ color: 0x1a1c22, metalness: 0.6, roughness: 0.35, envMap });
  const base = new THREE.Mesh(new THREE.CylinderGeometry(5, 6.5, 2.4, 64), dark); base.position.y = 1.2; balScene.add(base);
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.3, 44, 32), brass); post.position.y = 24; balScene.add(post);
  const beamG = new THREE.Group(); beamG.position.y = 45; balScene.add(beamG);
  const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 2 * ARM + 1.6, 24).rotateZ(Math.PI / 2), brass); beamG.add(bar);
  const hub = new THREE.Mesh(new THREE.SphereGeometry(1.7, 32, 16), brass); beamG.add(hub);
  const needle = new THREE.Mesh(new THREE.ConeGeometry(0.5, 9, 16), brass); needle.position.y = 5; beamG.add(needle);
  for (const sx of [-1, 1]) { const k = new THREE.Mesh(new THREE.SphereGeometry(0.9, 24, 12), brass); k.position.x = (ARM + 0.8) * sx; beamG.add(k); }
  function makePan() {
    const g = new THREE.Group();
    const prof = []; for (let i = 0; i <= 24; i++) { const r = PR * i / 24; prof.push(new THREE.Vector2(r, 0.8 * (r / PR) ** 2.2)); }
    panMat.side = THREE.DoubleSide; const dish = new THREE.Mesh(new THREE.LatheGeometry(prof, 96), panMat); g.add(dish);
    for (let k = 0; k < 3; k++) {
      const a = k * 2 * Math.PI / 3 + 0.5, p0 = new THREE.Vector3((PR - 0.4) * Math.cos(a), 0.8, (PR - 0.4) * Math.sin(a)), p1 = new THREE.Vector3(0, HANG, 0);
      const len = p0.distanceTo(p1), c = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, len, 8), brass);
      c.position.copy(p0).add(p1).multiplyScalar(0.5); c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), p1.clone().sub(p0).normalize()); g.add(c);
    }
    return g;
  }
  const panL = makePan(), panR = makePan(); balScene.add(panL, panR);
  const spoonB = makeSpoon(0); spoonB.scale.setScalar(1.3); balScene.add(spoonB);
  const sparksB = makeSparks(60); spoonB.add(sparksB);
  // the heap of people: a body and a head, thousands of them, in a cone on the right pan
  const body = new THREE.CapsuleGeometry(0.085, 0.26, 3, 8); body.translate(0, 0.215, 0);
  const head = new THREE.SphereGeometry(0.075, 10, 8); head.translate(0, 0.47, 0);
  const person = THREE.BufferGeometryUtils.mergeBufferGeometries([body, head]);
  const NP = 7000, people = new THREE.InstancedMesh(person, new THREE.MeshStandardMaterial({ roughness: 0.75, metalness: 0, envMap, envMapIntensity: 0.6 }), NP);
  { const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), c = new THREE.Color(); let rs = 7;
    const rnd = () => { rs = (rs * 16807) % 2147483647; return rs / 2147483647; };
    const pal = [[0.55, 0.12, 0.1], [0.1, 0.22, 0.5], [0.85, 0.75, 0.2], [0.15, 0.4, 0.2], [0.8, 0.8, 0.82], [0.2, 0.2, 0.22], [0.7, 0.35, 0.15], [0.45, 0.2, 0.5], [0.9, 0.5, 0.55], [0.35, 0.55, 0.75]];
    for (let i = 0; i < NP; i++) {
      const rr = (PR - 0.9) * Math.sqrt(rnd()), a = rnd() * 2 * Math.PI, hmax = 5.6 * Math.pow(1 - rr / (PR - 0.6), 1.15);
      const y = 0.7 * (rr / PR) ** 2.2 + hmax * Math.pow(rnd(), 0.35);
      e.set((rnd() - 0.5) * 3.2, rnd() * 6.3, (rnd() - 0.5) * 3.2); q.setFromEuler(e);
      m.compose(new THREE.Vector3(rr * Math.cos(a), y, rr * Math.sin(a)), q, new THREE.Vector3(1, 1, 1).multiplyScalar(0.9 + 0.25 * rnd()));
      people.setMatrixAt(i, m); const p = pal[Math.floor(rnd() * pal.length)]; c.setRGB(p[0], p[1], p[2]); people.setColorAt(i, c);
    }
  }
  panR.add(people);
  const keyB = new THREE.DirectionalLight(new THREE.Color(0.78, 0.86, 1.0), 2.2); keyB.position.set(-40, 60, 50); balScene.add(keyB);
  const rimB = new THREE.DirectionalLight(new THREE.Color(1.0, 0.85, 0.7), 1.2); rimB.position.set(50, 20, -60); balScene.add(rimB);
  balScene.add(new THREE.AmbientLight(0x404858, 0.5));
  const camB = new THREE.PerspectiveCamera(40, ${W} / ${H}, 0.5, 5000);

  // ---------- post: bloom, then ACES, gamma, a vignette and the flash ----------
  const rt = new THREE.WebGLRenderTarget(${W}, ${H}, { type: THREE.HalfFloatType, samples: ${+(process.env.MSAA || 0)} });
  const composer = new THREE.EffectComposer(renderer, rt);
  let drawScene = () => {};
  class MultiPass extends THREE.Pass { constructor() { super(); this.needsSwap = false; }
    render(r, wb, rb) { r.setRenderTarget(rb); r.setClearColor(0x000000, 1); r.clear(); drawScene(r); } }
  composer.addPass(new MultiPass());
  const bloom = new THREE.UnrealBloomPass(new THREE.Vector2(${W}, ${H}), 0.75, 0.55, 0.95); composer.addPass(bloom);
  const fin = new THREE.ShaderPass({ uniforms: { tDiffuse: { value: null }, flash: { value: 0 }, vig: { value: 0.28 } },
    vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: \`uniform sampler2D tDiffuse; uniform float flash, vig; varying vec2 vUv;
      vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
      void main() { vec3 c = texture2D(tDiffuse, vUv).rgb;
        vec2 q = vUv - 0.5; q.y *= 1.4; c *= 1.0 - vig * smoothstep(0.25, 0.85, length(q));
        c = mix(c, vec3(0.85, 0.92, 1.0) * 3.0, flash);
        c = aces(c * 0.9);
        gl_FragColor = vec4(pow(c, vec3(1.0 / 2.2)), 1.0); }\` });
  composer.addPass(fin);

  function setCam(cam, pos, look, fov, up) {
    cam.position.set(pos[0], pos[1], pos[2]); cam.up.set(...(up || [0, 1, 0])); cam.lookAt(look[0], look[1], look[2]);
    if (cam.fov !== fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
    cam.updateMatrixWorld();
  }
  function setStar(s, cam, opts) {
    starU.camWorld.value.copy(cam.matrixWorld); starU.projInv.value.copy(cam.projectionMatrixInverse); starU.camPos.value.copy(cam.position);
    starU.lens.value = s.lens; starU.air.value = s.air; starU.expo.value = s.expo;
    starU.bgK.value = opts.bg; starU.useGround.value = opts.ground ? 1 : 0;
    starU.crabK.value = s.crabK; starU.crabWt.value = s.crabW * D;
    beamU.phi0.value = s.phi - s.dphi / 2; beamU.dphi.value = s.dphi; starU.phiMid.value = s.phi;
    starU.noiseK.value = 1 - Math.min(1, Math.max(0, (s.dphi - 0.4) / 1.2));
    starU.pxAng.value = cam.fov * D / ${H};
    // field lines follow the magnetic axis (local +y -> m, local x -> across, turning with the phase)
    const m = magAxis(s.phi), x = new THREE.Vector3().crossVectors(S, m).normalize(), z = new THREE.Vector3().crossVectors(x, m);
    lines.matrix.makeBasis(x, m, z); lines.matrixAutoUpdate = false; lines.matrixWorldNeedsUpdate = true;
    lineU.camP.value.copy(cam.position); lineU.k.value = s.lines; lineU.time.value = s.t;
  }

  window.__render = (s) => {
    matterU.time.value = s.t; sparks.material.uniforms.time.value = s.t; sparksB.material.uniforms.time.value = s.t;
    fin.uniforms.flash.value = s.flash;
    if (s.mode === 'space') {
      setCam(camS, s.pos, s.look, s.fov);
      setStar(s, camS, { bg: 1 });
      if (s.spoon) {
        setCam(camSp, s.spoon.cam, s.spoon.look, s.spoon.fov);
        spoon.position.set(0, s.spoon.lift, s.spoon.lift * -0.3); spoon.rotation.set(0, s.spoon.yaw, s.spoon.roll);
      }
      drawScene = (r) => {
        r.render(quadScene, camS);
        if (s.lines > 0.001) r.render(linesScene, camS);
        if (s.spoon) { r.clearDepth(); r.render(spoonScene, camSp); }
      };
    } else if (s.mode === 'kyiv') {
      setCam(camK, s.pos, s.look, s.fov);
      camS.position.set(s.pos[0], s.pos[1] - STAR_Y, s.pos[2]); camS.quaternion.copy(camK.quaternion);
      if (camS.fov !== s.fov) { camS.fov = s.fov; camS.updateProjectionMatrix(); } camS.updateMatrixWorld();
      setStar(s, camS, { bg: 0, ground: 1 });
      sky.position.copy(camK.position);
      drawScene = (r) => { r.render(kyiv, camK); r.render(quadScene, camS); if (s.lines > 0.001) r.render(linesScene, camS); };
    } else {
      setCam(camS, s.bg.pos, s.bg.look, s.bg.fov);
      setStar(Object.assign({}, s, { lines: 0 }), camS, { bg: 1 });
      setCam(camB, s.pos, s.look, s.fov);
      const b = s.bal, th = b.theta;
      beamG.rotation.z = th;                           // + : the left end goes down
      panL.position.set(-ARM * Math.cos(th), 45 - ARM * Math.sin(th) - HANG, 0); panR.position.set(ARM * Math.cos(th), 45 + ARM * Math.sin(th) - HANG, 0);
      spoonB.position.set(panL.position.x + 1.2, panL.position.y + 1.0 + b.spoonY, 0.3); spoonB.rotation.set(0, Math.PI - 0.5, 0.0);
      drawScene = (r) => { r.render(quadScene, camS); r.clearDepth(); r.render(balScene, camB); };
    }
    composer.render();
    return renderer.domElement.toDataURL('image/jpeg', 0.95);
  };
  window.ready = 1;
}
setup().catch(e => console.error('setup failed', e.message, e.stack));
</script></body></html>`;

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const srv = await new Promise(res => {
    const s = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      if (u === '/') { rsp.writeHead(200, { 'Content-Type': 'text/html' }); return rsp.end(page); }
      const f = u === '/three.min.js' ? path.join(TOOLS, 'node_modules/three/build/three.min.js')
        : u.startsWith('/ex/') ? path.join(TOOLS, 'node_modules/three/examples/js', u.slice(4))
        : u.startsWith('/w/') ? path.join(WORK, u.slice(3)) : null;
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); return rsp.end(); }
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(s));
  });
  const br = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--js-flags=--max-old-space-size=6000'] });
  const p = await br.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log(m.text().slice(0, 400)); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/`);
  await p.waitForFunction(() => window.ready, null, { timeout: 600000, polling: 500 });
  const save = async (t, file) => {
    const url = await p.evaluate(s => window.__render(s), P.state(t));
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  };
  if (mode === 'stills') {
    for (const t of list.split(',').map(Number)) { const t0 = Date.now(); await save(t, path.join(WORK, `still_${t}.jpg`)); console.log('still', t, ((Date.now() - t0) / 1000).toFixed(1), 's'); }
  } else {
    const dir = path.join(WORK, 'w3d'); fs.mkdirSync(dir, { recursive: true });
    const n0 = Number(list) || 0, n1 = upto ? Number(upto) : Math.round(P.DURATION * P.FPS);
    for (let i = n0; i < n1; i++) {
      const f = path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`);
      if (fs.existsSync(f)) continue;
      await save(i / P.FPS, f); if (i % 30 === 0) console.log('frame', i, '/', n1);
    }
  }
  await br.close(); srv.close();
})();
