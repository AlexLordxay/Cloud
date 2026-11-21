// Wallpapers: one static composition per second (render with FAST=1 stills at 0.5, 1.5, …).
// Each shot: body, camera azimuth from the Sun direction (0 = fully lit), elevation, distance in radii,
// and `drop` — how far the body sits below the screen centre (in radii), leaving the top free for the lock-screen clock.
(() => {
  const D = Math.PI / 180;
  const SHOTS = [
    { id: 'mercury', az: 70, el: 10, dist: 5.2, drop: 0.25 },
  ];
  window.__sceneSetup = async (r) => {
    const s = r.state, T = r.THREE, sat = r.byId.saturn;
    s.index = r.BODIES.indexOf(sat); s.mode = 'focus'; s.flight = null;
    const q = new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 1, 0), new T.Vector3(0.08548, 0.88252, -0.46244).normalize());
    sat.tiltGroup.quaternion.copy(q);
    for (const m of sat.moons) if (m.planeTilt == null) m.plane.quaternion.copy(q);
    s.rate = 0;
  };
  window.__recCam = () => {
    const r = window.__rec, V = r.THREE.Vector3, t = window.__vt() - (window.__t0 || 0);
    const sh = SHOTS[Math.max(0, Math.min(SHOTS.length - 1, Math.floor(t)))];
    const b = r.byId[sh.id], C = b.world.clone(), R = b.radius;
    const n = sh.sat ? new V(0, 1, 0).applyQuaternion(b.tiltGroup.getWorldQuaternion(new r.THREE.Quaternion())).normalize() : new V(0, 1, 0);
    const sun = C.clone().negate().normalize();
    const e1 = sun.clone().addScaledVector(n, -sun.dot(n)).normalize(), e2 = new V().crossVectors(n, e1);
    const pos = C.clone()
      .addScaledVector(e1, Math.cos(sh.el * D) * Math.cos(sh.az * D) * sh.dist * R)
      .addScaledVector(e2, Math.cos(sh.el * D) * Math.sin(sh.az * D) * sh.dist * R)
      .addScaledVector(n, Math.sin(sh.el * D) * sh.dist * R);
    const keep = new Set([sh.id, 'sun', ...(sh.keep || [])]);
    for (const x of r.BODIES) { const ok = (keep.has(x.id) && !(x.id === 'earth' && sh.id === 'moon')) || (x.parent && keep.has(x.parent.id)); if (x.group) x.group.visible = ok || keep.has(x.id); if (x.tiltGroup) x.tiltGroup.visible = ok; }
    const cam = r.camera;
    cam.position.copy(pos); cam.up.copy(n); cam.lookAt(C);
    // shift the aim up so the body sits lower on screen
    const up = new V().setFromMatrixColumn(cam.matrixWorld, 1);
    const look = C.clone().addScaledVector(up, sh.drop * R);
    cam.lookAt(look); r.controls.target.copy(look);
    r.scene.traverse(o => { if (o.isLine) o.visible = false; });
    const near = Math.max(0.003, Math.min(0.5, (pos.distanceTo(C) - R * (sh.sat ? 2.3 : 1)) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
