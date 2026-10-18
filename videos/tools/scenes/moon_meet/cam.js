// "Знайомся: Місяць": the site's Earth and Moon for the shots between the 3D flights (terrain.js; laid over by post.py,
// so in those stretches the camera here just holds a neighbouring shot). Kondratyuk's route is drawn into the scene:
// the ship's orbit round the Moon, the ship, and the small lander going down and back up; then the way from the Earth.
// The clock is driven here: still, except for the tidal-lock shot, where two weeks pass in seven seconds.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  // first quarter: the Moon 90° from the Sun, so beside the Earth both are lit from the same side
  const BASE = Date.parse('2026-10-18T12:00:00Z'), DAY = 86400000;
  const LOCK = [35.2, 42.2];                       // the tidal-lock shot: the clock runs 14 days through it
  // after it the clock goes back (unseen: the 3D flights cover 42.2–58.4 s)
  const simAt = t => t > LOCK[1] + 1 ? BASE : BASE + 14 * DAY * smooth((t - LOCK[0]) / (LOCK[1] - LOCK[0]));
  // the Moon's direction from the Earth at a date, as the site places it (ecliptic, scene axes)
  function moonDir(V, ms) {
    const m = window.moonPos(ms / DAY + 2440587.5);
    return new V(Math.cos(m.lat) * Math.cos(m.lon), Math.sin(m.lat), -Math.cos(m.lat) * Math.sin(m.lon)).normalize();
  }
  const GOLD = 0xffc24a;
  let route = null;

  window.__sceneSetup = async (r) => {
    const s = r.state, T = r.THREE, mo = r.byId.moon;
    s.index = r.BODIES.indexOf(mo); s.mode = 'focus'; s.flight = null;
    s.rate = 1; s.simMs = simAt(0);
    // Kondratyuk's route, drawn round the Moon in its own frame (a group that follows the Moon, not its spin)
    const g = new T.Group(); r.scene.add(g);
    const ringPts = []; for (let i = 0; i <= 128; i++) { const a = i / 128 * Math.PI * 2; ringPts.push(new T.Vector3(Math.cos(a), 0, Math.sin(a))); }
    const ring = new T.Line(new T.BufferGeometry().setFromPoints(ringPts), new T.LineBasicMaterial({ color: GOLD, transparent: true, opacity: 0 }));
    const dot = (size, color) => new T.Points(new T.BufferGeometry().setFromPoints([new T.Vector3()]),
      new T.PointsMaterial({ size, sizeAttenuation: false, color, transparent: true, opacity: 0, depthWrite: false }));
    const ship = dot(15, 0xffffff), lander = dot(11, GOLD);
    const trail = new T.Line(new T.BufferGeometry().setFromPoints(new Array(240).fill(0).map(() => new T.Vector3())),
      new T.LineBasicMaterial({ color: GOLD, transparent: true, opacity: 0 }));
    g.add(ring, ship, lander, trail);
    // the way from the Earth: a curve from low Earth orbit out to the Moon's ring (in world space)
    const way = new T.Line(new T.BufferGeometry().setFromPoints(new Array(160).fill(0).map(() => new T.Vector3())),
      new T.LineBasicMaterial({ color: GOLD, transparent: true, opacity: 0 }));
    r.scene.add(way);
    // a mark on the middle of the near side, fixed to the Moon's surface: it keeps facing the Earth as the Moon goes round
    const near = dot(13, GOLD); near.material.depthTest = true;
    mo.tiltGroup.add(near);
    const toE = r.byId.earth.world.clone().sub(mo.world).normalize();
    mo.tiltGroup.updateMatrixWorld(true);
    const local = mo.tiltGroup.worldToLocal(mo.world.clone().addScaledVector(toE, mo.radius * 1.01));
    near.position.copy(local);
    route = { g, ring, ship, lander, trail, way, near, trailN: 0 };
    // only the Earth, the Moon and the Sun: a planet that happens to be behind them would only puzzle
    for (const b of r.BODIES) if (!['earth', 'moon', 'sun'].includes(b.id) && b.group) b.group.visible = false;
    // no aurora: in these wide shots it reads as a stray green ring
    const E = r.byId.earth;
    for (const m of E.tiltGroup.children) if (m.geometry && m.geometry.parameters && Math.abs(m.geometry.parameters.radius - E.radius * 1.025) < 1e-6) m.visible = false;
  };

  // Kondratyuk's scheme in the ring's frame (unit = the ring's radius, 1.45 Moon radii): the ship circles; at 13 s the
  // lander leaves it, goes down, sits on the Moon for a second, climbs back and meets the ship again at 19 s.
  const RING = 1.45, W = 0.55;                     // ring radius (Moon radii), ship's angular speed (rad/s)
  const shipAng = t => -0.6 + W * (t - 11.2);
  function landerAt(t) {
    const T0 = 13, T1 = 15.3, T2 = 16.3, T3 = 19;
    if (t < T0 || t > T3) return [shipAng(t), RING];
    const aDown = shipAng(T0) + 0.55;                // where it lands: a little ahead along the track
    if (t < T1) { const k = smooth((t - T0) / (T1 - T0)); return [lerp(shipAng(T0), aDown, Math.sqrt(k)), lerp(RING, 1.005, k)]; }
    if (t < T2) return [aDown, 1.005];
    const k = smooth((t - T2) / (T3 - T2));
    return [lerp(aDown, shipAng(T3), k * k), lerp(1.005, RING, Math.sqrt(k))];
  }

  // Around a centre in a frame tied to the Sun: e1 towards the Sun (in the ecliptic), up = ecliptic north.
  function at(c, C, R, az, el, dist) {
    return new c.V().copy(C)
      .addScaledVector(c.e1, Math.cos(el * D) * Math.cos(az * D) * dist * R)
      .addScaledVector(c.e2, Math.cos(el * D) * Math.sin(az * D) * dist * R)
      .addScaledVector(c.up, Math.sin(el * D) * dist * R);
  }
  // Earth and Moon in one tall frame: the camera above and behind the Earth on the Sun's side, looking out along the
  // line to the Moon — the Earth big at the bottom, the Moon further off above it
  function pair(c, back, height, swing) {
    const d = c.M.clone().sub(c.E).normalize();
    let side = new c.V().crossVectors(c.up, d).normalize();
    if (side.dot(c.e1) < 0) side.negate();
    const pos = c.E.clone().addScaledVector(d, -back).addScaledVector(c.up, height).addScaledVector(side, swing);
    return { pos, look: c.E.clone().lerp(c.M, 0.62) };
  }
  // [start, end, fn(k, ctx)]; the 3D flights cover 0–4.6, 27.8–35.2 and 42.2–58.4 s
  // [start, end, fn(k, ctx)]; the 3D flights cover 0–4.6, 27.8–35.2 and 42.2–58.4 s
  const SHOTS = [
    [0, 4.6, (k, c) => SHOTS[1][2](0, c)],
    // the Earth and the Moon (true sizes; the distance between them is shortened), slowly closing in
    [4.6, 11.2, (k, c) => { const e = ease(k); return pair(c, lerp(2.6, 2.2, e), lerp(6.6, 5.6, e), lerp(4.6, 4.2, e)); }],
    // Kondratyuk's route round the Moon: close in, the lit side toward us, the ring seen a little from above
    [11.2, 20.2, (k, c) => { const e = ease(k);
      return { pos: at(c, c.M, c.mr, lerp(40, 25, e), lerp(32, 26, e), lerp(5.6, 5.0, e)), look: c.M }; }],
    // the way from the Earth: both in the frame, the curve drawing itself out to the Moon
    [20.2, 27.8, (k, c) => { const e = ease(k); return pair(c, lerp(3.0, 3.4, e), lerp(7.0, 7.6, e), lerp(4.2, 3.8, e)); }],
    [27.8, 35.2, (k, c) => SHOTS[3][2](1, c)],
    // tidal lock: straight above the Earth, the Moon going half round it with its marked near side always toward the
    // Earth; the half circle fills the tall frame (its ends top and bottom)
    [35.2, 42.2, (k, c) => { const e = smooth(k), bulge = c.lockMid.clone().multiplyScalar(1.15);
      return { pos: c.E.clone().add(bulge).addScaledVector(c.up, lerp(12.6, 13.2, e)), look: c.E.clone().add(bulge), up: c.lockChord }; }],
    [42.2, 58.4, (k, c) => SHOTS[5][2](1, c)],
    // closing: from beside the Earth, its limb low in the frame, the camera drifting out as the Moon draws away
    [58.4, 67, (k, c) => { const e = ease(k), d = c.M.clone().sub(c.E).normalize();
      let side = new c.V().crossVectors(c.up, d).normalize(); if (side.dot(c.e1) < 0) side.negate();
      const pos = c.E.clone().addScaledVector(side, lerp(2.3, 3.1, e)).addScaledVector(c.up, lerp(0.9, 1.4, e)).addScaledVector(d, -0.6);
      return { pos, look: c.M.clone().lerp(c.E, 0.12) }; }],
  ];

  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, s = r.state, t = window.__vt() - (window.__t0 || 0);
    // the next tick adds 1/30 s × 1 min/s = 2 s of sim time, so set the clock just short of where the next frame should be
    s.simMs = simAt(t + 1 / 30) - 2000;
    const E = r.byId.earth, mo = r.byId.moon, C = E.world.clone(), M = mo.world.clone(), up = new V(0, 1, 0);
    const sun = C.clone().negate().normalize();
    const e1 = sun.clone().addScaledVector(up, -sun.dot(up)).normalize(), e2 = new V().crossVectors(up, e1);
    const ctx = { E: C, M, e1, e2, up, mr: mo.radius, V };
    if (window.moonPos) {
      const a = moonDir(V, simAt(LOCK[0])), b = moonDir(V, simAt(LOCK[1]));
      ctx.lockChord = b.clone().sub(a).normalize();
      ctx.lockMid = moonDir(V, BASE + 7 * DAY);
    }
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const { pos, look, up: camUp } = shot[2](Math.min(1, Math.max(0, (t - shot[0]) / (shot[1] - shot[0]))), ctx);

    // the drawings: the ring and dots during the route (11.2–27.8 s), the way from the Earth from 20.2 s
    if (route) {
      const R = route, inR = smooth((t - 11.4) / 0.8) * (1 - smooth((t - 27.2) / 0.6));
      R.g.position.copy(M); R.g.scale.setScalar(mo.radius);
      R.g.quaternion.setFromUnitVectors(new V(0, 1, 0), new V(0.18, 1, 0.1).normalize());   // the ring a little tilted
      R.ring.scale.setScalar(RING); R.ring.material.opacity = 0.85 * inR;
      const sa = shipAng(t);
      R.ship.position.set(Math.cos(sa) * RING, 0, Math.sin(sa) * RING); R.ship.material.opacity = inR;
      const [la, lr] = landerAt(t);
      R.lander.position.set(Math.cos(la) * lr, 0, Math.sin(la) * lr);
      R.lander.material.opacity = smooth((t - 12.6) / 0.4) * inR;
      // the lander's track, from where it left the ship
      const tp = R.trail.geometry.attributes.position, n = tp.count;
      const tEnd = Math.min(t, 19), tBeg = 13;
      for (let i = 0; i < n; i++) {
        const [a, rr] = landerAt(tBeg + (tEnd - tBeg) * i / (n - 1));
        tp.setXYZ(i, Math.cos(a) * rr, 0, Math.sin(a) * rr);
      }
      tp.needsUpdate = true;
      R.trail.material.opacity = t > 13 ? 0.8 * inR : 0;
      // the way out from the Earth: leaves low orbit on the far side of the Earth from the Moon's direction, swings out
      // and meets the ring
      const wp = R.way.geometry.attributes.position, wn = wp.count, toM = M.clone().sub(C).normalize();
      const side = new V().crossVectors(up, toM).normalize();
      const A = C.clone().addScaledVector(side, -E.radius * 1.15);
      const B = M.clone().addScaledVector(side, mo.radius * RING);
      const P1 = C.clone().addScaledVector(side, -E.radius * 2.2).addScaledVector(toM, E.radius * 1.5);
      const P2 = M.clone().addScaledVector(side, mo.radius * 3.0).addScaledVector(toM, -mo.radius * 2.5);
      const grow = smooth((t - 20.8) / 3.2);
      for (let i = 0; i < wn; i++) {
        const u = grow * i / (wn - 1), v = 1 - u;
        wp.setXYZ(i, v * v * v * A.x + 3 * v * v * u * P1.x + 3 * v * u * u * P2.x + u * u * u * B.x,
          v * v * v * A.y + 3 * v * v * u * P1.y + 3 * v * u * u * P2.y + u * u * u * B.y,
          v * v * v * A.z + 3 * v * v * u * P1.z + 3 * v * u * u * P2.z + u * u * u * B.z);
      }
      wp.needsUpdate = true;
      R.way.material.opacity = 0.95 * smooth((t - 20.6) / 0.4) * (1 - smooth((t - 27.2) / 0.6));
      R.near.material.opacity = smooth((t - 35.6) / 0.6) * (1 - smooth((t - 41.6) / 0.5));
    }
    // the Moon's orbit only while it goes round; other orbits and the belts would clutter the frame
    const showOrbit = smooth((t - 35.4) / 0.8) * (1 - smooth((t - 41.6) / 0.6));
    for (const x of r.BODIES) if (x.orbitLine) {
      const show = x.id === 'moon' ? showOrbit : 0;
      x.orbitLine.visible = show > 0.01; x.orbitLine.material.opacity = (x.baseOpacity || 0.5) * show * 1.6;
    }
    const cam = r.camera;
    cam.position.copy(pos); cam.up.copy(camUp || up); cam.lookAt(look);
    r.controls.target.copy(look);
    const near = Math.max(0.003, Math.min(0.3, Math.min(pos.distanceTo(C) - E.radius * 1.1, pos.distanceTo(M) - mo.radius) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
