// "An astronaut on Mars": the Nebozvid astronaut walks up a gentle slope towards a ridge at sunset (the Martian dusk is
// blue round the Sun), and on the crest plants the Nebozvid flag. Its own three.js scene drawn by __recRender.
//
// The ground is one deterministic height function H(x, z) (units ~ metres, the figure is ~1.9 tall, facing -z): a
// broad hill rising along the path to a crest at z ~ -4.6, beyond it a slope down into a wide valley, and far off the
// mountains of a crater's rim in the haze; on top, rolling noise, rock slabs (ridged noise cut into steps), craters
// with raised rims on three scales and sand ripples in the low places. Two meshes: a fine one round the path (0.1 apart)
// and a polar one out to the horizon. The terrain's own shadows (the Sun is low, they are long) are baked into the
// vertices by marching towards the Sun; the figure and the rocks cast real shadows (one shadow map).
// The walk: footprints laid out in time, each foot pinned to its print while it stands and swung on an arc between
// prints, the legs solved by two-bone IK in the side plane, the pelvis riding between the feet with a soft bounce.
(() => {
  const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

  // ---------------- the ground ----------------
  const hash2 = (i, j) => { let h = (Math.imul(i, 374761393) + Math.imul(j, 668265263)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
  function vn(x, z) {
    const i = Math.floor(x), j = Math.floor(z), fx = x - i, fz = z - j, u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
    const a = hash2(i, j), b = hash2(i + 1, j), c = hash2(i, j + 1), d = hash2(i + 1, j + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  const fbm = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { s += a * (vn(x * f + 17 * k, z * f - 9 * k) - 0.5); a *= 0.5; f *= 2.03; } return s; };
  const ridged = (x, z, n) => { let s = 0, a = 1, f = 1; for (let k = 0; k < n; k++) { const r = 1 - Math.abs(2 * vn(x * f + 5 * k, z * f + 11 * k) - 1); s += a * r * r; a *= 0.5; f *= 2.1; } return s / 1.75; };
  // craters: at most one in each cell of a grid (size C), radius between r0 and r1; d = distance / radius
  const craterShape = d => d < 1 ? 0.2 * (d * d - 1) + 0.055 * Math.exp(-(((d - 1) / 0.22) ** 2)) : 0.055 * Math.exp(-(((d - 1) / 0.4) ** 2));
  function craters(x, z, C, r0, r1, p, seed) {
    const ci = Math.floor(x / C), cj = Math.floor(z / C); let s = 0;
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) {
      if (hash2(i + seed, j) > p) continue;
      const cx = (i + hash2(i, j + seed)) * C, cz = (j + hash2(i - seed, j)) * C, r = r0 + (r1 - r0) * hash2(j, i + seed) ** 2;
      const d = Math.hypot(x - cx, z - cz) / r; if (d > 2.2) continue;
      s += r * craterShape(d) * (0.55 + 0.45 * hash2(i + 3 * seed, j + 7));   // older ones softer
    }
    return s;
  }
  const RIDGE = -4.6;
  const ridgeZ = x => RIDGE + 0.5 * Math.sin(x * 0.23 + 0.4) + 0.25 * Math.sin(x * 0.61);
  // the path: a calm strip along x ~ 0 (no rocks, small features damped)
  const pathMask = (x, z) => 1 - (1 - smooth((Math.abs(x) - 0.9) / 1.6)) * (1 - smooth((z - 16) / 3)) * (1 - smooth((-z - 6) / 1.5));
  function H(x, z) {
    const dz = z - ridgeZ(x);
    // the hill: up along the path to the crest, then down into the valley
    let h = dz > 0 ? 1.3 * (1 - Math.min(1, dz / 19) ** 2) : 1.3 - 6.5 * (1 - Math.exp(-dz * dz / 60));
    h -= 0.004 * x * x * smooth(dz / 4) * (1 - smooth((Math.abs(x) - 12) / 10));   // the hill's back rounds off to the sides
    const r = Math.hypot(x, z + 40);
    h += 2.2 * fbm(x * 0.045, z * 0.045, 3) * smooth((r - 10) / 30) + 0.5 * fbm(x * 0.13, z * 0.13, 3);
    const m = pathMask(x, z);
    // rock outcrops: ridged noise lifted in soft-edged layers, on the hillsides and in the valley
    const rg = ridged(x * 0.11 + 3, z * 0.11, 3);
    h += (0.22 * smooth((rg - 0.5) / 0.14) + 0.07 * smooth((rg - 0.68) / 0.08)) * (0.25 + 0.75 * m);
    // dunes on the valley floor: long crests across the wind, a gentle back and a steeper lee face
    { const ph = (x * 0.3 + z * 0.95) / 7 + 2.5 * fbm(x * 0.04 + 9, z * 0.04, 2), f = ph - Math.floor(ph);
      h += 0.8 * (f < 0.72 ? smooth(f / 0.72) : smooth((1 - f) / 0.28)) * smooth((-dz - 9) / 6) * (0.4 + vn(x * 0.04, z * 0.04)) * (1 - smooth((Math.hypot(x, z + 60) - 120) / 60)); }
    h += craters(x, z, 3.2, 0.25, 0.8, 0.45, 11) * m + craters(x, z, 13, 1.2, 4.5, 0.5, 23) * (0.3 + 0.7 * m) + craters(x, z, 70, 8, 26, 0.6, 37);
    // fine rubble and sand ripples (ripples where the ground is low and calm)
    h += 0.05 * fbm(x * 0.9, z * 0.9, 3) * (0.35 + 0.65 * m);
    h += 0.012 * Math.sin((x * 0.35 + z) * 9.5 + 3 * fbm(x * 0.3, z * 0.3, 2)) * smooth(-dz / 6) * (1 - smooth((rg - 0.45) / 0.1));
    // far away: the valley floor, mesas, and the rim of a big crater all round (highest ahead, under the Sun)
    const R = Math.hypot(x, z + 60);
    h += 55 * smooth((R - 250) / 500) * (0.45 + ridged(x / 160, z / 160, 4)) * (0.8 + 0.2 * Math.sin(Math.atan2(x, -z - 60) * 3));
    h += 7 * smooth((ridged(x / 45 + 7, z / 45, 2) - 0.58) / 0.16) * smooth((R - 60) / 60) * (1 - smooth((R - 400) / 100));
    return h;
  }
  const H0 = H(0, 0);
  const G = (x, z) => H(x, z) - H0;   // the ground, with the start of the path at y = 0
  const slopeZ = (x, z) => Math.atan((G(x, z - 0.15) - G(x, z + 0.15)) / 0.3);   // + where it rises ahead (-z)

  // ---------------- the walk ----------------
  // footprints: [time it lands, z of the ankle, side]; steps of 0.8 every 0.76 s, then shorter ones to a stop on the crest
  const STEP = 0.8, PER = 0.76;
  const PRINTS = (() => {
    const lens = [...Array(14).fill(STEP), 0.55, 0.32, 0.15], durs = [...Array(14).fill(PER), 0.72, 0.66, 0.6];
    const total = lens.reduce((a, b) => a + b, 0), z0 = RIDGE + 0.15 + total;
    const P = [[-0.3 - PER, z0 + STEP, 'R'], [-0.3, z0, 'L']];
    lens.forEach((L, i) => { const [t, z, s] = P[P.length - 1]; P.push([t + durs[i], z - L, s === 'L' ? 'R' : 'L']); });
    return P;
  })();
  const FOOT_X = 0.135, ANKLE_UP = 0.101;   // the sole's underside is 0.103 below the ankle pivot (sunk 2 mm)
  // where a foot would be at t if it stayed flat: [x, y, z, slope] of the ankle pivot (+ toe up); placeFoot rolls it
  function foot(side, t) {
    const own = PRINTS.map((p, i) => [p, i]).filter(([p]) => p[2] === side);
    let k = own.length - 1; while (k > 0 && own[k][0][0] > t) k--;
    const [cur, ci] = own[k], next = own[k + 1], x = (side === 'L' ? -1 : 1) * FOOT_X;
    const at = z => [x, G(x, z) + ANKLE_UP, z, slopeZ(x, z), -1, 0];   // + the swing's progress (-1: standing) and lift
    if (!next || t < cur[0]) return at(cur[1]);
    const prevOther = PRINTS[next[1] - 1], t0 = prevOther[0] + 0.1 * (next[0][0] - prevOther[0]), t1 = next[0][0];
    if (t < t0) return at(cur[1]);
    const u = clamp((t - t0) / (t1 - t0), 0, 1), e = u * u * (3 - 2 * u), a = at(cur[1]), b = at(next[0][1]);
    const lift = 0.085 * Math.sin(Math.PI * Math.pow(u, 0.8)) * Math.min(1, (b[2] - a[2]) / -0.5 + 0.3);
    return [x, a[1] + (b[1] - a[1]) * e + lift, a[2] + (b[2] - a[2]) * e, a[3] + (b[3] - a[3]) * e, u, lift];
  }
  // the pelvis: midway between the feet when a foot lands, gliding between those points (Catmull-Rom in time)
  const KNOTS = PRINTS.slice(1).map((p, i) => [p[0], (p[1] + PRINTS[i][1]) / 2]);
  function pelvisZ(t) {
    const K = KNOTS, n = K.length; if (t <= K[0][0]) return K[0][1] + (K[0][0] - t) * (K[1][1] - K[0][1]) / (K[1][0] - K[0][0]);
    if (t >= K[n - 1][0]) return K[n - 1][1];
    let i = 0; while (K[i + 1][0] < t) i++;
    const p0 = K[Math.max(i - 1, 0)], p1 = K[i], p2 = K[i + 1], p3 = K[Math.min(i + 2, n - 1)], u = (t - p1[0]) / (p2[0] - p1[0]);
    const m1 = (p2[1] - p0[1]) / (p2[0] - p0[0] || 1) * (p2[0] - p1[0]), m2 = (p3[1] - p1[1]) / (p3[0] - p1[0] || 1) * (p2[0] - p1[0]);
    const h00 = 2 * u ** 3 - 3 * u * u + 1, h10 = u ** 3 - 2 * u * u + u, h01 = -2 * u ** 3 + 3 * u * u, h11 = u ** 3 - u * u;
    return h00 * p1[1] + h10 * m1 + h01 * p2[1] + h11 * m2;
  }
  // 0 when a foot lands, 1 just before the next one; and how much of a stride is going on (0 once standing)
  function phase(t) {
    let i = 0; while (i < PRINTS.length - 1 && PRINTS[i + 1][0] <= t) i++;
    if (i >= PRINTS.length - 1) return [0, 0];
    return [(t - PRINTS[i][0]) / (PRINTS[i + 1][0] - PRINTS[i][0]), clamp(Math.abs(PRINTS[i + 1][1] - PRINTS[i][1]) / STEP, 0, 1)];
  }

  // two-bone IK in the side (y, z) plane: forward angle 0 = straight down, + = forward (-z)
  const L1 = Math.hypot(0.48, 0.02), L2 = Math.hypot(0.56, 0.02), O1 = Math.atan2(0.02, 0.48), O2 = Math.atan2(0.02, 0.56);
  function legIK(a, side, A, bx) {
    const J = a.joints, hp = J['hip' + side].getWorldPosition(new a.T.Vector3());
    let dy = A[1] - hp.y, dz = A[2] - hp.z, D = Math.hypot(dy, dz); const Dm = L1 + L2 - 0.0015;
    if (D > Dm) { dy *= Dm / D; dz *= Dm / D; D = Dm; }
    const phi = Math.atan2(-dz, -dy), al = Math.acos(clamp((L1 * L1 + D * D - L2 * L2) / (2 * L1 * D), -1, 1));
    const th1 = phi + al, ky = hp.y - L1 * Math.cos(th1), kz = hp.z - L1 * Math.sin(th1);
    const th2 = Math.atan2(-(hp.z + dz - kz), -(hp.y + dy - ky));
    const hx = th1 + O1 - bx, kx = th2 - O2 - (bx + hx);
    const s = side === 'L' ? -1 : 1;
    J['hip' + side].rotation.set(hx, 0, s * Math.atan2(Math.abs(A[0]) - 0.105, 1.0));
    J['knee' + side].rotation.set(kx, 0, 0);
    return bx + hx + kx;                                    // the shin's forward angle
  }
  // The suit's ankle bends high up the shin (the foot turns inside the boot), so it can't bend far. A foot stays flat
  // while it can; when the hip has moved on beyond the leg's reach it rolls (behind the hip over the toe: the heel
  // comes off; ahead of it onto the heel: the heel strike), the toe or heel pinned where it touches; and it rolls a
  // little more where the ankle would bend too far. The same in the swing, so takeoff and landing join smoothly.
  const TOE = [-ANKLE_UP, -0.16], HEEL = [-ANKLE_UP, 0.09], AX_UP = 0.35, AX_DN = -0.3, DMAX = L1 + L2 - 0.0035;   // the standing leg nearly straight (~9° at the knee: near full stretch a few mm make a big bend)
  const rot = (p, y, z) => [y * Math.cos(p) - z * Math.sin(p), y * Math.sin(p) + z * Math.cos(p)];
  function rolled(F, p) {
    const d = p - F[3]; if (Math.abs(d) < 1e-6) return F;
    const pv = d < 0 ? TOE : HEEL, w = rot(F[3], pv[0], pv[1]), r = rot(p, pv[0], pv[1]);
    return [F[0], F[1] + w[0] - r[0], F[2] + w[1] - r[1], p];
  }
  function placeFoot(a, side, F, bx) {
    const hp = a.joints['hip' + side].getWorldPosition(new a.T.Vector3());
    const over = p => { const A = rolled(F, p); return Math.hypot(A[1] - hp.y, A[2] - hp.z) - DMAX; };
    let p = F[3];
    if (over(p) > 0) {                                       // out of reach: roll just enough
      let lo = F[3], hi = F[3] + (F[2] > hp.z ? -1.2 : 0.8);
      if (over(hi) > 0) p = hi; else { for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2; if (over(mid) > 0) lo = mid; else hi = mid; } p = hi; }
    }
    for (let it = 0; it < 1; it++) {                         // and further if the ankle would bend too far
      const psi = legIK(a, side, rolled(F, p), bx), d0 = p - F[3], d1 = psi + clamp(F[3] - psi, AX_DN, AX_UP) - F[3];
      if (d0 === 0 || (Math.sign(d1) === Math.sign(d0) && Math.abs(d1) > Math.abs(d0))) p = F[3] + d1;
    }
    const psi = legIK(a, side, rolled(F, p), bx);
    a.joints['ankle' + side].rotation.set(clamp(p - psi, -0.55, 0.45), 0, -(side === 'L' ? -1 : 1) * 0.02);
  }

  // The plant, after the last step: the right arm lifts the flag high, holds a beat, thrusts it down into the ground
  // (leaning in, knees bending), holds, lets go and steps the arm back. Keys: [t, shoulder x, shoulder z, elbow, body
  // lean (- forward), crouch, left shoulder, head]; the thrust accelerates, the rest ease in and out.
  const T_LAST = PRINTS[PRINTS.length - 1][0];
  const PLANT = [
    [T_LAST - 0.15, 0.15, 0.3, 1.25, 0, 0, 0, 0],
    [T_LAST + 0.55, 1.3, 0.38, 0.95, 0.05, -0.01, 0.15, 0.12],
    [T_LAST + 0.85, 1.42, 0.38, 0.85, 0.07, 0, 0.2, 0.15],
    [T_LAST + 1.12, 0.52, 0.3, 0.22, -0.27, 0.15, 0.4, -0.05],
    [T_LAST + 1.75, 0.5, 0.3, 0.22, -0.26, 0.15, 0.4, -0.05],
    [T_LAST + 2.5, 0.08, 0.27, 0.55, 0, 0, 0, 0],
  ];
  const T_HIT = T_LAST + 1.06, T_DOWN = T_LAST + 1.12, T_REL = T_LAST + 1.7;   // the spike touches; all the way in; let go
  function plant(t) {
    const K = PLANT; let i = 0;
    if (t <= K[0][0]) i = -1; else while (i < K.length - 1 && K[i + 1][0] < t) i++;
    const pick = (k, u) => { const A = K[Math.max(k, 0)], B = K[Math.min(k + 1, K.length - 1)]; return A.map((v, j) => v + (B[j] - v) * u); };
    let r;
    if (i < 0 || i >= K.length - 1) r = K[i < 0 ? 0 : K.length - 1];
    else { const u = (t - K[i][0]) / (K[i + 1][0] - K[i][0]); r = pick(i, i === 2 ? u * u * (1.4 - 0.4 * u) : smooth(u)); }
    return { shX: r[1], shZ: r[2], el: r[3], lean: r[4], crouch: r[5], shL: r[6], head: r[7] };
  }
  // the right fist round the pole (looser than 'grip': the pole is thick); the pole's axis along the fist (the wrist's
  // local x), through the hollow of the curled fingers
  const GRIP = { f: [[0.7, 0.95, 0.55], [0.7, 0.95, 0.55], [0.72, 0.95, 0.55], [0.75, 0.95, 0.55]], spread: 0.35, th: [0.45, 0, 0.35, 0.3] };
  const GRIP_AT = [0, -0.108, -0.045];

  function walk(a, t) {
    const J = a.joints;
    a.pose(t, { glance: false });                            // breathing, fingers, the antenna
    const fl = foot('L', t), fr = foot('R', t), [ph, stride] = phase(t);
    const z = pelvisZ(t), stand = 1 - stride;
    // the pelvis rides on nearly straight legs, like a compass: lowest as a foot lands (the feet a step apart), highest
    // above the standing foot; over the ground smoothed along the path (uphill the foot behind rises on its toe)
    const hz = z - 0.035;
    let li = 0; while (li < PRINTS.length - 1 && PRINTS[li + 1][0] <= t) li++;
    const Li = li > 0 ? Math.abs(PRINTS[li][1] - PRINTS[li - 1][1]) : STEP, Ln = li < PRINTS.length - 1 ? Math.abs(PRINTS[li + 1][1] - PRINTS[li][1]) : Li;
    const dzs = ph < 0.5 ? (0.5 - ph) * Li : (ph - 0.5) * Ln;
    let gs = 0; for (let k = -2; k <= 2; k++) gs += G(0, hz + 0.2 * k) / 5;
    const pk0 = plant(t);
    const rise = Math.max(0, (G(0, hz - 0.4) - G(0, hz + 0.4)) / 0.8);   // uphill the foot ahead stands higher: reach it straight
    const y = gs + rise * dzs + ANKLE_UP + 0.13 + Math.sqrt(DMAX * DMAX - dzs * dzs) - pk0.crouch;
    const lead = (fr[2] - fl[2]) / -STEP;                    // + when the right foot is ahead
    const sway = 0.025 * Math.sin(Math.PI * clamp((t + 0.3) / PER, 0, 99)) * stride;
    a.group.position.set(sway, y, z);
    a.group.rotation.set(0, 0, 0);
    const bx = -0.09 * stride - 0.02 - 0.03 * Math.sin(2 * Math.PI * ph) * stride + pk0.lean;   // leaning into the walk (- = forward)
    J.body.rotation.set(bx, -0.07 * lead, 0.02 * lead);
    J.body.position.set(0, 0, 0);
    a.group.updateMatrixWorld(true);
    placeFoot(a, 'L', fl, bx); placeFoot(a, 'R', fr, bx);
    // the left arm swings against the legs; the right one carries the flag (and plants it, see PLANT)
    const sw = lead, pk = plant(t);
    // the left arm hangs at the side, the elbow a little bent, the palm towards the thigh (at rest the palm faces
    // forward: the wrist turns it in)
    J.shoulderL.rotation.set(0.04 + 0.3 * sw * stride + pk.shL, -0.05, -0.17);
    J.elbowL.rotation.set(0.25 + 0.2 * Math.max(0, sw) * stride + 0.3 * pk.shL, 0, 0);
    J.wristL.rotation.set(0.05, -1.4, -0.04);
    J.shoulderR.rotation.set(pk.shX - 0.06 * sw * stride, 0.05, pk.shZ);
    J.elbowR.rotation.set(pk.el, 0, 0);
    J.wristR.rotation.set(0, Math.PI / 2, 0);
    J.head.rotation.set(-0.12 - bx + pk.head, 0.05 * lead, 0);
    const w = 1 - smooth((t - T_REL + 0.12) / 0.3);         // the fist round the pole, opening as it lets go
    if (w > 0) a.hand('R', GRIP, w);
    if (t > T_REL - 0.2) a.hand('R', 'open', 0.6 * Math.sin(Math.PI * clamp((t - T_REL + 0.2) / 0.8, 0, 1)));
  }

  // ---------------- the scene ----------------
  let S = null;
  window.__sceneSetup = async (r) => {
    const T = r.THREE, scene = new T.Scene(), a = window.__makeAstronaut(T);
    a.T = T;
    await a.ready;
    scene.add(a.group);
    const sun = new T.Vector3(-0.25, 0.14, -1).normalize(), phobos = new T.Vector3(0.42, 0.3, -1).normalize();

    // the sky (linear colour): the dusk's dim brown, a blue glow round the Sun, darker overhead; the Sun's small disc
    // and Phobos lit from the side. The same function colours the haze over the ground.
    const SKY = `
      uniform vec3 sunD; uniform vec3 phoD;
      vec3 skyCol(vec3 d) {
        float e = d.y;
        vec3 c = mix(vec3(0.22, 0.165, 0.135), vec3(0.045, 0.045, 0.06), smoothstep(-0.02, 0.4, e));
        vec3 dh = normalize(vec3(d.x, d.y * 2.0, d.z));
        float a = acos(clamp(dot(dh, sunD), -1.0, 1.0));
        float toward = max(dot(normalize(vec3(d.x, 0.0, d.z)), normalize(vec3(sunD.x, 0.0, sunD.z))), 0.0);
        c += vec3(0.09, 0.15, 0.28) * exp(-a / 0.3) * 0.7 + vec3(0.2, 0.36, 0.66) * exp(-a / 0.11) * 0.95 + vec3(0.6, 0.8, 1.0) * exp(-a / 0.035) * 1.2;
        c += vec3(0.2, 0.15, 0.13) * exp(-max(e, 0.0) / 0.04) * (0.25 + 0.45 * toward);   // the dusty band along the horizon
        return pow(c, vec3(2.2)) * 1.5;
      }`;
    const sky = new T.Mesh(new T.SphereGeometry(8000, 64, 32), new T.ShaderMaterial({
      side: T.BackSide, depthWrite: false, uniforms: { sunD: { value: sun }, phoD: { value: phobos } },
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: SKY + `
        varying vec3 vD;
        void main(){
          vec3 d = normalize(vD), c = skyCol(d);
          float a = acos(clamp(dot(d, sunD), -1.0, 1.0));
          c += vec3(1.0, 0.98, 0.95) * (smoothstep(0.0062, 0.0052, a) * 30.0 + exp(-a / 0.012) * 3.0);
          // Phobos: a small lumpy disc, lit from the Sun's side
          vec3 ux = normalize(cross(vec3(0.0, 1.0, 0.0), phoD)), uy = cross(phoD, ux);
          vec2 q = vec2(dot(d, ux), dot(d, uy)) / 0.0075; q.x *= 1.25;
          float rr = dot(q, q);
          if (rr < 1.0 && dot(d, phoD) > 0.0) {
            vec3 n = normalize(ux * q.x + uy * q.y + phoD * -sqrt(1.0 - rr));
            float l = max(dot(n, sunD), 0.0);
            c = mix(c, vec3(0.5, 0.45, 0.42) * l * 1.8 + c * 0.4, smoothstep(1.0, 0.85, rr));
          }
          gl_FragColor = vec4(c, 1.0);
          #include <tonemapping_fragment>
          #include <encodings_fragment>
        }`,
    }));
    scene.add(sky);

    // the regolith's fine texture (a multiplier near 1) and its bump
    const cv = document.createElement('canvas'); cv.width = cv.height = 1024;
    { const g = cv.getContext('2d'), im = g.createImageData(1024, 1024);
      const vp = (x, y, P) => {                               // value noise that repeats every P cells (so the texture tiles)
        const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j, u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = k => ((k % P) + P) % P;
        const a = hash2(w(i), w(j)), b = hash2(w(i + 1), w(j)), c = hash2(w(i), w(j + 1)), d = hash2(w(i + 1), w(j + 1));
        return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; };
      for (let y = 0; y < 1024; y++) for (let x = 0; x < 1024; x++) {
        const n = 0.42 * vp(x / 32, y / 32, 32) + 0.3 * vp(x / 16, y / 16, 64) + 0.18 * vp(x / 8, y / 8, 128) + 0.1 * vp(x / 4, y / 4, 256);
        const v = clamp(175 + 80 * (n - 0.5) * 2, 0, 255), k = (y * 1024 + x) * 4;
        im.data[k] = im.data[k + 1] = im.data[k + 2] = v; im.data[k + 3] = 255;
      }
      g.putImageData(im, 0, 0);
      let sd = 7; const rr = () => { sd = Math.imul(sd ^ (sd >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((sd >>> 0) % 1e6) / 1e6; };
      for (let i = 0; i < 2600; i++) {                                    // grit and pebbles (wrapped at the edges)
        const x = rr() * 1024, y = rr() * 1024, r = 1.2 + 6 * rr() ** 4, sh = 70 + 90 * rr();
        for (const ox of [-1024, 0, 1024]) for (const oy of [-1024, 0, 1024]) {
          g.fillStyle = `rgba(${sh},${sh},${sh},0.85)`; g.beginPath(); g.ellipse(x + ox, y + oy, r, r * (0.7 + 0.3 * rr()), rr() * 3, 0, 6.3); g.fill();
          g.fillStyle = 'rgba(235,235,235,0.5)'; g.beginPath(); g.arc(x + ox - r * 0.25, y + oy - r * 0.25, r * 0.45, 0, 6.3); g.fill(); }
      } }
    const tex = new T.CanvasTexture(cv); tex.wrapS = tex.wrapT = T.RepeatWrapping; tex.anisotropy = 8;

    // baked sunlight on the ground: march towards the Sun; 1 = lit, 0 = in a shadow (a soft edge)
    const sunH = Math.hypot(sun.x, sun.z), tanE = sun.y / sunH, sx = sun.x / sunH, sz = sun.z / sunH;
    function lit(x, y, z, far) {
      let res = 1, t = 0.08;
      while (t < far) {
        const d = y + t * tanE - G(x + sx * t, z + sz * t);
        res = Math.min(res, 6 * d / t);
        if (res < -0.2) break;
        t *= 1.13; t += 0.02;
      }
      return smooth((res + 0.2) / 1.2);
    }
    // the ground's colour: rusty regolith, dark rock on the slabs and steep faces, paler dust in the hollows
    const lin = c => c.map(v => Math.pow(v, 2.2));
    const C_SOIL = lin([0.66, 0.39, 0.24]), C_ROCK = lin([0.33, 0.22, 0.16]), C_DUST = lin([0.76, 0.52, 0.35]);
    function colour(x, z, y, ny) {
      const rg = ridged(x * 0.11 + 3, z * 0.11, 3), rock = clamp(smooth((rg - 0.5) / 0.06) * 0.8 + smooth((0.82 - ny) / 0.15), 0, 1);
      const dust = clamp(smooth(fbm(x * 0.2 + 30, z * 0.2, 3) * 3 + 0.2) * (1 - rock), 0, 1);
      const v = 0.85 + 0.3 * (vn(x * 1.7, z * 1.7) - 0.5) + 0.2 * (vn(x * 0.21, z * 0.21) - 0.5);
      return [0, 1, 2].map(i => (C_SOIL[i] + (C_DUST[i] - C_SOIL[i]) * dust * 0.7 + (C_ROCK[i] - C_SOIL[i]) * rock) * v);
    }
    function terrainGeo(pos, idx, far) {
      const n = pos.length / 3, col = new Float32Array(n * 3), sh = new Float32Array(n), uv = new Float32Array(n * 2);
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setIndex(new T.BufferAttribute(idx, 1));
      g.computeVertexNormals();
      const N = g.attributes.normal;
      for (let i = 0; i < n; i++) {
        const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
        col.set(colour(x, z, y, N.getY(i)), i * 3);
        sh[i] = lit(x, y + 0.01, z, far);
        uv[i * 2] = x * 0.4; uv[i * 2 + 1] = z * 0.4;
      }
      g.setAttribute('color', new T.BufferAttribute(col, 3)); g.setAttribute('sunlit', new T.BufferAttribute(sh, 1)); g.setAttribute('uv', new T.BufferAttribute(uv, 2));
      return g;
    }
    // the fine mesh round the path
    const X0 = -16, X1 = 16, Z0 = -26, Z1 = 18, STEP = 0.1, NX = Math.round((X1 - X0) / STEP) + 1, NZ = Math.round((Z1 - Z0) / STEP) + 1;
    const nearGeo = (() => {
      const pos = new Float32Array(NX * NZ * 3), idx = new Uint32Array((NX - 1) * (NZ - 1) * 6);
      for (let j = 0; j < NZ; j++) for (let i = 0; i < NX; i++) { const x = X0 + i * STEP, z = Z0 + j * STEP; pos.set([x, G(x, z), z], (j * NX + i) * 3); }
      let m = 0; for (let j = 0; j < NZ - 1; j++) for (let i = 0; i < NX - 1; i++) { const q = j * NX + i; idx.set([q, q + NX, q + 1, q + 1, q + NX, q + NX + 1], m); m += 6; }
      return terrainGeo(pos, idx, 60);
    })();
    // the far mesh: rings round the middle out to the horizon; under the fine mesh it is pushed down out of sight
    const CX = 0, CZ = -4, NA = 720, NR = 200, RMIN = 12, RMAX = 4000;
    const farGeo = (() => {
      const pos = new Float32Array(NA * NR * 3), idx = new Uint32Array(NA * (NR - 1) * 6);
      for (let j = 0; j < NR; j++) for (let i = 0; i < NA; i++) {
        const rr = RMIN * Math.pow(RMAX / RMIN, j / (NR - 1)), an = 2 * Math.PI * i / NA, x = CX + rr * Math.sin(an), z = CZ - rr * Math.cos(an);
        const inside = x > X0 + 0.3 && x < X1 - 0.3 && z > Z0 + 0.3 && z < Z1 - 0.3;
        pos.set([x, G(x, z) - (inside ? 1.5 : 0), z], (j * NA + i) * 3);
      }
      let m = 0; for (let j = 0; j < NR - 1; j++) for (let i = 0; i < NA; i++) { const q = j * NA + i, q1 = j * NA + (i + 1) % NA; idx.set([q, q1, q + NA, q1, q1 + NA, q + NA], m); m += 6; }
      return terrainGeo(pos, idx, 600);
    })();

    // the haze and the baked sunlight, added to the standard material
    const fogK = { value: 0.0011 };
    function marsify(mat, baked) {
      mat.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { sunD: { value: sun }, phoD: { value: phobos }, fogK });
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP;' + (baked ? '\nattribute float sunlit; varying float vSun;' : ''))
          .replace('#include <fog_vertex>', '#include <fog_vertex>\n{ vec4 wp = vec4(transformed, 1.0);\n#ifdef USE_INSTANCING\n wp = instanceMatrix * wp;\n#endif\n vWP = (modelMatrix * wp).xyz; }' + (baked ? '\nvSun = sunlit;' : ''));
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; uniform float fogK;' + (baked ? '\nvarying float vSun;' : '') + SKY)
          .replace(/RE_Direct\( directLight, geometry, material, reflectedLight \);/g, (baked ? 'directLight.color *= vSun; ' : '') + 'RE_Direct( directLight, geometry, material, reflectedLight );')
          .replace('#include <fog_fragment>', `{
            vec3 dv = vWP - cameraPosition; float dist = length(dv);
            vec3 hd = normalize(vec3(dv.x, max(dv.y, 0.0) * 0.3 + 0.004 * length(dv.xz), dv.z));
            vec3 fc = skyCol(hd);
            #ifdef TONE_MAPPING
            fc = toneMapping(fc);
            #endif
            fc = linearToOutputTexel(vec4(fc, 1.0)).rgb;
            gl_FragColor.rgb = mix(gl_FragColor.rgb, fc, 1.0 - exp(-dist * fogK));
          }`);
      };
      mat.customProgramCacheKey = () => 'mars' + baked;   // the two variants must not share a program
      return mat;
    }
    const groundMat = marsify(new T.MeshPhysicalMaterial({ vertexColors: true, roughness: 1, metalness: 0, specularIntensity: 0.12, map: tex, bumpMap: tex, bumpScale: 0.008 }), true);   // dust: hardly any sheen
    const near = new T.Mesh(nearGeo, groundMat), far = new T.Mesh(farGeo, groundMat);
    near.receiveShadow = true; far.receiveShadow = false;
    scene.add(near, far);

    // rocks and boulders: a few shapes, hundreds of them (sizes from a power law), not on the path
    const rockMat = marsify(new T.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.9, metalness: 0, specularIntensity: 0.3, flatShading: true, map: tex }), false);
    const shapes = [0, 1, 2].map(k => {
      const g = new T.IcosahedronGeometry(1, 2), p = g.attributes.position;
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i), d = 1 + 0.35 * (vn(x * 1.6 + 10 * k, z * 1.6 + 3 * y + 5) - 0.5) + 0.15 * (vn(x * 4 + y * 3, z * 4 - 7 * k) - 0.5);
        p.setXYZ(i, x * d, Math.max(y * d * (0.6 + 0.12 * k), -0.4), z * d * (1 + 0.15 * k));
      }
      g.computeVertexNormals(); return g;
    });
    const rng = (() => { let s = 12345; return () => { s = Math.imul(s ^ (s >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((s >>> 0) % 1e6) / 1e6; }; })();
    const NROCK = 750, perShape = Math.ceil(NROCK / 3);
    const rockMeshes = shapes.map(g => { const m = new T.InstancedMesh(g, rockMat, perShape); m.castShadow = m.receiveShadow = true; m.count = 0; scene.add(m); return m; });
    const M4 = new T.Matrix4(), Q = new T.Quaternion(), E = new T.Euler(), V = new T.Vector3(), SC = new T.Vector3(), Cc = new T.Color();
    for (let k = 0; k < NROCK * 3 && rockMeshes.some(m => m.count < perShape); k++) {
      const x = -15 + 30 * rng(), z = -25 + 42 * rng(), u = rng();
      let s = Math.min(1.3, 0.05 / Math.pow(1 - 0.985 * u, 0.5));
      if (Math.abs(x) < 0.9 + s && z > -6 && z < 17) continue;       // keep the path clear
      if (pathMask(x, z) < 0.5 && s > 0.12) s *= 0.4;
      const m = rockMeshes[k % 3]; if (m.count >= perShape) continue;
      E.set(rng() * 0.5, rng() * 6.28, rng() * 0.5); Q.setFromEuler(E);
      SC.set(s * (0.8 + 0.4 * rng()), s, s * (0.8 + 0.4 * rng()));
      V.set(x, G(x, z) + s * 0.1, z); M4.compose(V, Q, SC); m.setMatrixAt(m.count, M4);
      const l = lit(x, G(x, z) + s * 0.5, z, 60), v = 0.75 + 0.4 * rng();
      Cc.setRGB(0.5 * v, 0.33 * v, 0.23 * v).convertSRGBToLinear().multiplyScalar(0.7 + 0.3 * l); m.setColorAt(m.count, Cc);
      m.count++;
    }
    rockMeshes.forEach(m => { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; });

    // the light: the low Sun (its shadow map covers the walk and the rocks round it: the Sun is so low that this
    // box reaches far along the ground), a dim brown sky and ground, a cool rim on the figure
    const key = new T.DirectionalLight(0xfff1e2, 2.6);
    key.position.copy(sun).multiplyScalar(80).add(new T.Vector3(0, 0, -5)); key.target.position.set(0, 0, -5);
    key.castShadow = true; key.shadow.mapSize.set(4096, 4096); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02; key.shadow.radius = 3;
    Object.assign(key.shadow.camera, { left: -16, right: 16, top: 7, bottom: -7, near: 15, far: 170 });
    scene.add(key, key.target);
    scene.add(new T.HemisphereLight(0x6a7088, 0x4a2c1e, 0.38));
    a.rim.color.value.setRGB(0.45, 0.65, 1.0);
    scene.environment = window.__astronautEnv(T, r.renderer, { warm: sun });

    const cam = new T.PerspectiveCamera(36, 720 / 1280, 0.03, 12000);

    // ---- the flag: an aluminium pole with a spike, a cross bar at the top that holds the cloth spread (as on the
    // Moon), the cloth deep blue with the emblem and НЕБОЗВІД. Local frame: +y up the pole (its foot at 0), cloth to +x.
    try { const ff = new FontFace('Unbounded', 'url(/fonts/Unbounded.ttf)'); await ff.load(); document.fonts.add(ff); } catch (e) { console.log('[scene] no font', e.message); }
    const emblem = await new Promise(ok => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = window.__astronautEmblem || ''; });
    const fcv = document.createElement('canvas'); fcv.width = 1024; fcv.height = 690;
    { const g = fcv.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 690);
      gr.addColorStop(0, '#1a2d5e'); gr.addColorStop(1, '#0c1736'); g.fillStyle = gr; g.fillRect(0, 0, 1024, 690);
      g.strokeStyle = '#c9a54a'; g.lineWidth = 10; g.strokeRect(22, 22, 980, 646);              // a thin gold border
      if (emblem) g.drawImage(emblem, 512 - 200, 52, 400, 400);
      g.fillStyle = '#f3f5f9'; g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.font = '700 96px Unbounded, sans-serif';
      try { g.letterSpacing = '8px'; } catch (e) {}
      g.fillText('НЕБОЗВІД', 512, 600); }
    const ftex = new T.CanvasTexture(fcv); ftex.encoding = T.sRGBEncoding; ftex.anisotropy = 8;
    const POLE = 2.0, CW = 0.66, CH = 0.445;
    const flag = new T.Group(); scene.add(flag);
    const alu = new T.MeshStandardMaterial({ color: 0xd4d8de, metalness: 0.85, roughness: 0.32 });
    const add = (g, m, x, y, z) => { const o = new T.Mesh(g, m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; flag.add(o); return o; };
    add(new T.CylinderGeometry(0.015, 0.015, POLE, 20), alu, 0, POLE / 2, 0);
    add(new T.ConeGeometry(0.015, 0.1, 20).rotateX(Math.PI), alu, 0, -0.05, 0);                  // the spike
    add(new T.SphereGeometry(0.026, 20, 14), new T.MeshStandardMaterial({ color: 0xd8b25a, metalness: 1, roughness: 0.25 }), 0, POLE + 0.012, 0);
    add(new T.CylinderGeometry(0.009, 0.009, CW + 0.03, 12).rotateZ(Math.PI / 2), alu, (CW + 0.03) / 2, POLE - 0.035, 0);   // the cross bar
    const clothGeo = new T.PlaneGeometry(CW, CH, 33, 22).translate(CW / 2 + 0.015, POLE - 0.04 - CH / 2, 0);
    const clothRest = clothGeo.attributes.position.array.slice();
    // printed on both faces (the back one mirrored back, so the name reads right from either side); a little of the
    // dusk shines through
    const ftexB = ftex.clone(); ftexB.wrapS = T.RepeatWrapping; ftexB.repeat.x = -1; ftexB.offset.x = 1; ftexB.needsUpdate = true;
    for (const [side, tx] of [[T.FrontSide, ftex], [T.BackSide, ftexB]])
      add(clothGeo, new T.MeshStandardMaterial({ map: tx, side, roughness: 0.8, metalness: 0, emissive: 0xffffff, emissiveMap: tx, emissiveIntensity: 0.18 }), 0, 0, 0);
    // the cloth stirs in the thin wind, more while it is carried (amp: 0 at the pole, 1 at the free edge)
    function stir(t, carried) {
      const P = clothGeo.attributes.position;
      for (let i = 0; i < P.count; i++) {
        const x = clothRest[i * 3] - 0.015, y = clothRest[i * 3 + 1], u = Math.max(0, x) / CW, amp = Math.pow(u, 1.15);
        const z = amp * ((0.026 + 0.03 * carried) * Math.sin(9 * x - 3.2 * t + 2.2 * y) + 0.012 * Math.sin(19 * x - 5.3 * t + 6 * y) + 0.04 * carried * Math.sin(2 * Math.PI * t / (2 * PER)));
        P.setXYZ(i, clothRest[i * 3] - 0.03 * amp * amp * (0.4 + carried), y - 0.012 * amp * amp, z);
      }
      P.needsUpdate = true; clothGeo.computeVertexNormals();
    }
    // the flag in the hand: the wrist is turned so the pole stands along D (world), the cloth turned towards side
    const QI = new T.Quaternion(), V1 = new T.Vector3(1, 0, 0);
    function holdFlag(t) {
      const W = a.joints.wristR; a.group.updateMatrixWorld(true);
      const carry = 1 - smooth((t - T_LAST + 0.3) / 0.8);
      const D = new T.Vector3(0.05 * Math.sin(Math.PI * t / PER) * carry, 1, -0.12 * carry - 0.04).normalize();
      const q = W.getWorldQuaternion(new T.Quaternion()), R = new T.Quaternion().setFromUnitVectors(V1.clone().applyQuaternion(q), D);
      W.quaternion.copy(W.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(R).multiply(q));
      a.group.updateMatrixWorld(true);
      const grip = W.localToWorld(new T.Vector3(...GRIP_AT));
      const slide = S0 + (S1 - S0) * smooth((t - T_LAST - 0.05) / 0.5);
      const side = new T.Vector3(0.15 + 0.85 * (1 - carry), 0, 1 - 0.4 * (1 - carry)), X = side.addScaledVector(D, -side.dot(D)).normalize();
      const M = new T.Matrix4().makeBasis(X, D, new T.Vector3().crossVectors(X, D)).setPosition(grip.addScaledVector(D, -slide));
      return M;
    }
    const S0 = 0.5, DEPTH = 0.2;
    let S1 = S0;
    walk(a, T_DOWN); { const M = holdFlag(T_DOWN), foot = new T.Vector3().setFromMatrixPosition(M), Dy = M.elements[5];
      S1 = clamp(S0 + (foot.y - (G(foot.x, foot.z) - DEPTH)) / Dy, 0.4, 1.3); }
    walk(a, T_REL); const PLANTED = holdFlag(T_REL);
    const FOOT = new T.Vector3().setFromMatrixPosition(PLANTED);
    function placeFlag(t) {
      flag.matrixAutoUpdate = false;
      flag.matrix.copy(t < T_REL ? holdFlag(t) : PLANTED); flag.matrixWorldNeedsUpdate = true;
      stir(t, 1 - smooth((t - T_LAST + 0.3) / 0.8));
    }

    // ---- footprints: the sole's print pressed into the dust (darker, the lugs' grooves, a rim of pushed-up soil),
    // laid over the ground where each foot lands, from the moment it lands
    const pcv = document.createElement('canvas'); pcv.width = 128; pcv.height = 320;
    const acv = document.createElement('canvas'); acv.width = 128; acv.height = 320;
    { const sole = (g, grow) => { g.beginPath(); g.ellipse(64, 95, 50 + grow, 78 + grow, 0, 0, 7); g.fill(); g.beginPath(); g.ellipse(64, 240, 42 + grow, 62 + grow, 0, 0, 7); g.fill(); g.fillRect(24 - grow, 95, 80 + 2 * grow, 145); };
      const g = pcv.getContext('2d'); g.fillStyle = 'rgb(235,235,235)'; sole(g, 7);                    // the rim
      g.fillStyle = 'rgb(120,120,120)'; sole(g, 0);                                                     // the floor, pressed down
      g.fillStyle = 'rgb(70,70,70)'; for (let y = 30; y < 300; y += 22) g.fillRect(20, y, 88, 9);       // the lugs' grooves
      g.filter = 'blur(1.5px)'; g.drawImage(pcv, 0, 0); g.filter = 'none';
      const h = acv.getContext('2d'); h.filter = 'blur(4px)'; h.fillStyle = '#fff'; sole(h, 9); }
    const pTex = new T.CanvasTexture(pcv), aTex = new T.CanvasTexture(acv);
    const pMat = marsify(new T.MeshPhysicalMaterial({ color: 0xffffff, map: pTex, alphaMap: aTex, bumpMap: pTex, bumpScale: 0.012, transparent: true, depthWrite: false,
      roughness: 1, specularIntensity: 0.12, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }), false);
    const prints = PRINTS.map(([tl, z, side]) => {
      const x = (side === 'L' ? -1 : 1) * FOOT_X, g = new T.PlaneGeometry(0.15, 0.37, 6, 12).rotateX(-Math.PI / 2), P = g.attributes.position, col = [];
      for (let i = 0; i < P.count; i++) { const px = x + P.getX(i), pz = z - 0.085 + P.getZ(i); P.setXYZ(i, px, G(px, pz) + 0.004, pz); col.push(...colour(px, pz, 0, 1).map(v => v * 0.85)); }
      g.setAttribute('color', new T.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
      const m = new T.Mesh(g, pMat); m.material = pMat.clone(); m.material.vertexColors = true; m.material.onBeforeCompile = pMat.onBeforeCompile; m.receiveShadow = true; m.userData.t = tl; scene.add(m); return m;
    });

    // ---- dust: kicked up where a foot lands and where it pushes off, a puff where the spike goes in, and fine motes
    // drifting in the air. Every grain moves by a formula of time (drag, slow settling, never below where it started),
    // so the frames don't depend on each other; lit by the Sun, bright where it scatters towards the camera.
    const DP = [], DV = [], DT = [], DL = [], DS = [], DK = [];
    const drng = (() => { let s = 777; return () => { s = Math.imul(s ^ (s >>> 15), 2246822519) + 0x9e3779b9 | 0; return ((s >>> 0) % 1e6) / 1e6; }; })();
    const grain = (p, v, t0, life, size, k) => { DP.push(p[0], p[1], p[2]); DV.push(v[0], v[1], v[2]); DT.push(t0); DL.push(life); DS.push(size); DK.push(k); };
    PRINTS.forEach(([tl, z, side], i) => {
      if (i < 1) return;
      const x = (side === 'L' ? -1 : 1) * FOOT_X, n = i >= PRINTS.length - 2 ? 20 : 46;
      for (let k = 0; k < n; k++) {                            // the landing: out from under the sole, low and wide
        const a0 = drng() * 6.283, r = Math.sqrt(drng()), px = x + 0.09 * r * Math.cos(a0), pz = z - 0.08 + 0.17 * r * Math.sin(a0), sp = 0.25 + 0.75 * drng();
        grain([px, G(px, pz) + 0.01, pz], [Math.cos(a0) * sp, 0.12 + 0.45 * drng(), Math.sin(a0) * sp - 0.25], tl + 0.06 * drng(), 1.2 + 1.8 * drng(), 0.02 + 0.04 * drng(), 2.6);
      }
      const nx = PRINTS.find((q, j) => j > i && q[2] === side);
      if (nx) { const t0 = PRINTS[PRINTS.indexOf(nx) - 1][0] + 0.1 * (nx[0] - PRINTS[PRINTS.indexOf(nx) - 1][0]);
        for (let k = 0; k < 26; k++) {                         // the push-off: thrown back and up from the toe
          const px = x + 0.08 * (drng() - 0.5), pz = z - 0.24 + 0.06 * drng();
          grain([px, G(px, pz) + 0.01, pz], [0.3 * (drng() - 0.5), 0.35 + 0.7 * drng(), 0.4 + 0.8 * drng()], t0 + 0.12 * drng(), 1.0 + 1.6 * drng(), 0.015 + 0.03 * drng(), 2.2); } }
    });
    for (let k = 0; k < 400; k++) {                            // the spike goes in
      const a0 = drng() * 6.283, sp = 0.3 + 1.1 * drng();
      grain([FOOT.x + 0.04 * Math.cos(a0), G(FOOT.x, FOOT.z) + 0.01, FOOT.z + 0.04 * Math.sin(a0)], [Math.cos(a0) * sp, 0.2 + 0.9 * drng(), Math.sin(a0) * sp], T_HIT + 0.08 * drng(), 1.8 + 2.2 * drng(), 0.012 + 0.025 * drng(), 2.0);
    }
    for (let k = 0; k < 700; k++) {                            // motes in the air along the walk
      const px = -5 + 10 * drng(), pz = -10 + 24 * drng();
      grain([px, G(px, pz) + 0.1 + 2.6 * drng(), pz], [0.06 + 0.04 * drng(), 0.01 * (drng() - 0.5), 0.02 * (drng() - 0.5)], -5, 99, 0.004 + 0.008 * drng(), 0.02);
    }
    const dg = new T.BufferGeometry();
    dg.setAttribute('position', new T.Float32BufferAttribute(DP, 3)); dg.setAttribute('v0', new T.Float32BufferAttribute(DV, 3));
    dg.setAttribute('t0', new T.Float32BufferAttribute(DT, 1)); dg.setAttribute('life', new T.Float32BufferAttribute(DL, 1));
    dg.setAttribute('sz', new T.Float32BufferAttribute(DS, 1)); dg.setAttribute('kd', new T.Float32BufferAttribute(DK, 1));
    const dustU = { uT: { value: 0 }, sunD: { value: sun }, uScale: { value: 1280 / (2 * Math.tan(18 * Math.PI / 180)) } };
    const dust = new T.Points(dg, new T.ShaderMaterial({
      uniforms: dustU, transparent: true, depthWrite: false,
      vertexShader: `uniform float uT; uniform vec3 sunD; uniform float uScale;
        attribute vec3 v0; attribute float t0; attribute float life; attribute float sz; attribute float kd;
        varying float vA; varying float vPh;
        void main() {
          float tau = uT - t0;
          if (tau < 0.0 || tau > life) { gl_Position = vec4(0.0, 0.0, -2.0, 1.0); gl_PointSize = 0.0; vA = 0.0; return; }
          vec3 p = position + v0 * (1.0 - exp(-kd * tau)) / kd;
          p.y -= 0.05 * tau * tau / (1.0 + tau);                  // settling, slowly
          p.y = max(p.y, position.y - 0.005);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          float g = tau / life;
          gl_PointSize = max(1.0, sz * (1.0 + 2.5 * g) * uScale / -mv.z);
          vA = pow(1.0 - g, 1.6) * smoothstep(0.0, 0.04, tau) * (kd < 0.1 ? 0.55 : 0.5 / (1.0 + 1.2 * g));
          vPh = pow(max(dot(normalize(p - cameraPosition), sunD), 0.0), 6.0);
        }`,
      fragmentShader: `varying float vA; varying float vPh;
        void main() {
          vec2 q = gl_PointCoord * 2.0 - 1.0; float r = dot(q, q); if (r > 1.0) discard;
          vec3 c = vec3(0.55, 0.36, 0.24) * (0.45 + 2.4 * vPh) + vec3(0.2, 0.3, 0.5) * 0.4 * vPh;
          gl_FragColor = vec4(c, vA * exp(-r * 3.0));
          #include <tonemapping_fragment>
          #include <encodings_fragment>
        }`,
    }));
    dust.frustumCulled = false; scene.add(dust);
    S = { T, scene, a, cam, sky, key, placeFlag, prints, dustU };
  };

  // ---------------- the camera ----------------
  // keys [t, camera offset from the pelvis (x, y, z; y kept above the ground), look-at offset]; Catmull-Rom between them.
  // low by the boots (a step into the dust), alongside, ahead-left looking back, round behind on the crest for the
  // flag, then up and back over the valley into the blue dusk.
  const CAM = [
    [0.0, [0.9, -1.12, 2.9], [0.0, -0.8, -1.0]],
    [2.6, [1.5, -0.75, 3.4], [0.0, -0.4, -0.8]],
    [4.8, [5.8, 0.35, 1.2], [0, 0.15, -0.2]],
    [7.4, [4.8, 0.6, -3.4], [0, 0.2, 0]],
    [10.0, [-3.6, 0.7, -5.2], [0, 0.25, 0.3]],
    [12.0, [-1.4, 0.8, 5.6], [0, 0.25, -2.0]],
    [13.4, [1.7, -0.3, 4.6], [-0.15, 0.35, -1.0]],
    [14.8, [1.9, -0.3, 4.0], [-0.1, 0.1, -0.8]],
    [16.6, [3.4, 0.45, 3.0], [0.25, 0.1, -0.3]],
    [18.3, [1.7, 1.2, 4.9], [0.15, -0.35, -1.8]],
    [20.0, [0.7, 2.0, 6.4], [0.2, -0.5, -7.0]],
    [23.0, [0.4, 3.0, 8.8], [0.2, -0.6, -9.0]],
  ];
  function shoot(t, a, cam) {
    const p = a.group.position, T = S.T, K = CAM, n = K.length;
    let i = 0; while (i < n - 2 && t > K[i + 1][0]) i++;
    const u = clamp((t - K[i][0]) / (K[i + 1][0] - K[i][0]), 0, 1);
    const k0 = K[Math.max(i - 1, 0)], k1 = K[i], k2 = K[i + 1], k3 = K[Math.min(i + 2, n - 1)];
    const cr = (a0, b, c, d) => 0.5 * (2 * b + (c - a0) * u + (2 * a0 - 5 * b + 4 * c - d) * u * u + (3 * b - a0 - 3 * c + d) * u * u * u);
    const f = q => [0, 1, 2].map(j => cr(k0[q][j], k1[q][j], k2[q][j], k3[q][j]));
    const o = f(1), l = f(2);
    const cx = o[0], cz = p.z + o[2], gy = G(cx, cz);
    cam.position.set(cx, Math.max(gy + 0.12, p.y + o[1]), cz);
    cam.lookAt(new T.Vector3(l[0], p.y + l[1], p.z + l[2]));
  }

  window.__recCam = () => {};
  window.__recRender = () => {
    const r = window.__rec, ren = r.renderer;
    if (!S) { ren.render(r.scene, r.camera); return; }
    const { T, scene, a, cam, sky } = S, t = window.__vt() - (window.__t0 || 0);
    walk(a, t);
    S.placeFlag(t);
    // the end: it turns its head to the camera and gives a thumbs-up with the free hand
    a.gestureAt(t, 'thumbsUp', { start: T_LAST + 2.9, end: T_LAST + 5.2, side: 'R' });
    shoot(t, a, cam);
    if (t > T_LAST + 2.6) a.lookAt(cam.position, smooth((t - T_LAST - 2.6) / 0.8) * (1 - smooth((t - T_LAST - 5.3) / 0.8)));
    a.group.updateMatrixWorld(true);
    S.prints.forEach(m => { m.visible = t >= m.userData.t; });
    S.dustU.uT.value = t;
    sky.position.copy(cam.position);
    const tm = ren.toneMapping, te = ren.toneMappingExposure, sm = ren.shadowMap.enabled, st = ren.shadowMap.type;
    ren.toneMapping = T.ACESFilmicToneMapping; ren.toneMappingExposure = 1.1; ren.shadowMap.enabled = true; ren.shadowMap.type = T.PCFSoftShadowMap;
    ren.setRenderTarget(null); ren.render(scene, cam);
    ren.toneMapping = tm; ren.toneMappingExposure = te; ren.shadowMap.enabled = sm; ren.shadowMap.type = st;
  };
})();
