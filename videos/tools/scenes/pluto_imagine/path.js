// The camera and the timed events of the one continuous flight (world3d.js), timed to the voice (voice.mp3 starts at
// 0.3 s; phrases: hook 0.3–3.25, «А ти уявляєш…» 3.7–5.4, Moon 5.8–11.4, heart 11.8–18.4, mountains 18.8–23.1,
// haze 23.6–29.0, weight 29.4–34.2, year 34.6–43.5, «Перешли…» 43.9–47.6, end card 47.9).
// Keys: t, pos (geo [lat, lon, alt km] or {xyz}), look (geo or {xyz}), up ('north' | 'radial' | mix 0…1), fov.
// Between keys: camera direction from Pluto's centre and log(distance) on a Catmull-Rom spline, so the long falls and
// climbs have no jumps in speed; the view direction and up likewise (slerped through unit vectors).
const D = Math.PI / 180, R = 1188.3;
const P = (lat, lon) => [Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D)];
const add = (a, b) => a.map((v, i) => v + b[i]), sub = (a, b) => a.map((v, i) => v - b[i]), mul = (a, k) => a.map(v => v * k);
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], len = a => Math.hypot(...a), norm = a => mul(a, 1 / len(a));
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const geo = (lat, lon, alt) => mul(P(lat, lon), R + alt);
const HEART = [18, 192], SPUT = [20, 178], TEN = [-15.6, 177.4];
const DURATION = 50.6;

// the Moon beside Pluto (true size), below it in the frame of the "sizes" moment
const V0 = P(16, 205);                                   // the view direction from Pluto toward the camera then
const UP0 = norm(sub([0, 1, 0], mul(V0, V0[1])));
const MOON = mul(UP0, -(R + 1737.4 + 900));
const PAIR_MID = mul(UP0, -(R + 1737.4 + 900 + 1737.4 - R) / 2);

const KEYS = [
  // hook: the heart facing us, Ukraine laid on it; a slow push
  { t: 0.0, pos: { xyz: mul(P(17, 200), R + 5600) }, look: { xyz: [0, 0, 0] }, up: 'north', fov: 40 },
  { t: 3.4, pos: { xyz: mul(P(17, 202), R + 4300) }, look: { xyz: mul(P(HEART[0], HEART[1]), 250) }, up: 'north', fov: 40 },
  // «А ти уявляєш…»: drawing back, turning a little
  { t: 5.6, pos: { xyz: mul(P(16, 204), R + 7000) }, look: { xyz: mul(UP0, -900) }, up: 'north', fov: 40 },
  // Pluto and the Moon side by side (stacked in the tall frame)
  { t: 8.0, pos: { xyz: add(PAIR_MID, mul(V0, 10200)) }, look: { xyz: PAIR_MID }, up: 'north', fov: 40 },
  { t: 11.2, pos: { xyz: add(PAIR_MID, mul(V0, 10000)) }, look: { xyz: PAIR_MID }, up: 'north', fov: 40 },
  // into the heart: down onto Sputnik Planitia
  { t: 13.6, pos: geo(28, 190, 2600), look: geo(SPUT[0], SPUT[1], 0), up: 'north', fov: 44 },
  { t: 16.2, pos: geo(22, 182, 420), look: geo(10, 178, 0), up: 0.6, fov: 50 },
  { t: 18.6, pos: geo(12, 179, 110), look: geo(-6, 177.5, 0), up: 'radial', fov: 52 },
  // along the plain to its shore, Tenzing Montes rising ahead
  { t: 21.0, pos: geo(-4, 177.9, 38), look: geo(-14.5, 177.0, 2), up: 'radial', fov: 52 },
  { t: 23.4, pos: geo(-10.6, 177.5, 11), look: geo(-15.4, 177.2, 3), up: 'radial', fov: 52 },
  // turning toward the Sun: the haze along the horizon, the tiny Sun
  { t: 26.2, pos: geo(-13.8, 176.2, 10), look: geo(-11.2, 181.0, 4), up: 'radial', fov: 52 },
  { t: 29.2, pos: geo(-15.0, 175.8, 9), look: geo(-12.0, 180.8, 4), up: 'radial', fov: 52 },
  // weight: a slow glide over the peaks
  { t: 34.0, pos: geo(-16.4, 176.6, 9.0), look: geo(-13.2, 179.8, 3), up: 'radial', fov: 52 },
  // the year: climbing out, turning to look back down at Pluto, far out until it is a point
  { t: 36.2, pos: geo(-15.6, 178.5, 420), look: geo(-12, 180, 0), up: 0.4, fov: 50 },
  { t: 38.4, pos: geo(-10, 186, 14000), look: { xyz: [0, 0, 0] }, up: 'north', fov: 40 },
  { t: 43.4, pos: geo(-8, 192, 90000), look: { xyz: [0, 0, 0] }, up: 'north', fov: 40 },
  // back to Pluto for the last line
  { t: 45.6, pos: geo(14, 205, 7600), look: { xyz: [0, 0, 0] }, up: 'north', fov: 40 },
  { t: 50.6, pos: geo(13, 214, 6400), look: { xyz: [0, 0, 0] }, up: 'north', fov: 40 },
];

const posOf = k => Array.isArray(k.pos) ? k.pos : k.pos.xyz;
const lookOf = k => Array.isArray(k.look) ? k.look : k.look.xyz;
function upOf(k, pos) {
  const north = [0, 1, 0], radial = norm(pos);
  const w = k.up === 'radial' ? 1 : k.up === 'north' ? 0 : k.up;
  return norm(add(mul(north, 1 - w), mul(radial, w)));
}
const cr = (a, b, c, d, u) => 0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (3 * b - a - 3 * c + d) * u * u * u);
const crv = (a, b, c, d, u) => a.map((_, i) => cr(a[i], b[i], c[i], d[i], u));
const smooth = (a, b, x) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };

function cam(t) {
  const K = KEYS, last = K.length - 1;
  let i = 0; while (i < last - 1 && t > K[i + 1].t) i++;
  const ks = [K[Math.max(i - 1, 0)], K[i], K[Math.min(i + 1, last)], K[Math.min(i + 2, last)]];
  const u = Math.min(1, Math.max(0, (t - ks[1].t) / Math.max(ks[2].t - ks[1].t, 1e-6)));
  const ps = ks.map(posOf);
  const dirs = ps.map(norm), lds = ps.map(p => Math.log(len(p) - R + 3));
  const dir = norm(crv(...dirs, u)), alt = Math.exp(cr(...lds, u)) - 3;
  const pos = mul(dir, R + Math.max(alt, 0.8));
  const look = crv(...ks.map(lookOf), u);
  const view = norm(sub(look, pos));
  const ups = ks.map((k, j) => upOf(k, ps[j]));
  let up = norm(crv(...ups, u)); up = norm(sub(up, mul(view, dot(up, view))));
  const fov = cr(...ks.map(k => k.fov), u);
  return { pos, look: add(pos, mul(view, 1000)), up, fov, alt: len(pos) - R };
}

function state(t) {
  const c = cam(t);
  const lowness = 1 - smooth(60, 400, c.alt);                     // inside the haze
  return {
    pos: c.pos, look: c.look, up: c.up, fov: c.fov,
    expo: 1.0 + 0.8 * lowness - 0.12 * smooth(23.6, 26.5, t) * (1 - smooth(29.5, 31.0, t)),   // «полудень як сутінки»: a touch dimmer
    atmo: lowness,
    haze: 1.0 + 0.6 * lowness,
    ua: smooth(0.6, 1.4, t) * (1 - smooth(4.6, 5.4, t)),
    moon: smooth(5.9, 7.2, t) * (1 - smooth(11.4, 12.4, t)),
    moonPos: MOON,
  };
}

// where a world point lands in the 720×1280 frame (for labels laid on afterwards)
function project(t, p, W = 720, H = 1280) {
  const c = cam(t), f = norm(sub(c.look, c.pos)), r = norm(cross(f, c.up)), u = cross(r, f);
  const d = sub(p, c.pos), z = dot(d, f);
  const k = (H / 2) / Math.tan(c.fov * D / 2);
  return [W / 2 + dot(d, r) / z * k, H / 2 - dot(d, u) / z * k, z];
}
module.exports = { state, project, DURATION, MOON, R };
