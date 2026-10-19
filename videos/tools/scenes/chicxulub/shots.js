// Shots of "Що сталося з Землею, коли вимерли динозаври" (world.js builds the world; render.js renders one shot at a
// time). Each shot: dur (seconds), setup(X) to show what it needs, frame(X, t) to place the camera and the Sun.
// Units: 1 = 1000 km. For now only the look of the Earth and the asteroid; the impact comes later.
(() => {
  const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const lerp = (a, b, k) => a + (b - a) * k;
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const CHX = [24.95, -71.9];                         // the impact site on the map of 66 million years ago (maps.py)

  function cam(X, pos, look, fov = 30, up = V(0, 1, 0), near = 0.01) {
    const c = X.camera; c.fov = fov; c.near = near; c.far = 3000; c.updateProjectionMatrix();
    c.position.copy(pos); c.up.copy(up); c.lookAt(look);
  }
  // the Sun: from the camera's direction to the Earth, turned az degrees round the axis and raised el degrees
  function sunFrom(X, dir, az, el) {
    const s = dir.clone().normalize().applyAxisAngle(V(0, 1, 0), az * X.D);
    const side = V(0, 1, 0).cross(s).normalize();
    X.U.sun.value.copy(s.applyAxisAngle(side, -el * X.D).normalize());
  }

  const SHOTS = {
    // the whole Earth, gibbous, the Americas and the young Atlantic toward us, slowly turning
    earth_full: { dur: 6,
      frame(X, t) {
        const p = X.dirLL(20, -52 + t * 1.2).multiplyScalar(46);
        cam(X, p, V(0, 0, 0), 30);
        sunFrom(X, p, -62, 8); X.U.cloudLon.value = t * 0.004;
      } },
    // above the Gulf: the shallow turquoise platform where it will strike, the horizon curving away
    earth_gulf: { dur: 6,
      frame(X, t) {
        const p = X.dirLL(8, -64).multiplyScalar(X.ER + 2.6), look = X.dirLL(CHX[0] + 3, CHX[1] - 2).multiplyScalar(X.ER);
        cam(X, p, look, 42, p.clone().normalize());
        sunFrom(X, X.dirLL(10, -95), 0, 0); X.U.cloudLon.value = 0.02;
      } },
    // the asteroid alone, close, the Sun from the side so the craters throw shadows
    asteroid: { dur: 6,
      setup(X) { X.earth.visible = X.halo.visible = false; X.asteroid.visible = true; X.asteroid.scale.setScalar(0.006); X.asteroid.position.set(0, 0, 0); },
      frame(X, t) {
        X.asteroid.position.set(200, 0, 0); X.asteroid.rotation.set(0.3, t * 0.25, 0.2);
        cam(X, V(200, 0.004, 0.032), X.asteroid.position, 32, V(0, 1, 0), 0.001);
        X.U.sun.value.set(-1, 0.3, -0.15).normalize();
      } },
    // the asteroid in front, the Earth beyond it, the Gulf in sunlight
    asteroid_earth: { dur: 6,
      setup(X) { X.asteroid.visible = true; X.asteroid.scale.setScalar(0.006); },
      frame(X, t) {
        const A = X.dirLL(CHX[0] + 6, CHX[1] + 18).multiplyScalar(X.ER + 30);
        X.asteroid.position.copy(A); X.asteroid.rotation.set(0.3, t * 0.25, 0.2);
        const toE = A.clone().negate().normalize(), side = V(0, 1, 0).cross(toE).normalize();
        const pos = A.clone().addScaledVector(toE, -0.045).addScaledVector(side, -0.003).add(V(0, 0.009, 0));
        cam(X, pos, A.clone().addScaledVector(toE, 30), 34, V(0, 1, 0), 0.001);
        sunFrom(X, A, -70, 10); X.U.cloudLon.value = 0.02;
      } },
  };
  window.SHOTS = SHOTS;
})();
