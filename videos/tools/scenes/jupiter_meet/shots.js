// Shots of "Знайомся: Юпітер" (world.js builds the bodies; render.js renders one shot at a time). Each shot: dur
// (seconds), setup(J) to show what it needs, frame(J, t) to place the camera and light. Units: 1 = 1000 km.
// Lengths are first guesses; they are set to the voice afterwards.
(() => {
  const ease = x => { x = Math.min(1, Math.max(0, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  const smooth = x => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };
  const lerp = (a, b, k) => a + (b - a) * k;
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const lerpV = (a, b, k) => a.clone().lerp(b, k);

  function sunAll(J, v) { const s = v.clone().normalize(); for (const b of Object.values(J.bodies)) b.userData.u.sun.value.copy(s); }
  function show(J, ...names) { for (const n of names) J.bodies[n].visible = true; }
  function cam(J, pos, look, fov = 40, up = V(0, 1, 0), near = 0.05, far = 50000) {
    const c = J.camera; c.fov = fov; c.near = near; c.far = far;
    c.position.copy(pos); c.up.copy(up); c.lookAt(look);
  }
  // a point at (lat, lon) on Jupiter's flattened cloud tops, and the outward normal there
  const JR = 71.492, JF = 66.854 / 71.492;
  const onJ = (J, lat, lon, h = 0) => { const d = J.dirLL(lat, lon); return V(d.x * (JR + h), d.y * (JR * JF + h), d.z * (JR + h)); };
  const GRS = [-20.5, -46.9];

  const SHOTS = {
    // The Great Red Spot, filling the frame, turning; the camera sinks slowly toward it (time-lapse: days in seconds)
    hook: { dur: 4.6,
      setup(J) { show(J, 'jupiter'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.22; u.drift.value = 0.012; },
      frame(J, t) {
        const k = smooth(t / 4.6), P = onJ(J, GRS[0] + 1.5, GRS[1]), n = J.dirLL(GRS[0], GRS[1]);
        const pos = onJ(J, GRS[0] - 12, GRS[1] + 1, lerp(80, 64, k));
        sunAll(J, n.clone().add(V(0.5, 0.6, 0.2)));
        cam(J, pos, P, 40, V(0, 1, 0), 1, 5000);
      } },
    // pulling back to the whole planet; the Earth, to scale, appears below its south pole
    zoom: { dur: 8.6,
      setup(J) { show(J, 'jupiter', 'earth'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.22; u.drift.value = 0.012;
        J.bodies.earth.position.set(0, -(66.854 + 26), 0); J.bodies.earth.rotation.y = 2.4; },
      frame(J, t) {
        const k = ease(t / 8.6), n = J.dirLL(GRS[0], GRS[1]);
        const far = J.dirLL(-6, GRS[1] + 4).multiplyScalar(400);
        const near = onJ(J, GRS[0] - 12, GRS[1] + 1, 64);
        const pos = lerpV(near, far, Math.pow(k, 0.7));
        const look = lerpV(onJ(J, GRS[0] + 1.5, GRS[1]), V(0, -14, 0), smooth((t - 0.8) / 6));
        sunAll(J, n.clone().add(V(0.4, 0.2, 0.6)));
        if (!J.earthLabel) J.earthLabel = J.sprite(J.LABEL('Земля'));
        const el = J.earthLabel; el.visible = true; el.position.set(0, -(66.854 + 26) - 13, 0);
        el.scale.set(J.px(220), J.px(41), 1); el.material.opacity = smooth((t - 4.5) / 1.2);
        cam(J, pos, look, 40, V(0, 1, 0), 1, 5000);
      } },
    // a time-lapse of its spin: one turn in six seconds, the bands racing by, the planet visibly squashed
    spin: { dur: 5.2,
      setup(J) { show(J, 'jupiter'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.05; u.drift.value = 0.004; },
      frame(J, t) {
        J.bodies.jupiter.rotation.y = -t / 6 * Math.PI * 2 + 0.8;
        sunAll(J, V(0.55, 0.12, 1));
        cam(J, V(0, 6, 300), V(0, 0, 0), 40, V(0, 1, 0), 1, 5000);
      } },
    // the dive: down through the cloud decks into the dark
    dive: { dur: 8.6,
      frame(J, t) { const u = J.dive.u; u.depth.value = lerp(-1.5, 17, Math.pow(t / 8.6, 1.15)); u.time.value = t; return { pass: J.dive }; } },
    // the four big moons in a row in front of the giant, the camera gliding past them (sizes true, spacing shortened)
    moons: { dur: 5.6,
      setup(J) {
        show(J, 'jupiter', 'io', 'europa', 'ganymede', 'callisto');
        J.bodies.jupiter.position.set(6, 2, -300);
        // a diagonal from the bottom left (Io, nearest) to the top right (Callisto), Jupiter filling the back
        J.bodies.io.position.set(-4, -8, -26); J.bodies.europa.position.set(-1, -3, -42);
        J.bodies.ganymede.position.set(3, 3, -60); J.bodies.callisto.position.set(5.5, 9, -84);
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.05; u.drift.value = 0.004;
      },
      frame(J, t) {
        const k = ease(t / 5.6);
        sunAll(J, V(0.9, 0.3, 0.6));
        cam(J, V(lerp(-1.5, 1.5, k), lerp(-0.5, 0.5, k), lerp(3, 0, k)), V(lerp(0.2, 1.2, k), 0, -60), 40, V(0, 1, 0), 0.5, 5000);
      } },
    // toward Io: yellow, orange and red, Jupiter huge behind it
    ioapp: { dur: 3.6,
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.bodies.jupiter.rotation.y = Math.PI;
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.03; u.drift.value = 0.002; },
      frame(J, t) {
        const k = ease(t / 3.6), d = J.dirLL(8, 165);
        sunAll(J, V(-0.35, 0.2, 1));
        cam(J, d.clone().multiplyScalar(lerp(60, 14, k)), V(lerp(30, 8, k), 0, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // Io squeezed by Jupiter's pull: it swells and settles toward the planet (shown many times over)
    iobreath: { dur: 7.6,
      setup(J) { SHOTS.ioapp.setup(J); },
      frame(J, t) {
        const s = 1 + 0.02 * Math.sin(t / 7.6 * Math.PI * 4) * smooth(t / 0.8);
        J.bodies.io.scale.set(s, 1 / Math.sqrt(s), 1 / Math.sqrt(s));      // stretched along the line to Jupiter (x)
        sunAll(J, V(-0.35, 0.2, 1));
        const a = lerp(165, 150, ease(t / 7.6)), d = J.dirLL(8, a);
        cam(J, d.clone().multiplyScalar(lerp(14, 11, ease(t / 7.6))), V(lerp(8, 6, ease(t / 7.6)), 0, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // under the yellow haze: low over Io toward Pele — its umbrella plume 300 km high, the red ring of fallout
    pele: { dur: 6.6, vent: [-18.6, 104.8],
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.plume.visible = true;
        J.bodies.io.scale.set(1, 1, 1); J.bodies.io.userData.u.spots.value[0].set(-18.6 * J.D, 104.8 * J.D, 0.6 * J.D, 0.6); },
      frame(J, t) {
        const k = ease(t / 6.6), io = J.bodies.io, R = io.userData.R, [la, lo] = SHOTS.pele.vent;
        const vent = J.dirLL(la, lo), east = V(-Math.sin(lo * J.D), 0, -Math.cos(lo * J.D)), north = V().crossVectors(vent, east).normalize();
        // the camera comes in from the south-west, sinking through the haze
        const back = 0.42, side = -0.12;
        const g = vent.clone().multiplyScalar(Math.cos(back)).addScaledVector(north, -Math.sin(back) * 0.8).addScaledVector(east, Math.sin(side)).normalize();
        const pos = g.multiplyScalar(R + lerp(0.42, 0.13, k));
        const look = vent.clone().multiplyScalar(R + lerp(0.05, 0.16, k));
        io.userData.u.fogK.value = lerp(0.9, 0.05, smooth(t / 4.0));
        io.updateMatrixWorld(true);
        J.updatePlume(io, la, lo, t, 5.0);
        J.plumeMat.uniforms.gain.value = 1.5;
        sunAll(J, vent.clone().multiplyScalar(0.55).addScaledVector(east, -0.8).addScaledVector(north, 0.3));
        cam(J, pos, look, 55, vent, 0.003, 5000);
      } },
    // Loki at night: the lava lake 200 km across glowing; low to the east of it, looking west — Jupiter (half lit)
    // stands 40° up in the sky beyond (Loki is on the side of Io that always faces Jupiter)
    loki: { dur: 5.6,
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.bodies.jupiter.rotation.y = Math.PI;
        J.bodies.io.scale.set(1, 1, 1); const u = J.bodies.io.userData.u;
        u.spots.value[0].set(11.3 * J.D, 49.6 * J.D, 3.8 * J.D, 1.0); u.night.value = 0.05; u.fogK.value = 0; },
      frame(J, t) {
        const k = ease(t / 5.6), io = J.bodies.io, R = io.userData.R;
        const c = J.dirLL(11.3, 49.6), east = V(-Math.sin(49.6 * J.D), 0, -Math.cos(49.6 * J.D)), north = V().crossVectors(c, east).normalize();
        const g = c.clone().multiplyScalar(Math.cos(0.16)).addScaledVector(east, Math.sin(0.16)).normalize();
        const pos = g.clone().multiplyScalar(R + lerp(0.16, 0.12, k));
        const jdir = V(422, 0, 0).sub(pos).normalize();
        const look = pos.clone().addScaledVector(c.clone().multiplyScalar(R).sub(pos).normalize(), 1).addScaledVector(jdir, 1.15);
        sunAll(J, V(-0.3, 0.05, 0.95));
        cam(J, pos, look, 72, g, 0.002, 5000);
      } },
    // Europa: low over the ice, flying west over the rusty cracks, a low Sun from the north; Jupiter on the horizon
    europa: { dur: 6.6,
      setup(J) { show(J, 'europa', 'jupiter'); J.bodies.jupiter.position.copy(J.dirLL(4, 168).multiplyScalar(671));
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.03; u.drift.value = 0.002; },
      frame(J, t) {
        const k = ease(t / 6.6), eu = J.bodies.europa, R = eu.userData.R;
        const la = lerp(16, 12, k), lo = lerp(-100, -122, k), up = J.dirLL(la, lo);
        const north = V(-Math.sin(la * J.D) * Math.cos(lo * J.D), Math.cos(la * J.D), Math.sin(la * J.D) * Math.sin(lo * J.D));
        const west = V(Math.sin(lo * J.D), 0, Math.cos(lo * J.D));
        const pos = up.clone().multiplyScalar(R + lerp(0.34, 0.24, k));
        const look = pos.clone().addScaledVector(west, 1).addScaledVector(up, -0.42);
        sunAll(J, up.clone().multiplyScalar(0.4).add(north).add(west.clone().multiplyScalar(-0.3)));
        cam(J, pos, look, 55, up, 0.002, 5000);
      } },
    // the Europa Clipper on its way: the probe crossing in front of the ice moon, Jupiter behind
    clipper: { dur: 5.2,
      setup(J) { show(J, 'europa', 'jupiter'); J.bodies.jupiter.position.copy(J.dirLL(-10, 74).multiplyScalar(671)); J.clipper.visible = true; },
      frame(J, t) {
        const k = t / 5.2;
        const cd = J.dirLL(5, -120), side = V().crossVectors(cd, V(0, 1, 0)).normalize().negate();
        sunAll(J, cd.clone().add(side.clone().multiplyScalar(1.3)).add(V(0, 0.3, 0)));
        const pos = cd.clone().multiplyScalar(lerp(9, 7.5, ease(k)));
        cam(J, pos, V(0, -0.6, 0), 40, V(0, 1, 0), 0.05, 5000);
        // the probe: in front of the camera, sliding up and in, a little smaller as it goes
        const c = J.camera; c.updateMatrixWorld(true);
        const fwd = V(0, 0, -1).applyQuaternion(c.quaternion), right = V(1, 0, 0).applyQuaternion(c.quaternion), up = V(0, 1, 0).applyQuaternion(c.quaternion);
        J.clipper.position.copy(c.position).addScaledVector(fwd, 2).addScaledVector(right, lerp(-0.55, 0.12, k)).addScaledVector(up, lerp(-0.55, 0.05, k));
        const sz = lerp(260, 150, k);
        J.clipper.scale.set(J.px(sz), J.px(sz * 200 / 512), 1);
        J.clipper.material.rotation = lerp(0.35, 0.15, k);
      } },
    // Ganymede beside Mercury, to scale — the moon is the bigger one — with its auroral ovals glowing
    ganymede: { dur: 6.6,
      async setup(J) {
        show(J, 'ganymede', 'mercury');
        J.bodies.ganymede.position.set(-3.2, 0, 0); J.bodies.mercury.position.set(3.2, -0.2, 0);
        const u = J.bodies.ganymede.userData.u; u.aur.value = 1.2; u.aurLat.value = 45 * J.D;
        if (!J.labels) {
          J.labels = [J.sprite(J.LABEL('Ганімед')), J.sprite(J.LABEL('Меркурій'))];
        }
        J.labels.forEach(l => { l.visible = true; l.scale.set(J.px(300), J.px(56), 1); });
        J.labels[0].position.set(-3.2, -3.6, 0); J.labels[1].position.set(3.2, -3.6, 0);
        J.extra = J.labels;
      },
      frame(J, t) {
        const k = ease(t / 6.6);
        J.bodies.ganymede.rotation.y = t * 0.05; J.bodies.mercury.rotation.y = t * 0.03;
        sunAll(J, V(0.9, 0.25, 0.5));
        cam(J, V(0, lerp(10, 8, k), lerp(25, 21, k)), V(0, -0.6, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // dawn over Ukraine: Jupiter, the brightest "star", high in the south-east
    dawn: { dur: 8.2,
      frame(J, t) { const u = J.dawn.u; u.k.value = lerp(0.12, 0.42, t / 8.2); u.time.value = t; return { pass: J.dawn }; } },
    // the end: Jupiter and its moons drawing away
    outro: { dur: 8.6,
      setup(J) { SHOTS.moons.setup(J); },
      frame(J, t) {
        const k = ease(t / 8.6);
        sunAll(J, V(-0.2, 0.15, 1));
        cam(J, V(lerp(4, 30, k), lerp(1, 20, k), lerp(0, 160, k)), V(2, -2, lerp(-80, -300, k)), 40, V(0, 1, 0), 0.5, 5000);
      } },
  };
  // one clock for the whole video (as timeline.py lays the shots: each overlaps the next by XF frames), so the turning
  // Spot, the drifting bands and the spin carry on across the cuts instead of starting over
  const ORDER = ['hook', 'zoom', 'spin', 'dive', 'moons', 'ioapp', 'iobreath', 'pele', 'loki', 'europa', 'clipper', 'ganymede', 'dawn', 'outro'];
  let at = 0;
  for (const n of ORDER) { SHOTS[n].t0 = at; at += Math.round(SHOTS[n].dur * 30) / 30 - 18 / 30; }
  // hide the labels in every shot but Ganymede's
  for (const [n, s] of Object.entries(SHOTS)) {
    const st = s.setup;
    s.setup = async J => { if (J.labels) J.labels.forEach(l => (l.visible = false)); if (J.earthLabel) J.earthLabel.visible = false;
      const io = J.bodies.io.userData.u; io.spots.value.forEach(v => v.set(0, 0, 0, 0)); io.fogK.value = 0; io.night.value = 0;
      J.bodies.ganymede.userData.u.aur.value = 0; J.bodies.io.scale.set(1, 1, 1); io.exposure.value = 1.25;
      if (st) await st(J); };
  }
  window.SHOTS = SHOTS;
})();
