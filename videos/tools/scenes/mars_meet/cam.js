// "Знайомся: Марс": the site's own Mars for the globe shots (whole planet, the red surface, Phobos and Deimos, the
// closing pull-back). The 3D flights over the real relief (terrain.js) are laid over the other stretches by post.py,
// so there the camera here just holds still.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;

  window.__sceneSetup = async (r) => {
    const s = r.state, m = r.byId.mars;
    s.index = r.BODIES.indexOf(m); s.mode = 'focus'; s.flight = null;
  };

  // Around Mars in a frame tied to the Sun: e1 towards the Sun (in the orbit plane), up = ecliptic north.
  function at(c, az, el, dist) {
    const { C, e1, e2, up, R, V } = c;
    return new V().copy(C)
      .addScaledVector(e1, Math.cos(el * D) * Math.cos(az * D) * dist * R)
      .addScaledVector(e2, Math.cos(el * D) * Math.sin(az * D) * dist * R)
      .addScaledVector(up, Math.sin(el * D) * dist * R);
  }
  // [start, end, fn(k, ctx)] — the gaps (0–3.4, 9–23.4, 37.4–43.8 s) are covered by the relief flights; there the
  // camera holds a neighbouring shot, so the crossfades never show a jump
  const SHOTS = [
    [0, 3.4, (k, c) => SHOTS[1][2](0, c)],
    // the whole planet, lit three-quarters, turning slowly as the camera swings round
    [3.4, 9.0, (k, c) => { const e = ease(k); return { pos: at(c, lerp(55, 30, e), lerp(18, 10, e), lerp(3.6, 2.9, e)), look: c.C }; }],
    [9.0, 23.4, (k, c) => SHOTS[1][2](1, c)],
    // the red, rusty surface close up: skimming low over the day side
    [23.4, 29.4, (k, c) => { const e = ease(k); return { pos: at(c, lerp(20, -5, e), lerp(30, 12, e), lerp(1.75, 1.42, e)), look: at(c, lerp(-5, -25, e), lerp(5, -5, e), 0.75) }; }],
    // Phobos and Deimos: pulled well back, high above their orbits, both moons and their paths in view
    [29.4, 37.4, (k, c) => { const e = ease(k); return { pos: at(c, lerp(60, 35, e), lerp(58, 48, e), lerp(10.5, 8.8, e)), look: c.C }; }],
    [37.4, 43.8, (k, c) => SHOTS[4][2](1, c)],
    // closing: Mars drifting away under the end card
    [43.8, 50.0, (k, c) => { const e = ease(k); return { pos: at(c, lerp(35, 20, e), lerp(14, 20, e), lerp(3.0, 5.2, e)), look: c.C }; }],
  ];

  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, m = r.byId.mars, t = window.__vt() - (window.__t0 || 0);
    const C = m.world.clone(), up = new V(0, 1, 0);
    const sun = C.clone().negate().normalize();
    const e1 = sun.clone().addScaledVector(up, -sun.dot(up)).normalize(), e2 = new V().crossVectors(up, e1);
    const ctx = { C, e1, e2, up, R: m.radius, V };
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const k = Math.min(1, Math.max(0, (t - shot[0]) / (shot[1] - shot[0])));
    const { pos, look } = shot[2](k, ctx);
    // orbit lines only for the two moons, while they are the subject
    const mo = t > 29.4 && t < 37.4 ? smooth((t - 29.6) / 1.2) * (1 - smooth((t - 36.4) / 1.0)) : 0;
    for (const x of r.BODIES) if (x.orbitLine) {
      const show = (x.id === 'phobos' || x.id === 'deimos') ? mo : 0;
      x.orbitLine.visible = show > 0.01; x.orbitLine.material.opacity = (x.baseOpacity || 0.5) * show * 1.6;
    }
    const cam = r.camera;
    cam.position.copy(pos); cam.up.set(0, 1, 0); cam.lookAt(look);
    r.controls.target.copy(look);
    const near = Math.max(0.003, Math.min(0.3, (pos.distanceTo(C) - m.radius) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
