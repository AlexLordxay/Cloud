// Небозвід — the Three.js renderer, quality modes, scene helpers, stars and belts.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- Three.js scene ---------- */
const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
/* ---------- Quality ---------- */
// "Economy" swaps 4K maps for 2K ones, lowers the render resolution on dense screens and simplifies the heaviest shaders.
const Q_KEY = "planetarium.quality";
const LARGE_MAPS = new Set(["mercury", "venus", "earth", "moon", "mars", "jupiter", "saturn"]);
function detectLowEnd() {
  try {
    const coarse = matchMedia("(pointer: coarse)").matches && Math.max(screen.width, screen.height) < 1100;
    const mem = navigator.deviceMemory, cores = navigator.hardwareConcurrency;
    // Only clear cases here; anything borderline is caught by the frame-rate check below.
    return coarse || (mem && mem <= 2) || (cores && cores <= 2);
  } catch (e) { return false; }
}
let qualitySetting = "auto";
try { qualitySetting = localStorage.getItem(Q_KEY) || "auto"; } catch (e) { /* storage may be blocked */ }
let autoDegraded = false;
let eco = qualitySetting === "eco" || (qualitySetting === "auto" && detectLowEnd());
const ecoMaterials = [];
const pixelRatio = () => Math.min(devicePixelRatio || 1, eco ? 1.25 : 2);
renderer.setPixelRatio(pixelRatio());
renderer.setSize(innerWidth, innerHeight, false);
renderer.outputEncoding = THREE.sRGBEncoding;
const maxAniso = renderer.capabilities.getMaxAnisotropy();

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x04060c);
const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.5, 8000);
const controls = new THREE.OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.enablePan = false;
controls.rotateSpeed = 0.6;
controls.zoomSpeed = 0.8;

scene.add(new THREE.AmbientLight(0x8fa0c8, 0.14));
const sunLight = new THREE.PointLight(0xfff2e0, 1.7, 0, 0);
scene.add(sunLight);

function toTexture(cv) {
  const t = new THREE.CanvasTexture(cv);
  t.encoding = THREE.sRGBEncoding;
  t.anisotropy = maxAniso;
  return t;
}
function glowSprite(color, size, opacity) {
  const cv = document.createElement("canvas");
  cv.width = cv.height = 256;
  const g = cv.getContext("2d"), grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grd.addColorStop(0, `rgba(${color},1)`);
  grd.addColorStop(0.2, `rgba(${color},0.55)`);
  grd.addColorStop(0.5, `rgba(${color},0.12)`);
  grd.addColorStop(1, `rgba(${color},0)`);
  g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: toTexture(cv), transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending }));
  s.scale.set(size, size, 1);
  return s;
}
function atmosphere(radius, rgb, power, strength) {
  const mat = new THREE.ShaderMaterial({
    uniforms: { c: { value: new THREE.Color(rgb[0], rgb[1], rgb[2]) }, p: { value: power }, k: { value: strength } },
    vertexShader: "varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.0); vP = mv.xyz; gl_Position = projectionMatrix * mv; }",
    fragmentShader: "uniform vec3 c; uniform float p; uniform float k; varying vec3 vN; varying vec3 vP; void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(-vP))), p); gl_FragColor = vec4(c, f * k); }",
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(radius, 64, 48), mat);
}
function ringMesh(inner, outer, map, tint) {
  const geo = new THREE.RingGeometry(inner, outer, 160, 1);
  const pos = geo.attributes.position, uv = geo.attributes.uv, v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    uv.setXY(i, (v.length() - inner) / (outer - inner), 0.5);
  }
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map, color: tint, side: THREE.DoubleSide, transparent: true, depthWrite: false }));
  m.rotation.x = -PI / 2;
  return m;
}
function beltPoints(n, rMin, rMax, height, color, size, opacity) {
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const a = Math.random() * TAU, r = rMin + (rMax - rMin) * Math.pow(Math.random(), 0.8);
    pos[i * 3] = Math.cos(a) * r; pos[i * 3 + 1] = (Math.random() + Math.random() - 1) * height; pos[i * 3 + 2] = Math.sin(a) * r;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color, size, sizeAttenuation: false, transparent: true, opacity, depthWrite: false }));
  scene.add(p);
  return p;
}

// Starfield
(() => {
  const n = 7000, pos = new Float32Array(n * 3), col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const u = Math.random() * 2 - 1, t = Math.random() * TAU, r = Math.sqrt(1 - u * u), R = 2600 + Math.random() * 800;
    pos[i * 3] = r * Math.cos(t) * R; pos[i * 3 + 1] = u * R; pos[i * 3 + 2] = r * Math.sin(t) * R;
    const b = 0.35 + Math.pow(Math.random(), 3) * 0.65, tint = Math.random();
    col[i * 3] = b * (tint > 0.8 ? 1 : 0.85); col[i * 3 + 1] = b * 0.9; col[i * 3 + 2] = b * (tint < 0.3 ? 1 : 0.85);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  scene.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true })));
})();
const asteroidBelt = beltPoints(4000, 50, 58, 1.2, 0xa89a88, 1.4, 0.7);
const kuiperBelt = beltPoints(3500, 152, 200, 7, 0x8fa0bc, 1.3, 0.45);
