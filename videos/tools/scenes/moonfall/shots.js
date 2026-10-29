// The film of «Що, якби Місяць упав на Землю?» as one shot (world.js builds the world; render.js renders it): every
// frame is a pure function of the video second, through the clock of timeline.py (the same keys, here in JS).
// Units: 1 = 1000 km, physical time in seconds (negative before the Moon touches the Earth).
(() => {
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const smooth = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const lerp = (a, b, k) => a + (b - a) * k;
  const D = Math.PI / 180;

  // ---- physics (facts.py): a two-body radial fall from rest at the mean distance --------------------------------------
  const G = 6.674e-11, ME = 5.972e24, MM = 7.342e22, RE_M = 6.371e6, RM_M = 1.7374e6, R0 = 3.844e8;
  const MU = G * (ME + MM), K = Math.sqrt(R0 ** 3 / (8 * MU));
  const tAt = r => { const e = Math.acos(2 * r / R0 - 1); return K * (e + Math.sin(e)); };
  const T_HIT = tAt(RE_M + RM_M);                                   // 4.82 days
  function rAt(t) {                                                  // metres from the Earth's centre, t seconds after the stop
    let lo = 0, hi = Math.PI;
    for (let i = 0; i < 60; i++) { const m = (lo + hi) / 2; if (K * (m + Math.sin(m)) < t) lo = m; else hi = m; }
    return R0 / 2 * (1 + Math.cos(lo));
  }
  const vAt = r => Math.sqrt(2 * MU * (1 / r - 1 / R0));
  const GMU = 3.986e-4;                                              // the Earth's GM in units³/s²
  const VHIT = vAt(RE_M + RM_M) / 1e6;                               // units/s at the touch

  // ---- the clock: video second -> physical second (negative = before the touch) ------------------------------------
  const KEYS = [[0.0, 180, 'lin'], [1.7, 180, 'log'], [3.0, T_HIT - 600, 'lin'], [9.5, 12 * 3600, 'log'], [15.5, 1.5 * 3600, 'log'],
    [23.0, 22.5 * 60, 'log'], [31.0, 180, 'log'], [33.5, 0.5, 'end']];
  const AFTER = [[33.5, 0], [36.5, 90], [39.5, 900], [43.5, 5400], [46.0, 14400]];   // slow at first: the Moon going in
  function tPhys(tau) {
    if (tau >= 33.5) {
      for (let i = 0; i < AFTER.length - 1; i++) { const [a, ta] = AFTER[i], [b, tb] = AFTER[i + 1]; if (tau <= b) return lerp(ta, tb, (tau - a) / (b - a)); }
      return AFTER[AFTER.length - 1][1];
    }
    for (let i = 0; i < KEYS.length - 1; i++) {
      const [a, ta, mode] = KEYS[i], [b, tb] = KEYS[i + 1];
      if (tau <= b) { const u = b > a ? (tau - a) / (b - a) : 1; return -(mode === 'lin' ? lerp(ta, tb, u) : Math.exp(lerp(Math.log(ta), Math.log(tb), u))); }
    }
    return 0;
  }
  // the Moon's centre from the Earth's centre (units); after the touch it ploughs on, slowing, until it is gone
  function moonZ(tp) {
    if (tp <= 0) return Math.max(rAt(T_HIT + tp), RE_M + RM_M) / 1e6;
    const stop = 700; const s = Math.min(tp, stop);
    return (RE_M + RM_M) / 1e6 - VHIT * (s - s * s / (2 * stop));
  }

  // ---- the geometry (inertial): where the Moon falls, where we are, the Sun --------------------------------------------
  const dirLL = (lat, lon) => V(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
  const MHAT = dirLL(22, 50);            // under the Moon at the touch: the Arabian Peninsula
  const AHAT = dirLL(54, 8);             // under us at the touch: northern Germany (45° of arc away; the horizon is 24° off)
  const SUN = dirLL(-13.5, -29.5);       // late October; 14:30 under us, sunset where it strikes
  const ALT = 0.6, OMEGA = 2 * Math.PI / 86164;
  const ER = 6.371, RM = 1.7374;
  const A = AHAT.clone().multiplyScalar(ER + ALT);
  // our local frame: up, and the azimuth toward the Moon (the Moon falls in the vertical plane through us, so it keeps
  // its bearing and only sinks)
  const UP = AHAT.clone(), TOWARD = MHAT.clone().sub(UP.clone().multiplyScalar(MHAT.dot(UP))).normalize(), SIDE = TOWARD.clone().cross(UP).normalize();
  const dirFrom = (pitchDeg, yawDeg = 0) => TOWARD.clone().applyAxisAngle(UP, yawDeg * D).multiplyScalar(Math.cos(pitchDeg * D)).addScaledVector(UP, Math.sin(pitchDeg * D)).normalize();
  const moonPos = tp => MHAT.clone().multiplyScalar(moonZ(tp));
  const elevOf = p => Math.asin(clamp(p.clone().sub(A).normalize().dot(UP), -1, 1)) / D;

  // the tides: the equilibrium height under the Moon (metres), stopped at ~3.2 km (beyond it the formula no longer holds;
  // the sea is already one heap) — facts.py: 0.36 m today, x(d0/d)^3
  const zetaAt = z => Math.min(0.357 * Math.pow(384.4 / z, 3), 3200);
  // how stretched and cracked the Moon is: from ~30 000 km in, more as it nears (the real tearing starts ~9 500 km)
  const stretchAt = z => 0.06 * smooth((30 - z) / 12) + 0.18 * smooth((18.5 - z) / 9);
  // how far the crust has broken up (0..1), by time before the touch: from ~9 minutes out, nearly all of the near half at the end
  const crumbleAt = tp => 0.8 * smooth((tp + 260) / 250);
  const crackAt = z => smooth((30 - z) / 12) * 0.6 + smooth((18.5 - z) / 8) * 0.4;

  // ---- the rubble: shed from the near side from ~14 minutes before the touch, each on its own fall ------------------
  let RUB = null;
  function buildRubble(X) {
    // (no separate specks before the touch any more — the author: they looked like noise; the crust breaking up and the
    // dust clouds are drawn on the Moon itself and as soft billows, buildPuffs)
    const rnd = X.rnd, n = 0, nr = 0, nc = 0;
    // the Moon's own frame (as in setup): +x toward the Earth; its surface stretched as in the vertex shader of world.js
    const xa = MHAT.clone().negate(), ya = V(0, 1, 0).sub(xa.clone().multiplyScalar(xa.y)).normalize(), za = xa.clone().cross(ya);
    const surface = (d, e) => { const lx = d.dot(xa), ly = d.dot(ya), lz = d.dot(za), k = 1 / Math.sqrt(1 + e);
      return xa.clone().multiplyScalar(lx * (1 + e) + e * 0.25 * Math.pow(Math.max(lx, 0), 4)).addScaledVector(ya, ly * k).addScaledVector(za, lz * k).multiplyScalar(RM); };
    const out = { dust: [], rocks: [] };
    const toE = MHAT.clone().negate();
    // each piece is born on the surface (a rock half sunk in it, so it climbs out of the ground rather than appearing)
    const make = (count, tFrom, tTo, dvMin, dvMax, list, pow, sizeOf) => {
      for (let i = 0; i < count; i++) {
        const u = Math.pow(rnd(), pow), tb = lerp(tFrom, tTo, u);                // birth (physical s): more of it later
        const z = moonZ(tb), e = stretchAt(z);
        // a point on the near cap (within ~40° of the point facing the Earth)
        let d; do { d = V(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1); } while (d.lengthSq() > 1 || d.lengthSq() < 0.01);
        d.normalize(); if (d.dot(toE) < 0) d.negate();
        d.lerp(toE, 0.55 * rnd()).normalize();
        if (d.dot(toE) < Math.cos(42 * D)) { i--; continue; }
        const size = sizeOf ? sizeOf() : 0;
        const p = MHAT.clone().multiplyScalar(z).add(surface(d, e)).addScaledVector(d, -0.5 * size);
        const vm = -vAt(z * 1e6) / 1e6;                                         // the Moon's own speed (toward the Earth)
        const dv = lerp(dvMin, dvMax, rnd());
        const v = MHAT.clone().multiplyScalar(vm).addScaledVector(d, dv).add(V(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).multiplyScalar(dv * 0.6));
        // integrate (velocity Verlet, 2 s) until it hits the ground or the film ends; keep every 4 s
        const samples = [p.x, p.y, p.z]; let t = tb, hit = null;
        const acc = q => q.clone().multiplyScalar(-GMU / Math.pow(q.length(), 3));
        let a0 = acc(p);
        while (t < 900) {
          const dt = 2;
          p.addScaledVector(v, dt).addScaledVector(a0, 0.5 * dt * dt);
          const a1 = acc(p); v.addScaledVector(a0.add(a1), 0.5 * dt); a0 = a1; t += dt;
          if (Math.round((t - tb) / dt) % 2 === 0) samples.push(p.x, p.y, p.z);
          if (p.length() < ER + 0.002) { hit = { t, dir: p.clone().normalize(), v: v.clone() }; break; }
        }
        list.push({ tb, s: new Float32Array(samples), hit, size });
      }
    };
    make(n, -14 * 60, -5, 0.00008, 0.0006, out.dust, 0.45);
    make(nr, -8 * 60, -5, 0.0001, 0.0009, out.rocks, 0.6, () => 0.004 + 0.026 * Math.pow(rnd(), 2.5));
    // a few big blocks peeling off the side that faces the Earth in the last minutes: 30-70 km, slow to part
    const big = []; make(nc, -150, -15, 0.00006, 0.0002, big, 0.8, () => 0.03 + 0.04 * Math.pow(rnd(), 1.5));
    out.rocks.push(...big);
    out.rocks.forEach(r => { r.ax = V(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize(); r.w = (rnd() - 0.5) * (r.size > 0.03 ? 0.003 : 0.012);
      r.asp = V(0.65 + 0.6 * rnd(), 0.65 + 0.6 * rnd(), 0.65 + 0.6 * rnd()); });
    out.hits = out.rocks.filter(r => r.hit).map(r => ({ t: r.hit.t, dir: r.hit.dir, size: r.size })).sort((a, b) => a.t - b.t);
    // meteors: the small stuff that reaches the air (straight for its last ~120 km)
    const met = X.streaks(4000); let k = 0;
    for (const d of out.dust) {
      if (!d.hit || k >= met.n) continue;
      const v = d.hit.v, sp = v.length(), dt = 0.12 / sp;
      met.set(k++, d.hit.dir.clone().multiplyScalar(ER + 0.002).addScaledVector(v, -dt), v, d.hit.t - dt, dt * 1.3, 0.05 + 0.08 * rnd(), 0.6 + 0.8 * rnd());
    }
    met.mesh.geometry.instanceCount = k; met.done(); out.met = met;
    return out;
  }
  // ---- dust billows off the crumbling end: born on the surface (stretched as the Moon is), drifting out and down toward
  // the Earth on their own falls (the Earth's gravity, integrated), growing and thinning as they go
  function buildPuffs(X) {
    const rnd = X.rnd, N = X.puffs.geometry.attributes.position.count, out = [];
    const xa = MHAT.clone().negate(), ya = V(0, 1, 0).sub(xa.clone().multiplyScalar(xa.y)).normalize(), za = xa.clone().cross(ya);
    const surface = (d, e) => { const lx = d.dot(xa), ly = d.dot(ya), lz = d.dot(za), k = 1 / Math.sqrt(1 + e);
      return xa.clone().multiplyScalar(lx * (1 + e) + e * 0.25 * Math.pow(Math.max(lx, 0), 4)).addScaledVector(ya, ly * k).addScaledVector(za, lz * k).multiplyScalar(RM); };
    const acc = q => q.clone().multiplyScalar(-GMU / Math.pow(q.length(), 3));
    for (let i = 0; i < N; i++) {
      const tb = lerp(-300, -3, Math.pow(rnd(), 0.6));
      const z = moonZ(tb), e = stretchAt(z), cr = crumbleAt(tb);
      // where on the near end: within the crumbling zone at that moment (it spreads up from the tip)
      let d; do { d = V(rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1); } while (d.lengthSq() > 1 || d.lengthSq() < 0.01);
      d.normalize(); if (d.dot(xa) < 0) d.negate();
      const reach = 0.95 - 0.8 * cr; if (d.dot(xa) < reach) d.lerp(xa, 0.5 + 0.5 * rnd()).normalize();
      const p = MHAT.clone().multiplyScalar(z).add(surface(d, e));
      const v = MHAT.clone().multiplyScalar(-vAt(z * 1e6) / 1e6).addScaledVector(d, 0.0003 + 0.0011 * rnd()).add(V(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).multiplyScalar(0.0004));
      const samples = [p.x, p.y, p.z]; let t = tb, a0 = acc(p), gone = null;
      while (t < 40) {
        const dt = 2; p.addScaledVector(v, dt).addScaledVector(a0, 0.5 * dt * dt);
        const a1 = acc(p); v.addScaledVector(a0.add(a1), 0.5 * dt); a0 = a1; t += dt;
        if (Math.round((t - tb) / dt) % 2 === 0) samples.push(p.x, p.y, p.z);
        if (p.length() < ER + 0.03) { gone = t; break; }
      }
      out.push({ tb, s: new Float32Array(samples), hit: gone !== null ? { t: gone } : null, life: 160 + 280 * rnd(), s0: 0.02 + 0.03 * rnd(), s1: 0.12 + 0.3 * Math.pow(rnd(), 1.5), a: 0.1 + 0.2 * rnd() });
    }
    return out;
  }
  let PUFFS = null;

  const posAt = (r, tp) => {                                                    // a rubble piece's place (null: not yet / gone)
    if (tp < r.tb || (r.hit && tp >= r.hit.t)) return null;
    const f = (tp - r.tb) / 4, i = Math.floor(f), s = r.s, m = s.length / 3 - 1;
    if (i >= m) return V(s[m * 3], s[m * 3 + 1], s[m * 3 + 2]);
    const k = f - i;
    return V(lerp(s[i * 3], s[i * 3 + 3], k), lerp(s[i * 3 + 1], s[i * 3 + 4], k), lerp(s[i * 3 + 2], s[i * 3 + 5], k));
  };

  // ---- the impact: a crown of molten rock thrown up round the rim where the Moon goes in --------------------------------
  // sparks: tens of thousands of glowing droplets on ballistic arcs (cooling white -> orange -> dark red); streaks: the
  // fastest ejecta shooting out in straight bright trails; a glow for the body of the crown; dark smoke and dust rising
  // behind; blocks of the Moon itself broken off and flung out, glowing; meteors as it all comes down round the world
  function buildPlume(X) {
    const rnd = X.rnd, up = MHAT.clone(), e1 = V(0, 1, 0).cross(up).normalize(), e2 = up.clone().cross(e1);
    const onRim = (ring, alt) => { const az = rnd() * 2 * Math.PI;
      const at = up.clone().addScaledVector(e1, Math.cos(az) * ring).addScaledVector(e2, Math.sin(az) * ring).normalize();
      return { at, p: at.clone().multiplyScalar(ER + alt), out: at.clone().sub(up.clone().multiplyScalar(at.dot(up))).normalize() }; };
    const sparks = X.fx(26000, true);
    for (let i = 0; i < sparks.n; i++) {
      const r = onRim(0.2 + 0.1 * rnd(), 0.01 + 0.06 * rnd()), sp = 0.0015 + 0.0085 * Math.pow(rnd(), 1.4), ang = 0.35 + 0.9 * rnd();
      const v = r.at.clone().multiplyScalar(sp * Math.sin(ang)).addScaledVector(r.out, sp * Math.cos(ang));
      sparks.set(i, r.p, v, Math.pow(rnd(), 2.0) * 420, 140 + 600 * rnd(), 0.006 + 0.012 * rnd(), 0.018 + 0.05 * rnd(), rnd());
    }
    sparks.u.heat.value = 1.7; sparks.u.grav.value.copy(up).multiplyScalar(-6e-6); sparks.done();
    const body = X.fx(2600, true);
    for (let i = 0; i < body.n; i++) {
      const r = onRim(0.18 + 0.12 * rnd(), 0.02), sp = 0.0008 + 0.004 * rnd();
      const v = r.at.clone().multiplyScalar(sp).addScaledVector(r.out, sp * 0.6 * rnd());
      body.set(i, r.p, v, Math.pow(rnd(), 1.6) * 500, 300 + 700 * rnd(), 0.05 + 0.06 * rnd(), 0.12 + 0.2 * rnd(), rnd());
    }
    body.u.heat.value = 2.6; body.u.grav.value.copy(up).multiplyScalar(-3e-6); body.u.gain.value = 0.45; body.done();
    const smoke = X.fx(3200, false);
    for (let i = 0; i < smoke.n; i++) {
      const r = onRim(0.12 + 0.35 * rnd(), 0.05 + 0.1 * rnd()), v = r.at.clone().multiplyScalar(0.0006 + 0.0018 * rnd()).addScaledVector(r.out, 0.001 * rnd());
      smoke.set(i, r.p, v, 15 + Math.pow(rnd(), 1.5) * 1500, 1200 + 3000 * rnd(), 0.15, 0.6 + 0.8 * rnd(), rnd());
    }
    smoke.u.smoke.value.setRGB(0.09, 0.065, 0.05); smoke.u.grav.value.copy(up).multiplyScalar(-1e-6); smoke.done();
    const jets = X.streaks(5000);
    for (let i = 0; i < jets.n; i++) {
      const r = onRim(0.2 + 0.09 * rnd(), 0.02), sp = 0.005 + 0.011 * rnd(), ang = 0.3 + 0.9 * rnd();
      const v = r.at.clone().multiplyScalar(sp * Math.sin(ang)).addScaledVector(r.out, sp * Math.cos(ang));
      jets.set(i, r.p, v, Math.pow(rnd(), 2.5) * 160, 25 + 60 * rnd(), 0.12 + 0.35 * rnd(), 0.8 + 1.0 * rnd());
    }
    jets.u.width.value = 1.3; jets.done();
    // blocks of the Moon flung out as it breaks against the Earth (instances after the falling rubble)
    const flung = [];
    for (let i = 0; i < 360; i++) {
      const r = onRim(0.16 + 0.12 * rnd(), 0.15 + 1.2 * rnd()), sp = 0.0008 + 0.004 * rnd();
      flung.push({ p: r.p, v: r.at.clone().multiplyScalar(sp * (0.4 + 0.6 * rnd())).addScaledVector(r.out, sp * (0.5 + rnd())), tb: Math.pow(rnd(), 1.5) * 150,
        size: 0.006 + 0.05 * Math.pow(rnd(), 2.5), ax: V(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize(), w: (rnd() - 0.5) * 0.03 });
    }
    // glows round the rim where the Moon cuts in (the near ones sit right on our horizon)
    const rim = [];
    for (let i = 0; i < 12; i++) {
      const az = i / 12 * 2 * Math.PI, at = up.clone().addScaledVector(e1, Math.cos(az) * 0.27).addScaledVector(e2, Math.sin(az) * 0.27).normalize();
      rim.push({ at, spr: X.glow([[0, 'rgba(255,250,235,1)'], [0.25, 'rgba(255,215,150,0.7)'], [0.6, 'rgba(255,130,50,0.18)'], [1, 'rgba(255,90,30,0)']]), ph: rnd() });
    }
    // the ejecta coming back down all over the world: meteors over the ground ahead of us, as the front passes
    const met = X.streaks(9000);
    for (let i = 0; i < met.n; i++) {
      const ang = 0.2 + 1.1 * Math.sqrt(rnd()), az = rnd() * 2 * Math.PI;
      const at = up.clone().multiplyScalar(Math.cos(ang)).addScaledVector(e1, Math.sin(ang) * Math.cos(az)).addScaledVector(e2, Math.sin(ang) * Math.sin(az)).normalize();
      const tb = 700 * Math.pow(ang / 0.785, 1.8) * (0.6 + 0.8 * rnd()) + 40 + 4200 * Math.pow(rnd(), 1.6);   // it keeps coming down for hours
      const out = at.clone().sub(up.clone().multiplyScalar(at.dot(up))).normalize();
      const v = at.clone().multiplyScalar(-0.006 - 0.004 * rnd()).addScaledVector(out, 0.004 * rnd());
      met.set(i, at.clone().multiplyScalar(ER + 0.13), v, tb, 0.13 / v.length(), 0.08 + 0.14 * rnd(), 0.8 + 1.2 * rnd());
    }
    met.done();
    return { sparks, body, smoke, jets, flung, rim, met, fx: [sparks, body, smoke] };
  }

  // ---- the camera: our head, inside the helmet ------------------------------------------------------------------------
  // Where we look, as poses that follow each other: 'm' — at the Moon (yaw, pitch as offsets from it, so the head keeps
  // tracking it as it sinks; after the touch, at the place where it went in), 'a' — a fixed yaw and pitch (deg) in our
  // own frame (yaw 0 = toward the Moon's bearing, + to the left; pitch from the horizontal). Each pose is reached from
  // the last over its own time with a quintic ease (a head turns smoothly, without a jerk at either end).
  const HEAD = [
    [0.0, 0.0, 'm', 0, 1.5],        // the hook (3 minutes before): the Moon on the horizon in front of us
    [3.0, 0.0, 'm', 0, -26],        // after the rewind: the Moon high up, the Earth along the bottom
    [5.4, 1.4, 'a', -20, -24],      // a look down to the left: the Earth turning under us, day after day
    [8.1, 1.5, 'm', 3, -24],        // back to the Moon
    [10.4, 1.6, 'a', 8, -27],       // down: the ground ahead, the sea coming in
    [12.9, 2.4, 'a', -9, -31],      // a slow look across the water
    [15.2, 1.9, 'a', 5, -25],
    [16.8, 1.6, 'm', 0, -12],       // up to the Moon again
    [20.0, 1.3, 'm', -9, -11],      // a glance aside
    [21.5, 1.4, 'm', 0, -8],
    [26.0, 2.5, 'm', 0, -5],
    [31.0, 1.5, 'm', 0, -3],
    [33.5, 0.45, 'm', -7, -7],      // the flash: the head flinches a little
    [34.3, 1.3, 'm', 2, -2],        // and looks straight at it: the Moon going in
    [39.4, 3.2, 'a', -6, -33],      // down at the burning ground
    [42.2, 1.8, 'a', 9, -29],
  ];
  const quint = u => { u = clamp(u, 0, 1); return u * u * u * (u * (u * 6 - 15) + 10); };
  function poseAt(k, tau, tp) {
    const [, , mode, y, p] = HEAD[k];
    if (mode === 'a') return { yaw: y, pitch: p };
    const tgt = tp < 0 ? moonPos(tp) : MHAT.clone().multiplyScalar(ER + 0.8);
    return { yaw: y, pitch: elevOf(tgt) + p };
  }
  function headAt(tau, tp) {
    let k = 0; while (k + 1 < HEAD.length && tau >= HEAD[k + 1][0]) k++;
    const now = poseAt(k, tau, tp);
    if (k === 0) return now;
    const u = quint((tau - HEAD[k][0]) / Math.max(HEAD[k][1], 1e-3)), was = poseAt(k - 1, tau, tp);
    return { yaw: lerp(was.yaw, now.yaw, u), pitch: lerp(was.pitch, now.pitch, u) };
  }
  // the head's small movements on top, all slow and smooth: a drift, the breath (no shaking: the author wants the view
  // to turn smoothly with the head)
  function headShake(tau) {
    const br = 0.18 * Math.sin(2 * Math.PI * tau / (tau < 20 ? 4.2 : tau < 30 ? 3.0 : 2.4));
    const drift = (a, b) => 0.4 * Math.sin(tau * a + 1) + 0.2 * Math.sin(tau * b + 2);
    return { dp: br + drift(0.31, 0.71), dy: drift(0.23, 0.53), dr: 0.3 * Math.sin(tau * 0.21) };
  }

  const SHOTS = {
    film: {
      dur: 46,
      async setup(X) {
        RUB = buildRubble(X);
        X.plume = buildPlume(X);
        PUFFS = buildPuffs(X);
        X.U.moonDir.value.copy(MHAT); X.U.sun.value.copy(SUN);
        X.moon.scale.setScalar(RM);
        const xa = MHAT.clone().negate(), ya = V(0, 1, 0).sub(xa.clone().multiplyScalar(xa.y)).normalize(), za = xa.clone().cross(ya);
        X.moon.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xa, ya, za));
        X.MU.toEarth.value.set(1, 0, 0);
      },
      frame(X, tau) {
        const tp = tPhys(tau);
        X.state = { tau, tp };
        // the Earth turns under us (at the touch its map lines up with the world)
        const phi = OMEGA * tp;
        X.earth.rotation.y = 0;
        X.U.toBody.value.setFromMatrix4(new THREE.Matrix4().makeRotationY(-phi));
        X.U.cloudLon.value = 0.000003 * tp;                                 // the weather drifts ~1500 km a day
        // thinner cloud while we look down at the water coming in (the map's one day of weather would hide it)
        X.U.cloudK.value = 1 - 0.6 * smooth((tau - 10.4) / 1.2) * (1 - smooth((tau - 16.8) / 1.2));
        // the Moon
        const z = moonZ(tp), zc = Math.max(z, 8.108);
        X.moon.position.copy(MHAT).multiplyScalar(z);
        X.moon.visible = tp < 700;
        X.MU.stretch.value = stretchAt(zc);
        X.RU.moonC.value.copy(X.moon.position); X.RU.moonR.value = RM * (1 + 0.3 * stretchAt(zc));
        X.MU.crack.value = crackAt(zc);
        X.MU.crumble.value = tp < 0 ? crumbleAt(tp) : 1;
        { const pp = X.puffs.geometry.attributes.position, ps = X.puffs.geometry.attributes.psize, pa = X.puffs.geometry.attributes.palpha;
          PUFFS.forEach((f, i) => {
            const age = tp - f.tb, p = posAt(f, tp);
            if (!p || age > f.life || tp > 25) { pa.setX(i, 0); return; }
            const u = age / f.life;
            pp.setXYZ(i, p.x, p.y, p.z); ps.setX(i, lerp(f.s0, f.s1, Math.sqrt(u)));
            pa.setX(i, f.a * smooth(age / 25) * (1 - smooth((u - 0.6) / 0.4)) * (tp > 0 ? 1 - smooth(tp / 20) : 1));
          });
          pp.needsUpdate = ps.needsUpdate = pa.needsUpdate = true; }
        X.MU.spin.value = -(13.18 / 360) * (tp + T_HIT) / 86400;            // its own turn goes on: 13° a day
        X.MU.heat.value = smooth((ER + 0.6 - (z - RM)) / 0.6) * (tp < 0 ? 1 : 1.4);
        X.MU.earthLit.value = 0.4;
        // the tide
        X.U.zeta.value = tp < 0 ? zetaAt(zc) : 3200;
        // moonlight on the night side
        X.U.moonL.value.set(MHAT.x, MHAT.y, MHAT.z, Math.min(0.06, 0.0005 * Math.pow(38.4 / zc, 2)));
        // the rubble
        const dpos = X.dust.geometry.attributes.position, dal = X.dust.geometry.attributes.alpha;
        RUB.dust.forEach((d, i) => {
          const p = posAt(d, tp);
          if (!p) { dal.setX(i, 0); return; }
          dpos.setXYZ(i, p.x, p.y, p.z); dal.setX(i, smooth((tp - d.tb) / 6) * 0.8);
        });
        dpos.needsUpdate = dal.needsUpdate = true;
        const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
        RUB.rocks.forEach((r, i) => {
          const p = posAt(r, tp);
          if (!p) { m4.makeScale(0, 0, 0); X.rocks.setMatrixAt(i, m4); return; }
          q.setFromAxisAngle(r.ax, r.w * (tp - r.tb)); sc.copy(r.asp).multiplyScalar(r.size);
          m4.compose(p, q, sc); X.rocks.setMatrixAt(i, m4);
        });
        X.rocks.instanceMatrix.needsUpdate = true;
        RUB.met.mesh.visible = tp > -400; RUB.met.u.time.value = tp;
        // rocks that have come down: the 8 latest glow on the ground
        const hs = RUB.hits.filter(h => h.t <= tp).slice(-8);
        for (let i = 0; i < 8; i++) { const h = hs[i]; if (h) X.U.hits.value[i].set(h.dir.x, h.dir.y, h.dir.z, tp - h.t); else X.U.hits.value[i].w = -1; }
        // the impact: its light, the plume, the fire spreading round the world, the melt
        const ta = Math.max(tp, 0);
        const fl = tp < 0 ? 0 : (1 - Math.exp(-ta / 4)) * (0.15 + 2.4 * Math.exp(-ta / 90) + 0.25 * Math.exp(-ta / 900)) * 30;
        X.U.flash.value.copy(MHAT).multiplyScalar(ER + 0.6); X.U.flash.value.w = fl; X.U.flashR.value = 2.2;
        X.U.fire.value.set(MHAT.x, MHAT.y, MHAT.z, tp < 0 ? 0 : Math.min(3.2, 0.03 + 0.62 * Math.pow(ta / 600, 0.55)));
        X.U.fire2.value.set(tp < 0 ? 0 : smooth(ta / 20), tp < 0 ? 0 : smooth(ta / 60), tp < 0 ? 0 : smooth(ta / 2400), tp < 0 ? 0 : smooth((ta - 100) / 1500) * 0.8);
        X.U.lights.value = 1 - smooth((ta - 200) / 900);
        for (const f of X.plume.fx) { f.points.visible = tp > 0; f.u.time.value = ta; }
        X.plume.sparks.u.gain.value = 1.1 * (0.4 + 0.6 * Math.exp(-ta / 300));
        X.plume.jets.mesh.visible = tp > 0; X.plume.jets.u.time.value = ta;
        X.plume.met.mesh.visible = tp > 0; X.plume.met.u.time.value = ta;
        // blocks flung out of the impact: after the falling rubble in the same instances, glowing as they fly
        { const base = RUB.rocks.length, hot = X.rocks.geometry.attributes.hot, g = MHAT.clone().multiplyScalar(-6e-6);
          X.plume.flung.forEach((f, i) => {
            const age = ta - f.tb;
            if (tp <= 0 || age < 0) { m4.makeScale(0, 0, 0); X.rocks.setMatrixAt(base + i, m4); hot.setX(base + i, 0); return; }
            const p = f.p.clone().addScaledVector(f.v, age).addScaledVector(g, 0.5 * age * age);
            if (p.length() < ER) { m4.makeScale(0, 0, 0); X.rocks.setMatrixAt(base + i, m4); hot.setX(base + i, 0); return; }
            q.setFromAxisAngle(f.ax, f.w * age); sc.setScalar(f.size * smooth(age / 4)); m4.compose(p, q, sc); X.rocks.setMatrixAt(base + i, m4);
            hot.setX(base + i, 2.2 * Math.exp(-age / 200));
          });
          hot.needsUpdate = true; X.rocks.count = base + X.plume.flung.length; }
        X.U.shk.value.set(tp < 0 ? 0 : 0.05 + 0.9 * Math.pow(ta / 300, 0.6), tp < 0 ? 0 : Math.exp(-ta / 400));
        X.U.pre.value.set(tp < 0 ? 1.4 * smooth((tp + 150) / 150) : 1.4 * Math.exp(-ta / 30), 0.35);
        X.MU.melt.value = tp < 0 ? 0 : smooth(ta / 25);
        for (const r of X.plume.rim) {
          r.spr.visible = tp > -2;
          const k = smooth((tp + 2) / 3) * (0.25 + 0.75 * Math.exp(-ta / 60)) * Math.exp(-ta / 500) * (0.85 + 0.15 * Math.sin(ta * 3 + r.ph * 6));
          r.spr.position.copy(r.at).multiplyScalar(ER + 0.25 + 0.0006 * Math.min(ta, 600)); r.spr.scale.setScalar(1.6 + 0.003 * Math.min(ta, 500));
          r.spr.material.opacity = Math.min(1, k);
        }
        // the fireball over the limb as it goes in
        X.fireball.core.visible = X.fireball.halo.visible = tp > 0;
        if (tp > 0) {
          const fbk = (1 - Math.exp(-ta / 3)) * Math.exp(-ta / 250);
          X.fireball.core.position.copy(MHAT).multiplyScalar(ER + 0.3 + 0.0012 * Math.min(ta, 600)); X.fireball.core.scale.setScalar(1.2 + 0.004 * Math.min(ta, 500));
          X.fireball.core.material.opacity = Math.min(1, fbk * 1.5);
          X.fireball.halo.position.copy(X.fireball.core.position); X.fireball.halo.scale.setScalar(4 + 0.008 * Math.min(ta, 500));
          X.fireball.halo.material.opacity = Math.min(1, fbk);
        }
        // the camera: our head (a head turning leans a little into the turn)
        const hd = headAt(tau, tp), h0 = headAt(tau - 0.04, tp), h1 = headAt(tau + 0.04, tp), hs2 = headShake(tau);
        const yawRate = (h1.yaw - h0.yaw) / 0.08, pitchRate = (h1.pitch - h0.pitch) / 0.08;
        const dir = dirFrom(hd.pitch + hs2.dp, hd.yaw + hs2.dy);
        // the lens: wider while we look round, narrowing on the Moon as it comes
        const fov = tau < 1.7 ? 85 : tau < 3.0 ? lerp(85, 100, smooth((tau - 1.7) / 1.3)) : tau < 22 ? 100 : tau < 33.5 ? lerp(100, 72, smooth((tau - 22) / 11)) : lerp(72, 92, smooth((tau - 38.5) / 4.5));
        const cam = X.camera; cam.fov = fov; cam.updateProjectionMatrix();
        cam.position.copy(A); cam.up.copy(UP); cam.lookAt(A.clone().add(dir));
        cam.rotateZ((hs2.dr - 0.12 * clamp(yawRate, -40, 40)) * D);
        cam.updateMatrixWorld();
        // what the overlay needs (captions.py reads it per frame): the clock, the distance, the tide, the Moon on screen
        const mp = X.moon.position.clone(), ndc = mp.clone().project(cam), dist = mp.distanceTo(A);
        const rpx = Math.tan(Math.atan(RM / dist)) / Math.tan(fov / 2 * D) * X.H / 2;
        X.state = { tau, tp, z, zeta: X.U.zeta.value, mx: (ndc.x + 1) / 2, my: (1 - ndc.y) / 2, mr: rpx / X.H, front: ndc.z < 1 && tp < 0, yawRate, pitchRate };
      },
    },
  };
  window.SHOTS = SHOTS;
  window.MF = { tPhys, moonZ, zetaAt, T_HIT, MHAT, AHAT, SUN, A, elevOf, moonPos };
})();
