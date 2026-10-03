// Total solar eclipse of 2 August 2027: camera script and scene clock. Runs in the page (injected before load).
// The shadow is the site's own: real Sun–Moon–Earth geometry, so it crosses the map where and when it really will.
// Time on the video is mapped to the date by scene.json "clock": [[video s, minutes after 00:00 UTC], ...].
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const DAY = Date.parse('2027-08-02T00:00:00Z');
  let CLOCK = [[0, 600]];

  // Minutes after midnight UTC at video time t: piecewise linear between the keys, eased inside each piece.
  function minutesAt(t) {
    if (t <= CLOCK[0][0]) return CLOCK[0][1];
    for (let i = 1; i < CLOCK.length; i++) {
      const [t0, m0] = CLOCK[i - 1], [t1, m1] = CLOCK[i];
      if (t <= t1) return lerp(m0, m1, (t - t0) / (t1 - t0));
    }
    return CLOCK[CLOCK.length - 1][1];
  }

  window.__sceneSetup = async (r, cfg) => {
    const s = r.state, E = r.byId.earth;
    CLOCK = cfg.clock || CLOCK;
    s.index = r.BODIES.indexOf(E); s.mode = 'focus'; s.flight = null;
    s.rate = 1;                                    // 1 min/s: Earth turns by the real sidereal time
    // No aurora here: on the limb in daylight shots it reads as a stray flash.
    for (const m of E.tiltGroup.children) if (m.geometry && m.geometry.parameters && Math.abs(m.geometry.parameters.radius - E.radius * 1.025) < 1e-6) m.visible = false;
    s.simMs = DAY + minutesAt(0) * 60000;
  };

  // A point above the Earth at (lat, lon), h Earth radii from the centre, in world coordinates.
  function geo(c, lat, lon, h) {
    const l = new c.V(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
    return l.applyQuaternion(c.q).multiplyScalar(c.R * h).add(c.C);
  }
  // The centre line of the shadow, as the site computes it (minutes after 00:00 UTC, lat, lon), every 15 minutes.
  // The camera follows this fixed track through a smooth spline, rather than chasing the live shadow point (which
  // crawls along the limb before the shadow touches the Earth and then jumps, swinging the camera).
  const TRACK = [[510, 32.5, -31.7], [525, 36.0, -10.6], [540, 36.2, 1.5], [555, 35.0, 10.7], [570, 33.2, 18.1],
    [585, 30.8, 24.3], [600, 28.0, 29.8], [615, 24.8, 34.7], [630, 21.3, 39.3], [645, 17.4, 43.9], [660, 13.2, 48.8],
    [675, 8.4, 54.3], [690, 2.7, 61.6]];
  function trackAt(m) {
    const i = Math.max(0, Math.min(TRACK.length - 2, Math.floor((m - TRACK[0][0]) / 15)));
    const f = (m - TRACK[i][0]) / 15, P = j => TRACK[Math.max(0, Math.min(TRACK.length - 1, j))];
    const cr = (a, b, c2, d, t) => 0.5 * (2 * b + (c2 - a) * t + (2 * a - 5 * b + 4 * c2 - d) * t * t + (3 * b - a - 3 * c2 + d) * t * t * t);
    return [1, 2].map(k => cr(P(i - 1)[k], P(i)[k], P(i + 1)[k], P(i + 2)[k], f));
  }


  // Shots: [start, end, fn(k, ctx) -> { pos, look, up? }].
  const SHOTS = [
    // Hook: the dark spot over the Libyan desert; slow push in, riding along with it.
    [0, 8, (k, c) => { const e = ease(k), p = c.spot; return { pos: geo(c, p[0] + 3, p[1] - 1, lerp(2.3, 1.85, e)), look: geo(c, p[0] - 1, p[1], 0.2) }; }],
    // Line-up, seen from the side: the Sun's light from one side, the Moon right on the line between it and the Earth.
    [8, 16, (k, c) => {
      const e = ease(k), toSun = c.C.clone().negate().normalize();
      const side = new c.V().crossVectors(toSun, c.n).normalize();
      const mid = c.C.clone().lerp(c.M, 0.5);
      const pos = mid.clone().addScaledVector(side, lerp(9, 7.5, e) * c.R).addScaledVector(toSun, lerp(0.2, 0.9, e) * c.R).addScaledVector(c.n, 0.8 * c.R);
      return { pos, look: mid };
    }],
    // The shadow comes in from the Atlantic at sunrise and sweeps over Spain and North Africa: the camera rides along,
    // a little north of the track and slightly behind, on the day side from the first frame.
    [16, 33, (k, c) => { const e = smooth(k), p = c.spot; return { pos: geo(c, p[0] + 7, p[1] - 3, lerp(2.8, 2.2, e)), look: geo(c, p[0], p[1], 0.2) }; }],
    // Egypt, the longest totality: the same move carries on and closes in over the desert west of the Nile.
    [33, 41, (k, c) => {
      const e = ease(k), p = c.spot;
      return { pos: geo(c, p[0] + lerp(7, 2.5, e), p[1] - lerp(3, 1, e), lerp(2.2, 1.6, e)), look: geo(c, p[0] - lerp(0, 1, e), p[1], lerp(0.2, 0.1, e)) };
    }],
    // From the ground's point of view: the Moon slides over the Sun and the corona comes out. Camera on the Sun–Moon line.
    [41, 49, (k, c) => {
      const e = ease(k);
      const axis = c.Sun.clone().sub(c.M).normalize();
      const side = new c.V().crossVectors(axis, c.n).normalize();
      const pos = c.M.clone().addScaledVector(axis, -c.behind).addScaledVector(side, lerp(0.05, 0, e) * c.mr).addScaledVector(c.n, lerp(0.3, 0, Math.min(1, e * 1.8)) * c.mr);
      return { pos, look: c.M.clone().addScaledVector(axis, 5), up: c.n, fov: 100 };
    }],
    // On across Arabia, Yemen and Somalia, pulling back.
    [49, 56, (k, c) => { const e = smooth(k), p = c.spot; return { pos: geo(c, p[0] + 9, p[1] - 6, lerp(2.3, 3.0, e)), look: geo(c, p[0], p[1], 0.2) }; }],
    // One unbroken move to the end: from above Ukraine (its partial eclipse), looking south at the shadow over Libya,
    // the camera slowly rises and swings south until the whole lit Earth is in view for the end card. The height grows
    // slowly at first, so Ukraine stays in the frame while its caption is on.
    [56, 72, (k, c) => {
      const e = ease(k), climb = smooth(Math.pow(k, 1.4));
      const pos = geo(c, lerp(56, 32, e), lerp(30, 23, e), lerp(2.2, 5.0, climb));
      return { pos, look: geo(c, lerp(38, 28, e), lerp(28, 24, e), 0.2).lerp(c.C, smooth((k - 0.25) / 0.6)) };
    }],
  ];

  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, E = r.byId.earth, s = r.state, t = window.__vt() - (window.__t0 || 0);
    // Drive the clock: the next tick adds 1/30 s × 60 (1 min/s), so set it just short of where the next frame should be.
    s.simMs = DAY + minutesAt(t + 1 / 30) * 60000 - 2000;
    const C = E.world.clone(), q = E.mesh.getWorldQuaternion(new r.THREE.Quaternion());
    const n = new V(0, 1, 0).applyQuaternion(E.tiltGroup.getWorldQuaternion(new r.THREE.Quaternion())).normalize();
    const mo = r.byId.moon, M = mo.world.clone(), Sun = r.byId.sun.world.clone(), sr = r.byId.sun.radius;
    // Distance behind the Moon where it just covers the Sun (the Moon's disc ~8 % larger, as on 2 August 2027).
    const dsm = Sun.distanceTo(M), behind = mo.radius * dsm / (sr * 1.08 - mo.radius);
    const ctx = { C, q, n, M, Sun, R: E.radius, mr: mo.radius, behind, V, spot: trackAt(minutesAt(t)) };
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const k = (t - shot[0]) / (shot[1] - shot[0]);
    let { pos, look, up, fov } = shot[2](Math.min(1, Math.max(0, k)), ctx);
    // No cut between the line-up and the sweep: the camera flies from the side view down to the shadow, the Earth
    // growing gradually (a cut straight to the full, bright globe read as a white flash).
    if (t > 14.5 && t < 20) {
      const at = (sh, tt) => sh[2](Math.min(1, Math.max(0, (tt - sh[0]) / (sh[1] - sh[0]))), ctx);
      const A = at(SHOTS[1], t), B = at(SHOTS[2], t), w = smooth((t - 14.5) / 5.5);
      const dA = A.pos.distanceTo(C), dB = B.pos.distanceTo(C);
      const dir = A.pos.clone().sub(C).normalize().lerp(B.pos.clone().sub(C).normalize(), w).normalize();
      pos = C.clone().addScaledVector(dir, Math.exp(lerp(Math.log(dA), Math.log(dB), w)));
      look = A.look.clone().lerp(B.look, w); up = n; fov = undefined;
    }
    // Orbit lines and the asteroid/Kuiper belts (a dotted band when seen edge-on) would only clutter the shots.
    for (const x of r.BODIES) if (x.orbitLine) x.orbitLine.visible = false;
    r.asteroidBelt.visible = r.kuiperBelt.visible = false;
    const cam = r.camera;
    // A wide lens only for the eclipse seen from the ground, so the whole corona fits around the Moon.
    if (window.__fov0 == null) window.__fov0 = cam.fov;
    const f = fov || window.__fov0;
    if (cam.fov !== f) { cam.fov = f; cam.updateProjectionMatrix(); }
    cam.position.copy(pos);
    cam.up.copy(up || n);
    cam.lookAt(look);
    r.controls.target.copy(look);
    const dE = pos.distanceTo(C) - E.radius * 1.1, dM = pos.distanceTo(M) - mo.radius;
    const near = Math.max(0.002, Math.min(0.5, Math.min(dE, dM) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
