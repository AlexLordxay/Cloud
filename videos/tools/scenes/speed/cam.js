// "You are flying right now": close to the night-time Earth over Ukraine while it turns into the day, then the camera
// pulls back to the Earth running along its orbit, then to the whole Solar System among the stars (the Sun's path round
// the Galaxy is told in the captions; the site has no Galaxy to show). The scene drives the simulated date itself.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const ms = s => Date.parse(s), DAY = 86400000;
  const T0 = ms('2026-10-08T02:30:00Z');   // Kyiv 05:30, still dark; the dawn reaches it within the first seconds
  const iin = x => x * x;
  // [t, date, curve for the segment ending here]
  const DATES = [
    [0, T0], [9, T0 + 5 * 3600000, x => x],            // the night over Ukraine turns into morning
    [17, T0 + 62 * DAY, iin],                          // two months along the orbit
    [31, T0 + 3 * 365.25 * DAY, iin],                  // three years: the inner planets circle, the outer ones creep
    [35, T0 + 3.2 * 365.25 * DAY, x => x],
  ];
  function simDate(t) {
    for (let i = 0; i < DATES.length - 1; i++) {
      const [ta, da] = DATES[i], [tb, db, f = x => x] = DATES[i + 1];
      if (t <= tb) return da + (db - da) * f(Math.min(1, Math.max(0, (t - ta) / (tb - ta))));
    }
    return DATES[DATES.length - 1][1];
  }

  let ready = false, dir0 = null, far = null;
  const N = () => new window.__rec.THREE.Vector3(0, 1, 0);   // ecliptic north in scene axes

  function geoOf(r, lat, lon, h) {
    const E = r.byId.earth, q = E.mesh.getWorldQuaternion(new r.THREE.Quaternion());
    const l = new r.THREE.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
    return l.applyQuaternion(q).multiplyScalar(E.radius * h).add(E.world);
  }

  window.__sceneSetup = async (r) => {
    const s = r.state;
    s.index = r.BODIES.indexOf(r.byId.earth); s.mode = 'focus'; s.flight = null;
    // The camera holds one direction in space while the Earth turns under it: the one that has Kyiv in the middle of the
    // shot, at 4.5 s (so Ukraine crosses the frame from the night into the morning).
    s.rate = 0; s.simMs = simDate(4.5); window.__step(1 / 30);
    const E = r.byId.earth;
    dir0 = geoOf(r, 50.45, 30.52, 1).sub(E.world).normalize();
    s.simMs = simDate(0); window.__step(1 / 30);
    // No aurora (a bright green band right in the opening shot).
    for (const m of E.tiltGroup.children) if (m.geometry && m.geometry.parameters && Math.abs(m.geometry.parameters.radius - E.radius * 1.025) < 1e-6) m.visible = false;
    ready = true;
  };

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, T = r.THREE, V = T.Vector3, t = window.__vt() - (window.__t0 || 0);
    r.state.simMs = simDate(t + 1 / 30);
    const E = r.byId.earth, C = E.world.clone(), R = E.radius, n = N();
    // Behind the Earth on its orbit and above it: the orbit, the Sun and the Earth's motion all in view.
    const vel = new V().crossVectors(n, C).normalize();          // direction of travel (anticlockwise seen from the north)
    const behind = vel.clone().negate().multiplyScalar(0.75).addScaledVector(C.clone().normalize(), 0.25).addScaledVector(n, 0.6).normalize();

    let pos, look, up;
    // One continuous move: 4.6 R over Kyiv (the whole disc in the narrow frame) → 90 units behind and above the Earth (t 9–17) → the whole system from
    // 430 units (25 s) → 750 units (31 s). The point looked at slides from the Earth to the Sun; the camera always stays
    // well above the planets' plane, so it never passes close to the Sun.
    if (t >= 17 && !far) far = behind.clone();
    const back = far || behind;
    const top = back.clone().setY(0).normalize().multiplyScalar(0.55).addScaledVector(n, 0.85).normalize();
    let dir = dir0.clone().lerp(back, smooth((t - 8.5) / 5)).normalize();
    if (t >= 17) dir = back.clone().lerp(top, smooth((t - 17) / 6)).normalize().applyAxisAngle(n, -0.35 * smooth((t - 17) / 18));
    const d = t < 17 ? Math.exp(lerp(Math.log(R * 4.6), Math.log(90), ease((t - 9) / 8)))
                     : Math.exp(lerp(Math.log(90), Math.log(430), ease((t - 17) / 8))) * lerp(1, 1.75, ease((t - 25) / 9));
    const centre = C.clone().lerp(new V(), smooth((t - 11) / 9));
    pos = centre.clone().addScaledVector(dir, d);
    look = centre;
    up = geoOf(r, 90, 0, 1).sub(C).normalize().lerp(n, smooth((t - 8.5) / 5)).normalize();

    // Orbits: only the Earth's while it runs along it, then all the planets'.
    const oAll = smooth((t - 16) / 3), oEarth = smooth((t - 9.5) / 2);
    for (const x of r.BODIES) if (x.orbitLine) {
      const o = x.parent ? 0 : x === E ? Math.max(0.55 * oEarth * (1 - oAll), x.baseOpacity * 1.6 * oAll) : x.baseOpacity * 1.6 * oAll;
      x.orbitLine.visible = o > 0.003; x.orbitLine.material.opacity = o;
    }
    r.asteroidBelt.visible = r.kuiperBelt.visible = t > 16;

    const cam = r.camera;
    cam.position.copy(pos); cam.up.copy(up); cam.lookAt(look);
    r.controls.target.copy(look);
    const near = Math.max(0.002, Math.min(0.5, (pos.distanceTo(C) - R * 1.05) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
