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
  // the Earth for scale: hovering just beside the Great Red Spot (the storm is ~16 000 km across, the Earth 12 742),
  // drawn so it looks the size it would be lying at the Spot's own distance from the camera
  const EARTH_AT = [-31, -43, 7.5];                 // below and to the side of the Spot, in the pale zone
  function placeEarth(J, camPos) {
    const e = J.bodies.earth, p = onJ(J, ...EARTH_AT);
    e.position.copy(p);
    e.scale.setScalar(camPos.distanceTo(p) / camPos.distanceTo(onJ(J, GRS[0], GRS[1])));
    // turned so Europe and Africa (longitude 20° E) face the camera
    const d = camPos.clone().sub(p), lonCam = Math.atan2(-d.z, d.x);
    e.rotation.y = lonCam - 20 * J.D;
  }

  const SHOTS = {
    // The Great Red Spot, filling the frame, turning; the camera sinks slowly toward it (time-lapse: days in seconds)
    hook: { dur: 5.433,
      setup(J) { show(J, 'jupiter', 'earth'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.22; u.drift.value = 0.012;
        },
      frame(J, t) {
        const k = smooth(t / this.dur), P = onJ(J, GRS[0] + 1.5, GRS[1]), n = J.dirLL(GRS[0], GRS[1]);
        const pos = onJ(J, GRS[0] - 12, GRS[1] + 1, lerp(80, 64, k));
        placeEarth(J, pos);
        sunAll(J, n.clone().add(V(0.5, 0.6, 0.2)));
        cam(J, pos, P, 40, V(0, 1, 0), 1, 5000);
      } },
    // pulling back to the whole planet; the Earth, to scale, appears below its south pole
    zoom: { dur: 11.133,
      setup(J) { show(J, 'jupiter', 'earth'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.22; u.drift.value = 0.012;
        },
      frame(J, t) {
        const k = ease(t / this.dur), n = J.dirLL(GRS[0], GRS[1]);
        const far = J.dirLL(-6, GRS[1] + 4).multiplyScalar(400);
        const near = onJ(J, GRS[0] - 12, GRS[1] + 1, 64);
        const pos = lerpV(near, far, Math.pow(k, 0.7));
        const look = lerpV(onJ(J, GRS[0] + 1.5, GRS[1]), V(0, -14, 0), smooth((t - 0.8) / (this.dur * 0.7)));
        sunAll(J, n.clone().add(V(0.4, 0.2, 0.6)));
        placeEarth(J, pos);
        if (!J.earthLabel) J.earthLabel = J.sprite(J.LABEL('Земля'));
        // the name just under the Earth, the same few pixels below it however far the camera is
        const el = J.earthLabel, ep = J.bodies.earth.position;
        el.visible = true; el.position.copy(ep).addScaledVector(V(0, -1, 0), 6.4 * J.bodies.earth.scale.x + pos.distanceTo(ep) * 0.035);
        el.scale.set(J.px(220), J.px(41), 1); el.material.opacity = smooth((t - 0.4) / 0.8);
        cam(J, pos, look, 40, V(0, 1, 0), 1, 5000);
      } },
    // a time-lapse of its spin: one turn in six seconds, the bands racing by, the planet visibly squashed
    spin: { dur: 8.800,
      setup(J) { show(J, 'jupiter'); const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.05; u.drift.value = 0.004; },
      frame(J, t) {
        J.bodies.jupiter.rotation.y = -t / 6 * Math.PI * 2 + 0.8;
        sunAll(J, V(0.55, 0.12, 1));
        cam(J, V(0, 6, 300), V(0, 0, 0), 40, V(0, 1, 0), 1, 5000);
      } },
    // the dive: down through the cloud decks into the dark
    dive: { dur: 12.300,
      frame(J, t) { const u = J.dive.u; u.depth.value = lerp(-1.5, 17, Math.pow(t / this.dur, 1.15)); u.time.value = t; return { pass: J.dive }; } },
    // the four big moons in a row in front of the giant, the camera gliding past them (sizes true, spacing shortened)
    moons: { dur: 8.667,
      setup(J) {
        show(J, 'jupiter', 'io', 'europa', 'ganymede', 'callisto');
        J.bodies.jupiter.position.set(6, 2, -300);
        // a diagonal from the bottom left (Io, nearest) to the top right (Callisto), Jupiter filling the back
        J.bodies.io.position.set(-4, -8, -26); J.bodies.europa.position.set(-1, -3, -42);
        J.bodies.ganymede.position.set(3, 3, -60); J.bodies.callisto.position.set(5.5, 9, -84);
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.05; u.drift.value = 0.004;
      },
      frame(J, t) {
        const k = ease(t / this.dur);
        sunAll(J, V(0.9, 0.3, 0.6));
        cam(J, V(lerp(-1.5, 1.5, k), lerp(-0.5, 0.5, k), lerp(3, 0, k)), V(lerp(0.2, 1.2, k), 0, -60), 40, V(0, 1, 0), 0.5, 5000);
      } },
    // toward Io: yellow, orange and red, Jupiter huge behind it
    ioapp: { dur: 4.733,
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.bodies.jupiter.rotation.y = Math.PI;
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.03; u.drift.value = 0.002; },
      frame(J, t) {
        const k = ease(t / this.dur), d = J.dirLL(8, 165);
        sunAll(J, V(-0.35, 0.2, 1));
        cam(J, d.clone().multiplyScalar(lerp(60, 14, k)), V(lerp(30, 8, k), 0, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // Io squeezed by Jupiter's pull: it swells and settles toward the planet (shown many times over)
    iobreath: { dur: 10.833,
      setup(J) { SHOTS.ioapp.setup(J); },
      frame(J, t) {
        const s = 1 + 0.02 * Math.sin(t / this.dur * Math.PI * 4) * smooth(t / 0.8);
        J.bodies.io.scale.set(s, 1 / Math.sqrt(s), 1 / Math.sqrt(s));      // stretched along the line to Jupiter (x)
        sunAll(J, V(-0.35, 0.2, 1));
        const a = lerp(165, 150, ease(t / this.dur)), d = J.dirLL(8, a);
        cam(J, d.clone().multiplyScalar(lerp(14, 11, ease(t / this.dur))), V(lerp(8, 6, ease(t / this.dur)), 0, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // under the yellow haze: low over Io toward Pele — its umbrella plume 300 km high, the red ring of fallout
    pele: { dur: 8.300, vent: [-18.6, 104.8],
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.plume.visible = true;
        J.bodies.io.scale.set(1, 1, 1); J.bodies.io.userData.u.spots.value[0].set(-18.6 * J.D, 104.8 * J.D, 0.6 * J.D, 0.6); },
      frame(J, t) {
        const k = ease(t / this.dur), io = J.bodies.io, R = io.userData.R, [la, lo] = SHOTS.pele.vent;
        const vent = J.dirLL(la, lo), east = V(-Math.sin(lo * J.D), 0, -Math.cos(lo * J.D)), north = V().crossVectors(vent, east).normalize();
        // the camera comes in from the south-west, sinking through the haze
        const back = 0.42, side = -0.12;
        const g = vent.clone().multiplyScalar(Math.cos(back)).addScaledVector(north, -Math.sin(back) * 0.8).addScaledVector(east, Math.sin(side)).normalize();
        const pos = g.multiplyScalar(R + lerp(0.42, 0.13, k));
        const look = vent.clone().multiplyScalar(R + lerp(0.05, 0.16, k));
        io.userData.u.fogK.value = lerp(0.9, 0.05, smooth(t / (this.dur * 0.6)));
        io.updateMatrixWorld(true);
        J.updatePlume(io, la, lo, t, 5.0);
        J.plumeMat.uniforms.gain.value = 1.5;
        sunAll(J, vent.clone().multiplyScalar(0.55).addScaledVector(east, -0.8).addScaledVector(north, 0.3));
        cam(J, pos, look, 55, vent, 0.003, 5000);
      } },
    // Loki at night: the lava lake 200 km across glowing; low to the east of it, looking west — Jupiter (half lit)
    // stands 40° up in the sky beyond (Loki is on the side of Io that always faces Jupiter)
    loki: { dur: 7.167,
      setup(J) { show(J, 'io', 'jupiter'); J.bodies.jupiter.position.set(422, 0, 0); J.bodies.jupiter.rotation.y = Math.PI;
        J.bodies.io.scale.set(1, 1, 1); const u = J.bodies.io.userData.u;
        u.spots.value[0].set(11.3 * J.D, 49.6 * J.D, 3.8 * J.D, 1.0); u.night.value = 0.05; u.fogK.value = 0; },
      frame(J, t) {
        const k = ease(t / this.dur), io = J.bodies.io, R = io.userData.R;
        const c = J.dirLL(11.3, 49.6), east = V(-Math.sin(49.6 * J.D), 0, -Math.cos(49.6 * J.D)), north = V().crossVectors(c, east).normalize();
        const g = c.clone().multiplyScalar(Math.cos(0.16)).addScaledVector(east, Math.sin(0.16)).normalize();
        const pos = g.clone().multiplyScalar(R + lerp(0.16, 0.12, k));
        const jdir = V(422, 0, 0).sub(pos).normalize();
        const look = pos.clone().addScaledVector(c.clone().multiplyScalar(R).sub(pos).normalize(), 1).addScaledVector(jdir, 1.15);
        sunAll(J, V(-0.3, 0.05, 0.95));
        cam(J, pos, look, 72, g, 0.002, 5000);
      } },
    // Europa: low over the ice, flying west over the rusty cracks, a low Sun from the north; Jupiter on the horizon
    europa: { dur: 8.633,
      setup(J) { show(J, 'europa', 'jupiter'); J.bodies.jupiter.position.copy(J.dirLL(4, 168).multiplyScalar(671));
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.03; u.drift.value = 0.002; },
      frame(J, t) {
        const k = ease(t / this.dur), eu = J.bodies.europa, R = eu.userData.R;
        const la = lerp(16, 12, k), lo = lerp(-100, -122, k), up = J.dirLL(la, lo);
        const north = V(-Math.sin(la * J.D) * Math.cos(lo * J.D), Math.cos(la * J.D), Math.sin(la * J.D) * Math.sin(lo * J.D));
        const west = V(Math.sin(lo * J.D), 0, Math.cos(lo * J.D));
        const pos = up.clone().multiplyScalar(R + lerp(0.34, 0.24, k));
        const look = pos.clone().addScaledVector(west, 1).addScaledVector(up, -0.42);
        sunAll(J, up.clone().multiplyScalar(0.4).add(north).add(west.clone().multiplyScalar(-0.3)));
        cam(J, pos, look, 55, up, 0.002, 5000);
      } },
    // the Europa Clipper on its way: the probe crossing in front of the ice moon, Jupiter behind
    clipper: { dur: 7.333,
      setup(J) { show(J, 'europa', 'jupiter'); J.bodies.jupiter.position.copy(J.dirLL(-10, 74).multiplyScalar(671)); J.clipper.visible = true; },
      frame(J, t) {
        const k = t / this.dur;
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
    ganymede: { dur: 8.167,
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
        const k = ease(t / this.dur);
        J.bodies.ganymede.rotation.y = t * 0.05; J.bodies.mercury.rotation.y = t * 0.03;
        sunAll(J, V(0.9, 0.25, 0.5));
        cam(J, V(0, lerp(10, 8, k), lerp(25, 21, k)), V(0, -0.6, 0), 40, V(0, 1, 0), 0.05, 5000);
      } },
    // dawn over Ukraine: Jupiter, the brightest "star", high in the south-east
    dawn: { dur: 8.933,
      frame(J, t) { const u = J.dawn.u; u.k.value = lerp(0.12, 0.42, t / this.dur); u.time.value = t; return { pass: J.dawn }; } },
    // the end, as it really is: seen from the Earth the four moons stand almost on one line through Jupiter (their
    // orbits are edge-on to us), at their true distances. Positions for 30 October 2026, 5:00 in Kyiv (Meeus' method),
    // in Jupiter radii west (+) or east (−) of it, and toward us (+) or away. The view is turned so the line runs
    // corner to corner of the tall frame; the camera pulls back until all four are in.
    outro: { dur: 10.300, pos: { io: [-5.84, -0.97], europa: [-3.29, -8.85], ganymede: [14.84, 2.15], callisto: [8.03, 25.2] },
      setup(J) {
        show(J, 'jupiter', 'io', 'europa', 'ganymede', 'callisto');
        const RJ = 71.492, P = SHOTS.outro.pos;
        // from the Earth (600 million km away) there is no parallax: depth only decides what is in front, so it is
        // kept tiny (a moon nearer than Jupiter just in front of it, a farther one just behind)
        for (const n of Object.keys(P)) J.bodies[n].position.set(-P[n][0] * RJ, 0, Math.sign(P[n][1]) * 2 * RJ);
        const u = J.bodies.jupiter.userData.u; u.grsSpin.value = 0.05; u.drift.value = 0.004;
        if (!J.moonMarks) {
          const GLOW = J.canvas(64, 64, g => { const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
            gr.addColorStop(0, 'rgba(255,250,240,1)'); gr.addColorStop(0.2, 'rgba(255,240,220,0.9)'); gr.addColorStop(0.5, 'rgba(255,230,200,0.2)'); gr.addColorStop(1, 'rgba(255,230,200,0)');
            g.fillStyle = gr; g.fillRect(0, 0, 64, 64); });
          const names = { io: 'Іо', europa: 'Європа', ganymede: 'Ганімед', callisto: 'Каллісто' };
          J.moonMarks = Object.keys(names).map(n => ({ n, glow: J.sprite(GLOW), label: J.sprite(J.LABEL(names[n])) }));
        }
        J.extra = J.moonMarks;
      },
      frame(J, t) {
        const kk = ease(Math.min(1, t / 4.6)), D = lerp(700, 2800, kk), cx = lerp(0, -322, kk);   // centred on the line's middle
        const up = V(Math.sin(60 * J.D), Math.cos(60 * J.D), 0);       // the line of moons (x) runs at 60° on screen
        sunAll(J, V(0.18, 0.05, 1));
        cam(J, V(cx, 0, D), V(cx, 0, 0), 40, up, 1, 20000);
        for (const m of J.moonMarks) {
          const b = J.bodies[m.n].position;
          m.glow.visible = m.label.visible = true;
          m.glow.position.copy(b); m.glow.scale.set(J.px(22), J.px(22), 1);
          m.glow.material.opacity = smooth((D - 900) / 500);
          // the name beside the moon, off the line (world +y shows up and to the left of it)
          m.label.position.copy(b).add(V(0, D * 0.04, 0)); m.label.scale.set(J.px(220), J.px(41), 1);
          m.label.material.opacity = smooth((t - 2.8) / 0.8) * (1 - smooth((t - (this.dur - 4.2)) / 0.6));
        }
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
      if (J.moonMarks) J.moonMarks.forEach(m => { m.glow.visible = m.label.visible = false; });
      const io = J.bodies.io.userData.u; io.spots.value.forEach(v => v.set(0, 0, 0, 0)); io.fogK.value = 0; io.night.value = 0;
      J.bodies.ganymede.userData.u.aur.value = 0; J.bodies.io.scale.set(1, 1, 1); io.exposure.value = 1.25;
      if (st) await st(J); };
  }
  window.SHOTS = SHOTS;
})();
