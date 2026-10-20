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

  const P_back = shot => shot.P.back;

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
        const pxScale = X.H / (2 * Math.tan(X.camera.fov * X.D / 2));
        for (const F of [this.glowFx, this.smokeFx]) { F.u.time.value = this.tau0 - tau; F.u.scale.value = pxScale; }
        // dusk: the Sun just gone down in the west — the ground in twilight, the air high up still lit — so the
        // fireball's own light shows on the clouds and the sea
        X.U.sun.value.copy(S.up.clone().multiplyScalar(-0.05).addScaledVector(horiz(S, 265), 1).normalize());
        X.U.cloudLon.value = 0.02;
      } },
    // the impact, its first two minutes squeezed into ten seconds (real time T = 120·(t/10)^1.8 s): the flash; the
    // fireball of rock and sea turned to vapour, rising past the top of the air, thrown a little downrange (south-west);
    // the curtain of ejecta, an inverted cone of rock opening outward from the growing crater on ballistic arcs; the
    // blast running out over the sea and the clouds (Sedov: ~340 km in two minutes for ~4·10²³ J), sweeping them away
    // and leaving a pall of dust; the young crater's floor glowing. The camera starts where the entry ended and draws
    // back and up to show the size of it all.
    impact: { dur: 10,
      T(t) { return 120 * Math.pow(Math.max(t, 0) / this.dur, 1.8); },
      setup(X) {
        SHOTS.entry.setup.call(SHOTS.entry, X);                        // the trail and its smoke still hang there
        const S = site(X), P = path(S); this.S = S; this.P = P;
        X.asteroid.visible = false;
        const r = X.rnd, rv = () => V(r() - 0.5, r() - 0.5, r() - 0.5), dr = horiz(S, AZ + 180);
        // a direction and speed for the vapour: any way up, fastest straight up and a little downrange (the cloud grows as
        // a rounded, leaning dome, then a mushroom), with a random share of that speed so it fills its volume
        const pvel = () => {
          let d = rv().normalize(); if (d.dot(S.up) < 0) d.addScaledVector(S.up, -2 * d.dot(S.up));
          d.addScaledVector(dr, 0.2).normalize();
          const c = Math.max(d.dot(S.up), 0), sp = 0.012 * (0.3 + 0.7 * Math.pow(c, 1.6)) * (0.35 + 0.65 * Math.pow(r(), 0.5));
          return d.multiplyScalar(sp).add(rv().multiplyScalar(0.0015));
        };
        // the fireball: vapour flung up and out at 3–13 km/s, slowed by the air (drag 0.02/s)
        const PG = this.pg = this.pg || X.fx(10000, true), PS = this.ps = this.ps || X.fx(6000, false), DRAG = 0.02;
        for (let i = 0; i < PG.n; i++) {
          const v = pvel();
          PG.set(i, S.I.clone().addScaledVector(S.up, 0.002).add(rv().multiplyScalar(0.004)), v, 0.3 * r(), 40 + 80 * r(), 0.006, 0.05 + 0.09 * r(), r());
        }
        // its smoke: born later where the vapour has got to by then, carrying on with what speed it has left; and the
        // top of the cloud, past the thin upper air, spreading sideways into a cap (the plume spreads out above the
        // atmosphere): a mushroom
        const hz = () => { const a = r() * Math.PI * 2; return S.east.clone().multiplyScalar(Math.cos(a)).addScaledVector(S.north, Math.sin(a)); };
        for (let i = 0; i < PS.n; i++) {
          if (i % 5 < 2) {
            // born only once the rising vapour has got that high (its top: 0.6·(1 − e^(−0.02 T)) units)
            const hgt = 0.2 + 0.14 * r(), h = hz(), b = -Math.log(1 - hgt / 0.6) / DRAG + 12 * r();
            const p = S.I.clone().addScaledVector(S.up, hgt).addScaledVector(h, 0.06 * r()).addScaledVector(dr, 0.04);
            PS.set(i, p, h.multiplyScalar(0.003 + 0.005 * r()).addScaledVector(S.up, 0.0008 * r()), b, 150 + 100 * r(), 0.05, 0.12 + 0.08 * r(), r());
          } else {
            const v = pvel(), b = 6 + 50 * r();
            const p = S.I.clone().addScaledVector(v, (1 - Math.exp(-DRAG * b)) / DRAG);
            PS.set(i, p, v.multiplyScalar(Math.exp(-DRAG * b)), b, 150 + 100 * r(), 0.04, 0.10 + 0.08 * r(), r());
          }
        }
        PG.u.drag.value = PS.u.drag.value = DRAG; PG.u.heat.value = 2.0; PG.u.gain.value = 0.032;
        PS.u.shade.value = 1; PS.u.ldir.value.set(-0.75, 0.35);
        PS.u.smoke.value.setRGB(0.46, 0.40, 0.34); PS.u.gain.value = 0.8;
        // the curtain: rock thrown out at 45° from the crater's growing rim, slower the later and further out it
        // leaves (2.5 → 0.6 km/s), on ballistic arcs; hot at first, then dark dust
        const CG = this.cg = this.cg || X.fx(5000, true), CS = this.cs = this.cs || X.fx(12000, false);
        const launch = (F, i, life, s0, s1) => {
          const b = 60 * Math.pow(r(), 1.5), f = Math.sqrt(b / 60), phi = r() * Math.PI * 2;
          const h = S.east.clone().multiplyScalar(Math.cos(phi)).addScaledVector(S.north, Math.sin(phi));
          const v = 0.0025 * (1 - 0.75 * f), pos = S.I.clone().addScaledVector(h, 0.05 * f).addScaledVector(S.up, 0.001);
          F.set(i, pos, h.multiplyScalar(v * 0.707).addScaledVector(S.up, v * 0.707), b, life, s0, s1, r());
        };
        for (let i = 0; i < CG.n; i++) launch(CG, i, 15 + 20 * r(), 0.003, 0.01);
        for (let i = 0; i < CS.n; i++) launch(CS, i, 300, 0.006, 0.022 + 0.016 * r());
        CG.u.drag.value = CS.u.drag.value = 0.0005; CG.u.heat.value = 3.0; CG.u.gain.value = 0.06;
        CG.u.grav.value.copy(S.up).multiplyScalar(-9.8e-6); CS.u.grav.value.copy(S.up).multiplyScalar(-9.8e-6);
        CS.u.smoke.value.setRGB(0.26, 0.21, 0.17); CS.u.gain.value = 0.3;
        // above ~60 km the smoke and dust still catch the Sun, set on the ground below
        for (const F of [PS, CS]) F.u.litH.value.set(0.04, 0.12);
        // the blast dome, its foot on the ground ring: tilted so its pole is the site's up
        X.dome.visible = true; X.dome.position.copy(S.I); X.dome.quaternion.setFromUnitVectors(V(0, 1, 0), S.up);
        for (const F of [PG, PS, CG, CS]) F.points.visible = true;
        X.head.core.visible = X.head.halo.visible = true;
      },
      frame(X, t) {
        const T = this.T(t), S = this.S, E = SHOTS.entry;
        // the flash: blinding at contact, gone in seconds; the fireball's own light lingers
        const fl = Math.exp(-T / 1.5), glowPt = S.I.clone().addScaledVector(S.up, 0.01);
        X.head.core.position.copy(glowPt); X.head.core.scale.setScalar(0.05 + 0.5 * fl);
        X.head.halo.position.copy(glowPt); X.head.halo.scale.setScalar(0.25 + 2.2 * fl);
        X.U.fball.value.set(glowPt.x, glowPt.y + 0.0, glowPt.z, 2.5 * fl + 0.6 * Math.exp(-T / 40));
        // the blast ring, the swept and dusty ground inside it, the crater (transient, ~100 km across) glowing
        const RB = 0.34 * Math.pow(Math.max(T, 0.01) / 120, 0.4);
        X.U.shock.value.set(S.up.x, S.up.y, S.up.z, RB / X.ER);
        X.dome.scale.set(RB, RB * 0.55, RB); X.dome.material.uniforms.k.value = 0.7 * Math.exp(-T / 45) + 0.1;
        X.U.shock2.value.set(0.04 + 0.15 * Math.exp(-T / 40), 0.05 * Math.sqrt(Math.min(T / 90, 1)) / X.ER, 1.8, 0.85 * smooth(T / 20));
        // the camera: from where the entry ended, back to ~1700 km and up to ~850 km
        const k = smooth((t - 0.6) / 9.4);
        const base = S.I.clone().addScaledVector(horiz(S, 140), lerp(0.38, 1.7, k)).normalize().multiplyScalar(X.ER + lerp(0.24, 0.85, k));
        cam(X, base.addScaledVector(S.east, 0.006 * (E.dur + t)), S.I.clone().addScaledVector(P_back(this), lerp(0.06, 0.0, k)).addScaledVector(S.up, lerp(0, 0.3, k)),
            lerp(40, 48, k), S.up.clone(), 0.002);
        const pxScale = X.H / (2 * Math.tan(X.camera.fov * X.D / 2));
        for (const F of [E.glowFx, E.smokeFx]) { F.u.time.value = E.tau0 + T; F.u.scale.value = pxScale; }
        for (const F of [this.pg, this.ps, this.cg, this.cs]) { F.u.time.value = T; F.u.scale.value = pxScale; }
        X.U.sun.value.copy(S.up.clone().multiplyScalar(-0.05).addScaledVector(horiz(S, 265), 1).normalize());
        X.U.cloudLon.value = 0.02;
      } },
    // checks of the detailed region by day: straight down on the site from ~700 km, and low and oblique over the coast
    site_top: { dur: 2,
      frame(X, t) {
        const S = site(X);
        cam(X, S.up.clone().multiplyScalar(X.ER + 0.7), S.I, 60, S.north.clone(), 0.01);
        X.U.sun.value.copy(S.up.clone().multiplyScalar(0.8).addScaledVector(horiz(S, 250), 0.6).normalize());
      } },
    site_low: { dur: 2,
      frame(X, t) {
        const S = site(X);
        const pos = S.I.clone().addScaledVector(horiz(S, 200), 0.45).normalize().multiplyScalar(X.ER + 0.12);
        cam(X, pos, S.I.clone().addScaledVector(horiz(S, 200), 0.1), 50, S.up.clone(), 0.002);
        X.U.sun.value.copy(S.up.clone().multiplyScalar(0.6).addScaledVector(horiz(S, 250), 0.8).normalize());
      } },
  };
  window.SHOTS = SHOTS;
})();
