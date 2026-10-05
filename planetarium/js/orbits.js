// Небозвід — real positions: dates, orbital elements, the Moon, the distance scale.
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- Real positions: date and orbital elements ---------- */
const J2000 = 2451545.0;
const jdOf = ms => ms / 86400000 + 2440587.5;
// JPL "Approximate Positions of the Planets" (E. M. Standish), valid 1800–2050.
// [a (AU), e, I, L, long. of perihelion, long. of node] at J2000 (deg), and their rates per Julian century.
const JPL = {
  mercury: [[0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593], [0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081]],
  venus: [[0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255], [0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418]],
  earth: [[1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0], [0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0]],
  mars: [[1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891], [0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343]],
  jupiter: [[5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909], [-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106]],
  saturn: [[9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448], [-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794]],
  uranus: [[19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503], [-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589]],
  neptune: [[30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574], [0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664]],
  pluto: [[39.48211675, 0.24882730, 17.14001206, 238.92903833, 224.06891629, 110.30393684], [-0.00031596, 0.00005170, 0.00004818, 145.20780515, -0.04062942, -0.01183482]],
};
// Osculating elements (a, e, i, node, argument of perihelion, mean anomaly at epoch), approximate.
const KEP = {
  ceres: { a: 2.7691651, e: 0.0760090, i: 10.59407, node: 80.30553, peri: 73.59764, M: 77.37209, epoch: 2459000.5 },
  haumea: { a: 43.116, e: 0.19642, i: 28.2137, node: 122.167, peri: 239.041, M: 218.205, epoch: 2459000.5 },
  makemake: { a: 45.430, e: 0.16126, i: 28.9835, node: 79.620, peri: 294.834, M: 165.514, epoch: 2459000.5 },
  eris: { a: 67.864, e: 0.43607, i: 44.040, node: 35.951, peri: 151.639, M: 205.989, epoch: 2459000.5 },
  // 1P/Halley: perihelion 9 Feb 1986; a chosen so the next perihelion falls in mid-2061.
  halley: { a: 17.86, e: 0.96714, i: 162.26, node: 58.42, peri: 111.33, M: 0, epoch: 2446470.96 },
  // 67P/Churyumov–Gerasimenko: timed on its real perihelia (13 Aug 2015, 2 Nov 2021),
  // so both passages land on their true dates despite Jupiter's small nudges to the orbit.
  cg67p: { a: 3.4630, e: 0.6405, i: 7.0405, node: 50.147, peri: 12.780, M: 0, epoch: 2459520.55, perihelia: [2457247.59, 2459520.55] },
  // C/1995 O1 Hale–Bopp: perihelion 1 Apr 1997 at q = 0.914 AU; a set for the ~2400-year period after its 1996 pass by Jupiter.
  halebopp: { a: 179, e: 0.994893, i: 89.429, node: 282.471, peri: 130.589, M: 0, epoch: 2450539.64 },
};
function elementsAt(id, jd) {
  const j = JPL[id];
  if (j) {
    const T = (jd - J2000) / 36525, v = j[0], r = j[1];
    const wb = v[4] + r[4] * T, node = v[5] + r[5] * T;
    return { a: v[0] + r[0] * T, e: v[1] + r[1] * T, i: v[2] + r[2] * T, node, peri: wb - node, M: v[3] + r[3] * T - wb };
  }
  const k = KEP[id], n = 0.9856076686 / Math.pow(k.a, 1.5);
  let M = k.M + n * (jd - k.epoch);
  if (k.perihelia) {
    // Between two known perihelia, spread one full orbit evenly over the real interval (continuous at both ends);
    // outside them, run on from the nearest one at the mean rate.
    const p = k.perihelia;
    if (jd < p[0]) M = n * (jd - p[0]);
    else if (jd >= p[p.length - 1]) M = n * (jd - p[p.length - 1]);
    else for (let i = 0; i < p.length - 1; i++) if (jd < p[i + 1]) { M = 360 * (jd - p[i]) / (p[i + 1] - p[i]); break; }
  }
  return { a: k.a, e: k.e, i: k.i, node: k.node, peri: k.peri, M };
}
// Kepler's equation E − e·sin E = M for M in [−π, π]. The left side is monotonic there, so bisection always converges,
// even for comet-like eccentricities where Newton's method can jump between branches.
function solveKepler(M, e) {
  let lo = -PI, hi = PI;
  for (let k = 0; k < 52; k++) {
    const E = (lo + hi) / 2;
    if (E - e * Math.sin(E) - M > 0) hi = E; else lo = E;
  }
  return (lo + hi) / 2;
}
// Heliocentric ecliptic position (AU) for eccentric anomaly E, in scene axes: x → vernal equinox, y → ecliptic north.
function posFromE(el, E, out) {
  const w = el.peri * DEG, O = el.node * DEG, I = el.i * DEG;
  const xp = el.a * (Math.cos(E) - el.e), yp = el.a * Math.sqrt(1 - el.e * el.e) * Math.sin(E);
  const cw = Math.cos(w), sw = Math.sin(w), cO = Math.cos(O), sO = Math.sin(O), cI = Math.cos(I), sI = Math.sin(I);
  const x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp;
  const y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp;
  const z = sw * sI * xp + cw * sI * yp;
  return out.set(x, z, -y);
}
function helioAU(id, jd, out) {
  const el = elementsAt(id, jd);
  let M = (el.M % 360) * DEG;
  if (M > PI) M -= TAU;
  if (M < -PI) M += TAU;
  return posFromE(el, solveKepler(M, el.e), out);
}
// Stylised distance scale: real AU → scene units. Monotonic, interpolated in log(AU), so order and eccentricity stay true.
const DIST = [[0.05, 11], [0.2, 15], [0.387, 20], [0.723, 28], [1, 37], [1.524, 46], [2.2, 51], [2.77, 54], [3.3, 57], [5.2, 72], [9.54, 104], [19.19, 132], [30.07, 150], [39.5, 170], [43.1, 182], [45.4, 190], [67.8, 205], [100, 218], [300, 240], [400, 246]];
// The table is only a guide: its slope (scene units per ln AU) jumps from knot to knot, and a comet crossing a jump
// would visibly bend. So the slope is smoothed with a Gaussian (σ = 0.12 in ln AU) and integrated once at start-up;
// the bodies move by at most ~2 % of their distance, and every orbit stays smooth.
const DIST_X0 = Math.log(DIST[0][0]), DIST_H = (Math.log(DIST[DIST.length - 1][0]) - DIST_X0) / 4000;
const DIST_F = (() => {
  const n = 4000, h = DIST_H, raw = new Float64Array(n + 1), f = new Float64Array(n + 1);
  const linear = x => {
    for (let k = 1; k < DIST.length; k++) {
      const x1 = Math.log(DIST[k][0]);
      if (x <= x1 || k === DIST.length - 1) {
        const x0 = Math.log(DIST[k - 1][0]);
        return (DIST[k][1] - DIST[k - 1][1]) / (x1 - x0);
      }
    }
  };
  for (let i = 0; i <= n; i++) raw[i] = linear(DIST_X0 + i * h);
  const sigma = 0.12, R = Math.ceil(3 * sigma / h), g = [];
  for (let j = -R; j <= R; j++) g.push(Math.exp(-0.5 * (j * h / sigma) ** 2));
  let prev = 0;
  for (let i = 0; i <= n; i++) {
    let sum = 0, w = 0;
    for (let j = -R; j <= R; j++) { const k = Math.min(n, Math.max(0, i + j)); sum += g[j + R] * raw[k]; w += g[j + R]; }
    const slope = sum / w;
    f[i] = i === 0 ? DIST[0][1] : f[i - 1] + (prev + slope) / 2 * h;
    prev = slope;
  }
  return f;
})();
function sceneDist(au) {
  const u = (Math.log(Math.max(au, 1e-9)) - DIST_X0) / DIST_H;
  if (u <= 0) return DIST_F[0];
  if (u >= DIST_F.length - 1) return DIST_F[DIST_F.length - 1];
  const i = Math.floor(u), t = u - i;
  return DIST_F[i] + (DIST_F[i + 1] - DIST_F[i]) * t;
}
function toScene(vAU, out) {
  const r = vAU.length();
  return out.copy(vAU).multiplyScalar(r > 0 ? sceneDist(r) / r : 0);
}
// Greenwich mean sidereal time (rad): which meridian faces the vernal equinox.
const gmst = jd => ((280.46061837 + 360.98564736629 * (jd - J2000)) % 360) * DEG;
// Moon (Meeus, ch. 47, main periodic terms): geocentric ecliptic longitude/latitude (rad, J2000 frame) and distance (km).
const MOON_LON = [[0,0,1,0,6.288774],[2,0,-1,0,1.274027],[2,0,0,0,0.658314],[0,0,2,0,0.213618],[0,1,0,0,-0.185116],[0,0,0,2,-0.114332],[2,0,-2,0,0.058793],[2,-1,-1,0,0.057066],[2,0,1,0,0.053322],[2,-1,0,0,0.045758],[0,1,-1,0,-0.040923],[1,0,0,0,-0.034720],[0,1,1,0,-0.030383],[2,0,0,-2,0.015327],[0,0,1,2,-0.012528],[0,0,1,-2,0.010980],[4,0,-1,0,0.010675],[0,0,3,0,0.010034],[4,0,-2,0,0.008548],[2,1,-1,0,-0.007888],[2,1,0,0,-0.006766],[1,0,-1,0,-0.005163],[1,1,0,0,0.004987],[2,-1,1,0,0.004036],[2,0,2,0,0.003994],[4,0,0,0,0.003861],[2,0,-3,0,0.003665],[0,1,-2,0,-0.002689],[2,0,-1,2,-0.002602],[2,-1,-2,0,0.002390],[1,0,1,0,-0.002348],[2,-2,0,0,0.002236],[0,1,2,0,-0.002120],[0,2,0,0,-0.002069]];
const MOON_DIST = [[0,0,1,0,-20905.355],[2,0,-1,0,-3699.111],[2,0,0,0,-2955.968],[0,0,2,0,-569.925],[0,1,0,0,48.888],[0,0,0,2,-3.149],[2,0,-2,0,246.158],[2,-1,-1,0,-152.138],[2,0,1,0,-170.733],[2,-1,0,0,-204.586],[0,1,-1,0,-129.620],[1,0,0,0,108.743],[0,1,1,0,104.755],[2,0,0,-2,10.321],[0,0,1,-2,79.661],[4,0,-1,0,-34.782],[0,0,3,0,-23.210],[4,0,-2,0,-21.636],[2,1,-1,0,24.208],[2,1,0,0,30.824],[1,0,-1,0,-8.379],[1,1,0,0,-16.675],[2,-1,1,0,-12.831],[2,0,2,0,-10.445],[4,0,0,0,-11.650],[2,0,-3,0,14.403],[0,1,-2,0,-7.003],[2,-1,-2,0,10.056],[1,0,1,0,6.322],[2,-2,0,0,-9.884],[0,1,2,0,5.751]];
const MOON_LAT = [[0,0,0,1,5.128122],[0,0,1,1,0.280602],[0,0,1,-1,0.277693],[2,0,0,-1,0.173237],[2,0,-1,1,0.055413],[2,0,-1,-1,0.046271],[2,0,0,1,0.032573],[0,0,2,1,0.017198],[2,0,1,-1,0.009266],[0,0,2,-1,0.008822],[2,-1,0,-1,0.008216],[2,0,-2,-1,0.004324],[2,0,1,1,0.004200]];
function moonPos(jd) {
  const T = (jd - J2000) / 36525;
  const Lp = 218.3164477 + 481267.88123421 * T, D = 297.8501921 + 445267.1114034 * T, M = 357.5291092 + 35999.0502909 * T;
  const Mp = 134.9633964 + 477198.8675055 * T, F = 93.2720950 + 483202.0175233 * T;
  const E = 1 - 0.002516 * T;
  const arg = t => (t[0] * D + t[1] * M + t[2] * Mp + t[3] * F) * DEG, ecc = t => Math.pow(E, Math.abs(t[1]));
  let lon = Lp, lat = 0, dist = 385000.56;
  for (const t of MOON_LON) lon += t[4] * ecc(t) * Math.sin(arg(t));
  for (const t of MOON_LAT) lat += t[4] * ecc(t) * Math.sin(arg(t));
  for (const t of MOON_DIST) dist += t[4] * ecc(t) * Math.cos(arg(t));
  // Meeus gives the equinox of date; planets use J2000, so remove general precession (≈1.397° per century).
  lon -= 1.3969713 * T;
  return { lon: lon * DEG, lat: lat * DEG, dist };
}
// Galilean moons: mean longitudes (Meeus), good to a few degrees. Other moons use their real period with an arbitrary phase.
const GALILEAN = { io: [106.07719, 203.48895579], europa: [175.73161, 101.374724735], ganymede: [120.55883, 50.317609207], callisto: [84.44459, 21.571071177] };
// Sidereal rotation periods (days); negative = retrograde.
const ROT = { sun: 25.38, mercury: 58.646, venus: -243.02, earth: 0.99727, mars: 1.02596, jupiter: 0.41354, saturn: 0.44401, uranus: -0.71833, neptune: 0.67125, ceres: 0.3781, pluto: -6.3872, haumea: 0.1631, makemake: 0.9511, eris: 15.786, halley: 2.2, cg67p: 0.517, halebopp: 0.47 };
const clampAbs = (x, m) => x > m ? m : x < -m ? -m : x;
