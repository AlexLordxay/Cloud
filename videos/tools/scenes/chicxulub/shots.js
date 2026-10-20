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

  // the impact site's own frame: the point on the ground, up, east, north
  function site(X) {
    const up = X.dirLL(CHX[0], CHX[1]), lon = CHX[1] * X.D;
    const east = V(-Math.sin(lon), 0, -Math.cos(lon)), north = up.clone().cross(east).normalize();
    return { I: up.clone().multiplyScalar(X.ER), up, east, north };
  }
  const horiz = (S, az) => S.north.clone().multiplyScalar(Math.cos(az * Math.PI / 180)).addScaledVector(S.east, Math.sin(az * Math.PI / 180));
  // the path: in from the north-east (azimuth 45°) at 60° to the ground, 20 km/s (0.02 units/s) — the steep, north-
  // easterly approach the crater's shape points to (Collins et al. 2020). back: the unit vector up the path.
  const AZ = 45, EL = 60, SPEED = 0.02;
  function path(S) {
    const back = horiz(S, AZ).multiplyScalar(Math.cos(EL * Math.PI / 180)).addScaledVector(S.up, Math.sin(EL * Math.PI / 180));
    return { back, at: tau => S.I.clone().addScaledVector(back, SPEED * tau), alt: tau => SPEED * tau * Math.sin(EL * Math.PI / 180) };
  }
  // how brightly the air glows round it at a height (units): from nothing above ~125 km to full below ~70 km
  const glowAt = h => smooth((0.125 - h) / 0.055);

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
    // into the air: the last seconds above Yucatán seen from the side, from ~250 km up to the south-east. It lights up
    // ~120 km high, a white-hot head with a glowing wake that cools to orange and red and leaves smoke behind; the
    // clouds and the sea below take its light. Ends at the moment it reaches the ground.
    entry: { dur: 7.5, tau0: 7.5,
      setup(X) {
        const S = site(X), P = path(S); this.S = S; this.P = P;
        X.asteroid.visible = true; X.asteroid.scale.setScalar(0.006); X.asteroid.rotation.set(0.4, 1.1, 0.3);
        const fwd = P.back.clone().negate();
        // the wake: born along the path where the air glows — a white-hot tube that cools to orange and red over a few
        // seconds and swells, then smoke; pushed a little along the path, spreading and slowing in the air
        const G = this.glowFx = this.glowFx || X.fx(14000, true), K = this.smokeFx = this.smokeFx || X.fx(5000, false);
        const r = X.rnd, rv = () => V(r() - 0.5, r() - 0.5, r() - 0.5);
        for (let i = 0; i < G.n; i++) {
          const b = r() * this.tau0, tau = this.tau0 - b, g = glowAt(P.alt(tau)), big = r() < 0.25;
          const pos = P.at(tau).add(rv().multiplyScalar(big ? 0.008 : 0.003));
          const vel = fwd.clone().multiplyScalar(SPEED * 0.15 * r()).add(rv().multiplyScalar(big ? 0.012 : 0.005));
          G.set(i, pos, vel, g > 0.02 ? b : 1e9, big ? 2 + 5 * r() : 0.6 + 2.5 * r() * r(),
                (big ? 0.005 : 0.002) * g, (big ? 0.016 + 0.016 * r() : 0.005 + 0.008 * r()) * g, r());
        }
        for (let i = 0; i < K.n; i++) {
          const b = r() * this.tau0, tau = this.tau0 - b, g = glowAt(P.alt(tau));
          const pos = P.at(tau).add(rv().multiplyScalar(0.01));
          K.set(i, pos, rv().multiplyScalar(0.006), g > 0.05 ? b + 1.0 + r() * 1.5 : 1e9, 10 + 8 * r(), 0.015 * g, (0.05 + 0.06 * r()) * g, r());
        }
        G.done(); K.done();
        G.u.drag.value = K.u.drag.value = 1.0; G.u.heat.value = 2.6; G.u.gain.value = 0.05;
        K.u.smoke.value.setRGB(0.30, 0.26, 0.23);
        G.points.visible = K.points.visible = true;
        X.head.core.visible = X.head.halo.visible = true;
      },
      frame(X, t) {
        const S = this.S, P = this.P, tau = Math.max(this.tau0 - t, 0), g = glowAt(P.alt(tau));
        const A = P.at(tau); X.asteroid.position.copy(A);
        const ahead = A.clone().addScaledVector(P.back, -0.0035);
        X.head.core.position.copy(ahead); X.head.core.scale.setScalar(0.022 * g + 1e-6);
        X.head.halo.position.copy(ahead); X.head.halo.scale.setScalar(0.10 * g + 1e-6);
        X.U.fball.value.set(ahead.x, ahead.y, ahead.z, 0.9 * g);
        X.AU.heat.value = g; X.AU.fwd.value.copy(P.back).negate();
        // the camera: ~380 km south-east along the ground, ~240 km up, looking at the lower half of the path
        const base = S.I.clone().addScaledVector(horiz(S, 140), 0.38).normalize().multiplyScalar(X.ER + 0.24);
        const look = S.I.clone().addScaledVector(P.back, 0.06);
        cam(X, base.addScaledVector(S.east, 0.006 * t), look, 40, S.up.clone(), 0.002);
        X.U.haze.value = 0.35;
        const pxScale = X.H / (2 * Math.tan(X.camera.fov * X.D / 2));
        for (const F of [this.glowFx, this.smokeFx]) { F.u.time.value = this.tau0 - tau; F.u.scale.value = pxScale; }
        // dusk: the Sun just above the western horizon, so the fireball's own light shows on the clouds and the sea
        X.U.sun.value.copy(S.up.clone().multiplyScalar(0.07).addScaledVector(horiz(S, 265), 1).normalize());
        X.U.cloudLon.value = 0.02;
      } },
  };
  window.SHOTS = SHOTS;
})();
