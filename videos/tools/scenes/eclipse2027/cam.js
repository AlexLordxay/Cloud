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
    s.simMs = DAY + minutesAt(0) * 60000;
  };

  // A point above the Earth at (lat, lon), h Earth radii from the centre, in world coordinates.
  function geo(c, lat, lon, h) {
    const l = new c.V(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
    return l.applyQuaternion(c.q).multiplyScalar(c.R * h).add(c.C);
  }
  // Where the shadow axis meets the Earth (or the nearest point of the limb when it misses), as [lat, lon];
  // eased towards the previous value so the camera glides rather than jitters.
  let spot = null;
  function shadowSpot(r, qInv) {
    const U = r.earthU, M = U.eMoon.value, A = U.eAxis.value, al0 = -M.dot(A);
    const P = M.clone().addScaledVector(A, al0), miss = P.length();
    const pt = miss < 1 ? M.clone().addScaledVector(A, al0 - Math.sqrt(1 - miss * miss)) : P.normalize();
    const l = pt.normalize().applyQuaternion(qInv);
    const now = [Math.asin(l.y) / D, Math.atan2(-l.z, l.x) / D];
    if (!spot || Math.abs(now[1] - spot[1]) > 20) spot = now;
    else spot = [lerp(spot[0], now[0], 0.08), lerp(spot[1], now[1], 0.08)];
    return spot;
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
    // The shadow comes in from the Atlantic at sunrise and sweeps over Spain and North Africa: the camera rides along.
    [16, 33, (k, c) => { const e = smooth(k), p = c.spot; return { pos: geo(c, p[0] + 7, p[1] - 3, lerp(2.8, 2.2, e)), look: geo(c, p[0], p[1], 0.2) }; }],
    // Egypt, the longest totality: close in over the desert west of the Nile.
    [33, 41, (k, c) => { const e = ease(k), p = c.spot; return { pos: geo(c, p[0] + 2.5, p[1] - 1, lerp(1.8, 1.6, e)), look: geo(c, p[0] - 1, p[1], 0.1) }; }],
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
    const ctx = { C, q, n, M, Sun, R: E.radius, mr: mo.radius, behind, V, spot: shadowSpot(r, q.clone().invert()) };
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const k = (t - shot[0]) / (shot[1] - shot[0]);
    const { pos, look, up, fov } = shot[2](Math.min(1, Math.max(0, k)), ctx);
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
