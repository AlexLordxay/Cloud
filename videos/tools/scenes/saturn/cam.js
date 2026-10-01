// Saturn short: camera script and scene setup. Runs in the page (injected before load, after clock.js).
// Times are on a 60 s grid stretched by TS (1.2 → 72 s), so every caption stays on screen ~1 s longer.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const TS = 1.2;

  // Setup after the site has loaded (date and speed are already set from scene.json).
  window.__sceneSetup = async (r, cfg) => {
    const s = r.state, T = r.THREE, sat = r.byId.saturn, ti = r.byId.titan;
    s.index = r.BODIES.indexOf(sat); s.mode = 'focus'; s.flight = null;
    // Saturn's real north pole (IAU: RA 40.589°, Dec 83.537° → ecliptic λ 79.5°, β 61.9°), so the Sun lights the rings as on the date.
    const q = new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 1, 0), new T.Vector3(0.08548, 0.88252, -0.46244).normalize());
    sat.tiltGroup.quaternion.copy(q);
    for (const m of sat.moons) if (m.planeTilt == null) m.plane.quaternion.copy(q);
    // Put Titan where the Titan shot (its middle, 55.2 s in) sees it and Saturn lit from ~40° off the Sun.
    const keep = s.simMs;
    s.simMs = keep + (1.5 + 55.2) * 3600 * 1000;   // warm-up + 55.2 s at 1 hour per second
    let best = null;
    for (let k = 0; k < 72; k++) {
      ti.phase = k / 72 * Math.PI * 2;
      s.paused = true; window.__step(0); s.paused = false;
      const C = sat.world, n = new T.Vector3(0, 1, 0).applyQuaternion(sat.tiltGroup.getWorldQuaternion(new T.Quaternion()));
      const sun = C.clone().negate().normalize(), e1 = sun.clone().addScaledVector(n, -sun.dot(n)).normalize(), e2 = new T.Vector3().crossVectors(n, e1);
      const d = ti.world.clone().sub(C);
      const az = Math.atan2(d.dot(e2), d.dot(e1)) / D, err = Math.abs(((az - 40) + 540) % 360 - 180);
      if (!best || err < best.err) best = { err, phase: ti.phase, az };
    }
    ti.phase = best.phase; s.simMs = keep;
    console.log('[scene] titan phase', best.phase.toFixed(3), 'az', best.az.toFixed(1));
    // Titan's infrared map and seas, for the "under the haze" moment.
    await new Promise(res => {
      const ld = new T.TextureLoader();
      ld.load('textures/titan_surface.jpg', t => {
        t.encoding = T.sRGBEncoding; t.wrapS = T.RepeatWrapping; r.titanU.surfMap.value = t;
        ld.load('textures/titan_lakes.png', l => { l.wrapS = T.RepeatWrapping; r.titanU.lakeMap.value = l; res(); });
      });
    });
  };

  // Camera positions around Saturn in its own frame: e1 = towards the Sun (in the ring plane), n = north pole.
  function sat(ctx, az, el, dist) {
    const { C, e1, e2, n, R, V } = ctx;
    return new V().copy(C)
      .addScaledVector(e1, Math.cos(el * D) * Math.cos(az * D) * dist * R)
      .addScaledVector(e2, Math.cos(el * D) * Math.sin(az * D) * dist * R)
      .addScaledVector(n, Math.sin(el * D) * dist * R);
  }
  // Shots: [start, end, fn(k, ctx) -> { pos, look }], k = 0..1 within the shot.
  const SHOTS = [
    // flight in from above the planets, past Jupiter
    [0, 7.5 * TS, (k, c) => { const e = ease(k); return { pos: sat(c, lerp(75, 30, e), lerp(48, 22, e), lerp(70, 7.5, Math.pow(e, 0.7))), look: c.C }; }],
    // slow arc over the rings on the day side
    [7.5 * TS, 19 * TS, (k, c) => { const e = ease(k); return { pos: sat(c, lerp(30, -35, e), lerp(22, 12, e), lerp(7.5, 5.2, e)), look: c.C }; }],
    // climb to the north pole and its hexagon
    [19 * TS, 30 * TS, (k, c) => { const e = ease(k); return { pos: sat(c, lerp(-35, -10, e), lerp(12, 66, e), lerp(5.2, 3.5, e)), look: c.C }; }],
    // dive down to skim the lit rings
    [30 * TS, 41 * TS, (k, c) => { const e = ease(k); return { pos: sat(c, lerp(-10, 45, e), lerp(66, 7, e), lerp(3.5, 3.25, e)), look: c.C }; }],
    // Titan in front, Saturn behind it
    [41 * TS, 51 * TS, (k, c) => {
      const e = ease(k), T = c.titan, V = c.V;
      const away = new V().copy(T).sub(c.C).normalize();
      const side = new V().crossVectors(away, c.n).normalize();
      const pos = new V().copy(T).addScaledVector(away, lerp(9, 5.5, e) * c.tr).addScaledVector(side, lerp(3.5, -2.5, e) * c.tr).addScaledVector(c.n, lerp(1.2, 0.8, e) * c.tr);
      return { pos, look: new V().copy(T).lerp(c.C, lerp(0.12, 0.2, e)) };
    }],
    // pull back for the end card
    [51 * TS, 60 * TS, (k, c) => { const e = ease(k); return { pos: sat(c, lerp(40, 15, e), lerp(16, 26, e), lerp(6, 17, e)), look: c.C }; }],
  ];

  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, s = r.byId.saturn, t = window.__vt() - (window.__t0 || 0);
    const C = s.world.clone();
    const n = new V(0, 1, 0).applyQuaternion(s.tiltGroup.getWorldQuaternion(new r.THREE.Quaternion())).normalize();
    const sun = C.clone().negate().normalize();
    const e1 = sun.clone().addScaledVector(n, -sun.dot(n)).normalize();
    const e2 = new V().crossVectors(n, e1);
    const titan = r.byId.titan.world.clone();
    const ctx = { C, n, e1, e2, R: s.radius, V, titan, tr: r.byId.titan.radius };
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const k = (t - shot[0]) / (shot[1] - shot[0]);
    let { pos, look } = shot[2](Math.min(1, Math.max(0, k)), ctx);
    // No cut from Titan to the closing shot: glide from the end of the Titan shot into the pull-back over ~2.6 s.
    const T5 = 51 * TS, GLIDE = 2.6;
    if (t >= T5 && t < T5 + GLIDE) {
      const from = SHOTS[4][2](1, ctx), w = smooth((t - T5) / GLIDE);
      pos = from.pos.clone().lerp(pos, w);
      look = from.look.clone().lerp(look, w);
    }
    // Orbit lines: visible in the wide opening, fading out as we close in.
    const of = 1 - smooth((t - 2.4) / 4.8);
    for (const x of r.BODIES) if (x.orbitLine) { x.orbitLine.visible = of > 0.01; x.orbitLine.material.opacity = x.baseOpacity * of * 1.4; }
    // Under Titan's haze while the caption about methane seas is on; the haze returns slowly as the camera pulls away.
    r.titanU.surface.value = t > 41 * TS && t < 51 * TS + 3.0 ? 0.9 * smooth((t - 56.0) / 1.6) * (1 - smooth((t - 60.4) / 2.6)) : 0;
    const cam = r.camera;
    cam.position.copy(pos);
    cam.up.set(0, 1, 0);
    cam.lookAt(look);
    r.controls.target.copy(look);
    // Near plane from the closest surface, so close passes don't clip and far ones keep depth precision.
    const dS = pos.distanceTo(C) - s.radius * 2.3, dT = pos.distanceTo(titan) - r.byId.titan.radius;
    const near = Math.max(0.003, Math.min(0.5, Math.min(Math.max(dS, pos.distanceTo(C) - s.radius), dT) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
