// "Знайомся: Венера": the site's own Venus for the globe shots — the planet turning (backwards, as it does) while the
// voice tells of its slow retrograde spin, and the closing pull-back under the question and the end card. The rest of
// the video is the 3D relief and drawn pieces (assemble.py).
(() => {
  const ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;

  window.__sceneSetup = async (r) => {
    const s = r.state, v = r.byId.venus;
    s.index = r.BODIES.indexOf(v); s.mode = 'focus'; s.flight = null;
  };

  // Around Venus in a frame tied to the Sun: e1 towards the Sun (in the orbit plane), up = ecliptic north.
  function at(c, az, el, dist) {
    const { C, e1, e2, up, R, V } = c;
    return new V().copy(C)
      .addScaledVector(e1, Math.cos(el * D) * Math.cos(az * D) * dist * R)
      .addScaledVector(e2, Math.cos(el * D) * Math.sin(az * D) * dist * R)
      .addScaledVector(up, Math.sin(el * D) * dist * R);
  }
  // [start, end, fn(k, ctx)] in recording time. Only 2.8–18.6 s is recorded (frames.sh): 2.8–11.4 the turning globe
  // (video 2.8–11.4), 11.4–18.6 the closing pull-back (laid at video 71.3–78.5 by assemble.py)
  const SHOTS = [
    [0, 2.8, (k, c) => SHOTS[1][2](0, c)],
    // the whole planet three-quarters lit; the camera swings the opposite way to its spin, so the turn reads
    [2.8, 11.4, (k, c) => { const e = ease(k); return { pos: at(c, lerp(40, 70, e), lerp(14, 8, e), lerp(4.6, 3.9, e)), look: c.C }; }],
    // closing: Venus drawing away under the question and the end card
    [11.4, 18.6, (k, c) => { const e = ease(k); return { pos: at(c, lerp(35, 22, e), lerp(12, 20, e), lerp(4.0, 7.0, e)), look: c.C }; }],
  ];

  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, v = r.byId.venus, t = window.__vt() - (window.__t0 || 0);
    const C = v.world.clone(), up = new V(0, 1, 0);
    const sun = C.clone().negate().normalize();
    const e1 = sun.clone().addScaledVector(up, -sun.dot(up)).normalize(), e2 = new V().crossVectors(up, e1);
    const ctx = { C, e1, e2, up, R: v.radius, V };
    let shot = SHOTS[SHOTS.length - 1];
    for (const sh of SHOTS) if (t < sh[1]) { shot = sh; break; }
    const k = Math.min(1, Math.max(0, (t - shot[0]) / (shot[1] - shot[0])));
    const { pos, look } = shot[2](k, ctx);
    for (const x of r.BODIES) if (x.orbitLine) x.orbitLine.visible = false;
    // only Venus in view: the site draws the planets enlarged, so the neighbours would crowd the background
    for (const x of r.BODIES) { x.group.visible = x === v || x === v.parent; x.tiltGroup.visible = x === v; }
    const cam = r.camera;
    cam.position.copy(pos); cam.up.set(0, 1, 0); cam.lookAt(look);
    r.controls.target.copy(look);
    const near = Math.max(0.003, Math.min(0.3, (pos.distanceTo(C) - v.radius) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
