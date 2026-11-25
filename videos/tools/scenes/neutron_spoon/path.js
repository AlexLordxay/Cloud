// «Ложка нейтронної зорі»: the timeline. Voice (scene.json parts) starts at 0.3 s; the shots:
//   S1 0–4.4    a teaspoon of the star's matter, the star behind it ("Чайна ложка цієї зорі важить мільярд тонн")
//   S2 4.4–8.3  fly in to the star, then far out until it is the pulsar in the Crab Nebula ("ядро зорі, що вибухнула")
//   S3 8.3–14.7 the star (true size, 20 km) over Kyiv ("важча за Сонце, але менша за Київ")
//   S4 14.7–22.1 a balance: the spoon outweighs a heap of people ("більше, ніж усі люди на Землі разом")
//   S5 22.1–27  the star spins up to 716 turns a second ("понад сімсот разів за секунду")
//   S6 27–34    out to the Crab again, the question, the end card
// Units: the star's world in km (star at the origin, R 10 km); Kyiv's in km (ground y = 0, north −z, star at y 26);
// the spoon's and the balance's in cm.
const DURATION = 34.0, FPS = 30;
const W0 = (process.env.W0 || '42,40,66,-2,31,0').split(',').map(Number), W1 = (process.env.W1 || '38,38,62,1,30,0').split(',').map(Number);
const R = 10, RS = 4.13;                      // 20 km across, 1.4 Suns -> Schwarzschild radius 4.13 km
const STAR_Y = 26;                           // the star's centre over Kyiv, km
const CUT = [4.4, 8.3, 14.7, 22.1, 27.0];
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const smooth = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
const ease = x => { x = clamp(x, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const lerp = (a, b, k) => a + (b - a) * k;
const lerpV = (a, b, k) => a.map((v, i) => lerp(v, b[i], k));
const lerpLog = (a, b, k) => Math.exp(lerp(Math.log(a), Math.log(b), k));
const sph = (d, az, el) => [d * Math.cos(el) * Math.sin(az), d * Math.sin(el), d * Math.cos(el) * Math.cos(az)];

// spin rate, turns per second: slow and readable, then (S5) up to 716
function rate(t) {
  if (t < 22.5) return 0.45;
  if (t < 26.0) return Math.min(716, 0.45 * Math.exp(Math.log(716 / 0.45) * ease((t - 22.5) / 3.5)));
  return 716;
}
// the phase is the integral of the rate (fine steps, cached)
const PH = []; { let p = 0; const dt = 1 / 600; for (let i = 0; i <= DURATION * 600 + 10; i++) { PH.push(p); p += 2 * Math.PI * rate(i * dt) * dt; } }
const phase = t => { const k = clamp(t, 0, DURATION) * 600, i = Math.floor(k); return lerp(PH[i], PH[i + 1], k - i); };

function state(t) {
  const s = { t, mode: 'space', fov: 40, up: [0, 1, 0], lens: 1, air: 0, lines: 1, crabK: 0, crabW: 30, expo: 1, spoon: null, bal: null, flash: 0 };
  const r = rate(t);
  s.rate = r; s.phi = phase(t) % (2 * Math.PI);
  s.dphi = Math.max(0.03, Math.min(2 * Math.PI, 2 * Math.PI * r / FPS * 0.5));   // a 180° shutter
  for (const c of [CUT[1], CUT[2], CUT[3]]) s.flash = Math.max(s.flash, Math.exp(-Math.abs(t - c) / 0.07) * (t < c ? 0.55 : 1));
  if (t < CUT[0]) {
    // S1: the spoon close up; the star 150 km away above it, drifting a little
    const k = t / CUT[0];
    s.pos = sph(lerp(165, 140, k), lerp(-0.25, -0.18, k), lerp(0.05, 0.07, k)); s.look = [0, -34, 0]; s.fov = 42;
    const out = smooth((t - 3.9) / 0.6);
    s.spoon = { cam: [lerp(-6.0, -5.2, k), lerp(5.6, 5.0, k), lerp(17.5, 15.5, k)], look: [1.2, 0.4, 0], fov: 38, yaw: lerp(-0.95, -0.85, k), roll: 0.04, lift: -out * 9, glow: 1 };
  } else if (t < CUT[1]) {
    // S2: in to 42 km, a quarter turn round it, then the long pull out (log) into the Crab Nebula
    const a = smooth((t - CUT[0]) / 1.9), b = ease((t - 6.3) / 2.0);
    const az = lerp(-0.18, 0.55, smooth((t - CUT[0]) / 3.9)), el = lerp(0.07, 0.22, a);
    const d = t < 6.3 ? lerp(140, 56, ease((t - CUT[0]) / 1.9)) : lerpLog(56, 4e7, b);
    s.pos = sph(d, az, el); s.look = [0, lerp(-6, 0, a), 0]; s.fov = 40;
    s.lines = 1 - smooth((d - 400) / 3000);
    s.crabK = smooth((t - 7.0) / 0.9); s.crabW = lerpLog(900, 26, smooth((t - 6.6) / 1.75));
    if (t < CUT[0] + 0.5) s.spoon = { cam: [-5.2, 5.0, 15.5], look: [1.2, 0.4, 0], fov: 38, yaw: -0.85, roll: 0.04, lift: -9, glow: 1 };
  } else if (t < CUT[2]) {
    // S3: over Kyiv; true size, so no lensing (a 20 km disc)
    s.mode = 'kyiv'; s.lens = 0; s.air = 1; s.fov = 50;
    const k = ease((t - CUT[1]) / 3.6), k2 = smooth((t - 11.9) / 2.8);
    s.pos = lerpV(lerpV([-40, 150, 150], [-18, 52, 86], k), [14, 44, 80], k2);
    s.look = lerpV([0, 12, 0], [0, 17, 0], k);
    s.lines = 0.55;
  } else if (t < CUT[3]) {
    // S4: the balance (cm). Close on the spoon, out to the whole balance, the spoon lands at 18.75, the beam tips
    s.mode = 'balance';
    const land = 18.75;
    const drop = t < land ? 0 : 1;
    const th0 = -0.11, th1 = 0.30;
    let th = th0;
    if (t > land) { const u = t - land; th = th1 + (th0 - th1) * Math.exp(-3.2 * u) * Math.cos(9 * u); }
    const spoonY = t < 18.25 ? 9 : t < land ? lerp(9, 0, Math.pow((t - 18.25) / 0.5, 2)) : 0;
    s.bal = { theta: th, spoonY, glow: 1 };
    // camera
    const c1 = ease((t - 17.1) / 1.5), c2 = smooth((t - 18.8) / 3.3);
    const close = { pos: [-12 + 19 * Math.sin(0.35 + 0.10 * (t - CUT[2])), 37.5, 19 * Math.cos(0.35 + 0.10 * (t - CUT[2]))], look: [-12, 36.0, 0] };
    const wide = { pos: [W0[0], W0[1], W0[2]], look: [W0[3], W0[4], W0[5]] }, end = { pos: [W1[0], W1[1], W1[2]], look: [W1[3], W1[4], W1[5]] };
    s.pos = lerpV(lerpV(close.pos, wide.pos, c1), end.pos, c2); s.look = lerpV(lerpV(close.look, wide.look, c1), end.look, c2);
    s.fov = lerp(34, 40, c1);
    s.bg = { pos: sph(1100, 0.35 + 0.05 * (t - CUT[2]) / 7, 0.18), look: [190, -330, 0], fov: 40 };
  } else if (t < CUT[4]) {
    // S5: close; the spin-up; a slow drift round
    const k = (t - CUT[3]) / (CUT[4] - CUT[3]);
    s.pos = sph(lerp(70, 95, smooth(k)), lerp(0.9, 1.25, k), lerp(0.16, 0.30, k)); s.look = [0, -3, 0]; s.fov = 40;
    s.lines = 1 - smooth((r - 1.5) / 3);
    const sh = smooth((r - 30) / 300) * 0.25;           // a faint shake once it is a blur
    s.pos = s.pos.map((v, i) => v + sh * Math.sin(t * (37 + 11 * i) + i));
  } else {
    // S6: out to the Crab, slowly, then held under the question and the end card
    const b = ease((t - CUT[4]) / 3.2);
    s.pos = sph(lerpLog(95, 4e7, b), lerp(1.25, 1.5, smooth((t - CUT[4]) / 7)), lerp(0.3, 0.2, b)); s.look = [0, 0, 0]; s.fov = 40;
    s.lines = 0;
    s.crabK = smooth((t - 28.0) / 1.0); s.crabW = lerpLog(900, 28, smooth((t - 27.6) / 2.4)) * (1 - 0.04 * smooth((t - 29.6) / 4.4));
  }
  return s;
}

// a camera's view of a point: [x px, y px, depth] on the 720 × 1280 frame
function project(cam, p) {
  const f = cam.pos, l = cam.look;
  const z = norm(sub(f, l)), x = norm(cross([0, 1, 0], z)), y = cross(z, x);
  const d = sub(p, f), cx = dot(d, x), cy = dot(d, y), cz = -dot(d, z);
  const fpx = 640 / Math.tan(cam.fov * Math.PI / 360);
  return [360 + cx / cz * fpx, 640 - cy / cz * fpx, cz];
}
function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(a) { const n = Math.hypot(...a); return a.map(v => v / n); }

module.exports = { DURATION, FPS, R, RS, STAR_Y, CUT, state, project, rate };
