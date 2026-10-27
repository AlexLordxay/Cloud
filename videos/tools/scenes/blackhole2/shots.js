// Shots of «Що буде, якщо впасти в чорну діру?» v2 — the camera, the astronaut and the effects as functions of time
// (seconds of the video), in the hole's frame (r_s = 1). Kept apart from cam.js so a still can be re-shot without
// rebuilding the galaxy and the sky (see the dev harness note in cam.js). Times by voice line: see script.md.
window.__bhShots = (H) => {
  const { smooth, lerp, D, clamp, lerpLog, sm, ease, RS_LY } = H;
  const V = (x, y, z) => new (window.__rec.THREE.Vector3)(x, y, z);
  const sph = (el, az) => V(Math.sin(az * D) * Math.cos(el * D), Math.sin(el * D), Math.cos(az * D) * Math.cos(el * D));
  function slerpV(a, b, k) {
    const d = clamp(a.dot(b), -1, 1), w = Math.acos(d);
    if (w < 1e-5) return a.clone();
    const s = Math.sin(w); return a.clone().multiplyScalar(Math.sin((1 - k) * w) / s).addScaledVector(b, Math.sin(k * w) / s);
  }
  const Qh = () => new (window.__rec.THREE.Quaternion)().setFromAxisAngle(V(1, 0, 0), 70 * D);   // hole frame -> galaxy frame
  // The disc stands nearly across the galactic plane, its axis close to the direction of the Sun — so from Earth (and in
  // the 2022 photo) we look at it almost face on.
  const FAR = 1.1e5 / RS_LY;                                    // the whole galaxy: 110 000 ly

  // 0–6.2: the visor close up, the pull-back; he turns round to the hole
  function s1(t) {
    const A = V(0, 1.0, 24), s = 0.32, head = A.clone().add(V(0, 0.8 * s, 0));
    const k = ease((t - 1.2) / 4.8);
    const dist = lerpLog(1.45 * s, 11, k) * (1 - 0.03 * Math.min(t, 1.2));
    const off = V(lerp(0.32, 0.32, k), lerp(0.06, 0.22, k), 1).normalize();
    const pos = head.clone().lerp(A, k).addScaledVector(off, dist);
    const look = head.clone().add(V(0.05 * s, 0.32 * s, 0)).lerp(V(0, 0.65, 15.6), ease((t - 1.6) / 4.4));
    const turn = Math.PI * ease((t - 3.4) / 2.6);
    return { cam: { pos, look, up: V(0, 1, 0), fov: 40 }, exposure: 1.3,
      astro: { pos: A, fwd: V(Math.sin(turn), 0, Math.cos(turn)), up: V(0, 1, 0), s, env: 'front', warm: V(0.35, 0.3, 1) } };
  }
  // 6.2–16.4: out to the whole Milky Way ("the heart of our galaxy"), back in; Mercury's orbit for scale
  function s2(t) {
    const e = s1(6.2), u1 = e.cam.pos.clone().normalize(), d1 = e.cam.pos.length(), qi = Qh().invert();
    const gd = V(0, Math.sin(55 * D), Math.cos(55 * D)).applyQuaternion(qi), gu = V(0, 1, 0).applyQuaternion(qi), dM = sph(30, 25);
    let dist, dir, up = V(0, 1, 0), look = V(0, 0, 0);
    if (t < 9.4) {
      // a slow start (he stays in view, shrinking), then faster and faster out to the whole galaxy
      const u = clamp((t - 6.2) / 3.2, 0, 1), f = Math.pow((1 - Math.cos(Math.PI * u)) / 2, 3);
      dist = lerpLog(d1, FAR, f);
      dir = slerpV(u1, gd, smooth((t - 7.0) / 2.2)); up = slerpV(V(0, 1, 0), gu, smooth((t - 7.0) / 2.2));
      look = e.cam.look.clone().lerp(V(0, 0, 0), smooth((t - 6.2) / 1.2));
    } else if (t < 10.2) {
      dist = lerpLog(FAR, FAR * 0.9, (t - 9.4) / 0.8); dir = gd; up = gu;
    } else if (t < 12.7) {
      const k = (t - 10.2) / 2.5;
      dist = lerpLog(FAR * 0.9, 32, ease(k)); dir = slerpV(gd, dM, smooth(k * 1.15)); up = slerpV(gu, V(0, 1, 0), smooth(k * 1.15));
    } else {
      const k = (t - 12.7) / 3.7; dist = lerp(32, 28, k); dir = sph(lerp(30, 34, k), lerp(25, 40, k));
    }
    // the astronaut stays where he was, fading only once he is small
    const astro = t < 8.2 ? Object.assign({}, e.astro, { op: 1 - sm(7.3, 8.1, t) }) : null;
    return { cam: { pos: dir.multiplyScalar(dist), look, up, fov: 45 }, astro, merc: sm(12.6, 13.4, t) * (1 - sm(16.0, 16.6, t)), you: sm(8.6, 9.1, t) * (1 - sm(9.9, 10.4, t)) };
  }
  // 16.4–20.6: from above, as we see it from Earth; the 2022 photo
  function s3(t) {
    const k = (t - 16.4) / 4.5;
    const dir = sph(lerp(34, 74, smooth((t - 16.4) / 3.2)), lerp(40, 70, k));
    return { cam: { pos: dir.multiplyScalar(lerp(28, 25, k)), look: V(0, 0, 0), up: V(0, 1, 0), fov: 45 } };
  }
  // 21.8–42: the event horizon. He hangs in the plane across the view through the hole and sinks towards it; his lamp
  // flashes, the light that gets away shrinks to a sliver, then nothing. The camera closes in on him.
  const C4 = () => sph(7, -15);
  const r4 = t => Math.max(1.004, 1 + 12 * Math.pow(1 - clamp((t - 21.6) / 12.6, 0, 1), 1.6));   // the lamp's distance (also in captions.py)
  function plane4() { const e3 = C4(), e1 = V(0, 1, 0).cross(e3).normalize(), e2 = e3.clone().cross(e1); return { e1, e2, e3 }; }
  const th4 = t => lerp(62, 40, sm(21.6, 35, t)) * D;
  const lamp4 = t => { const { e1, e2 } = plane4(), r = r4(t); return e1.multiplyScalar(r * Math.cos(th4(t))).addScaledVector(e2, r * Math.sin(th4(t))); };
  const BURSTS = [22.0, 24.2, 26.4, 28.6, 30.4, 31.9, 33.1, 34.4, 35.7];
  function s4(t) {
    const { e3 } = plane4(), L = lamp4(t), rad = L.clone().normalize();
    const look = V(0, 0.4, 0).lerp(L.clone().multiplyScalar(0.62), sm(27, 36, t));
    const d = lerpLog(27, 7.5, ease((t - 26.5) / 9.5));
    return { cam: { pos: look.clone().addScaledVector(e3, d), look, up: V(0, 1, 0), fov: 45 }, discK: 0.5,
      astro: { lamp: L, fwd: e3, up: rad, s: 0.3, env: 'side', warm: rad.clone().negate(), op: sm(21.0, 21.8, t) },
      bursts: true, grid: (0.3 * sm(32.8, 33.6, t) + 0.9 * sm(37.2, 38.0, t)) * (1 - sm(41.5, 41.95, t)) };
  }
  // 42–50.6: a friend far away: the astronaut goes off towards the hole, slower and slower, redder, and freezes at its edge
  function s5(t) {
    const c = sph(10, 30).multiplyScalar(40), look = V(0, 0.8, 0), f = look.clone().sub(c).normalize();
    const rgt = f.clone().cross(V(0, 1, 0)).normalize(), up = rgt.clone().cross(f);
    const k = (1 - Math.exp(-(t - 42.0) / 3.0)) / (1 - Math.exp(-8.6 / 3.0));
    const dd = lerpLog(1.6, 40.5, Math.pow(k, 1.25)), xs = lerp(0.17, 2.3 / 40, k), ys = lerp(-0.22, 2.0 / 40, k);
    const P = c.clone().addScaledVector(f, dd).addScaledVector(rgt, xs * dd).addScaledVector(up, ys * dd), red = k * k;
    return { cam: { pos: c, look, up: V(0, 1, 0), fov: 45 },
      astro: { pos: P, fwd: f, up, s: 0.35, poseT: 42 + 5.5 * k, tint: [1, 1 - 0.7 * red, 1 - 0.92 * red], op: 1 - sm(47.6, 50.2, t), tumble: k, env: 'back', warm: f } };
  }
  // 50.6–59.3: through his own eyes the fall goes on; round the photon sphere (1.5 r_s) light circles, and ahead in it
  // the back of his own helmet
  function orb() { const A = V(0.15, 0.3, 1).normalize(), T = V(1, 0.1, 0); const B = T.sub(A.clone().multiplyScalar(A.dot(T))).normalize(); return { A, B, N: A.clone().cross(B) }; }
  const R6 = t => t < 53.4 ? lerpLog(7.5, 1.72, Math.pow(clamp((t - 50.6) / 2.8, 0, 1), 1.6)) : lerp(1.72, 1.56, sm(53.4, 59.3, t));
  const PH6 = t => t < 53.4 ? 0.45 * sm(50.6, 53.4, t) : 0.45 + 0.42 * (t - 53.4);
  function s6(t) {
    const { A, B, N } = orb(), ph = PH6(t), R = R6(t);
    const rad = A.clone().multiplyScalar(Math.cos(ph)).addScaledVector(B, Math.sin(ph)), tan = B.clone().multiplyScalar(Math.cos(ph)).addScaledVector(A, -Math.sin(ph));
    const P = rad.clone().multiplyScalar(R), far = 1 + 1.6 * (1 - sm(50.6, 53.6, t));
    const pos = P.clone().addScaledVector(tan, -1.3 * far).addScaledVector(rad, 0.1 * far).addScaledVector(N, 0.35 * far);
    const look = P.clone().addScaledVector(tan, 2.5).addScaledVector(rad, 0.35 - 0.6 * (far - 1)).addScaledVector(N, -0.1);
    // his own back, seen ahead just under the bright ring (placed in the view: in front, a little up and to the side)
    const f = look.clone().sub(pos).normalize(), rg = f.clone().cross(rad).normalize(), uv = rg.clone().cross(f);
    const gp = pos.clone().addScaledVector(f, 2.2).addScaledVector(uv, 0.26).addScaledVector(rg, 0.42);
    // light circling the hole through that point, across the view
    const oA = gp.clone().normalize(), oB = f.clone().sub(oA.clone().multiplyScalar(f.dot(oA))).normalize();
    return { cam: { pos, look, up: rad.clone(), fov: 50 }, orbit: sm(52.6, 53.6, t), orb: { A: oA, B: oB, R: gp.length() },
      astro: { pos: P, fwd: tan.clone(), up: rad.clone(), s: 0.3, env: 'fall', warm: rad.clone().negate(), lookCam: sm(55.4, 56.4, t) * (1 - sm(58.6, 59.3, t)),
        ghost: { k: sm(56.2, 57.2, t), pos: gp, fwd: f.clone(), up: uv.clone() } } };
  }
  // 59.3–62.6: a small black hole (~10 Suns) would stretch him like spaghetti
  function s8a(t) {
    const c = sph(13, -35).multiplyScalar(14), look = V(0, 2.0, 0), e3 = c.clone().normalize();
    const e1 = V(0, 1, 0).cross(e3).normalize(), e2 = e3.clone().cross(e1);
    const w = e1.clone().multiplyScalar(Math.cos(70 * D)).addScaledVector(e2, Math.sin(70 * D));
    const k = 1 + 2.2 * Math.pow(sm(59.8, 62.4, t), 1.4), R = lerp(4.6, 3.5, sm(59.5, 62.5, t)) - 0.3 * (k - 1);
    return { cam: { pos: c, look, up: V(0, 1, 0), fov: 45 }, discTint: [0.78, 0.9, 1.2], discHot: 1.45,
      astro: { pos: w.clone().multiplyScalar(R), fwd: e3, up: w, s: 0.5, stretch: k, tint: [1, 1 - 0.08 * (k - 1), 1 - 0.12 * (k - 1)], env: 'side', warm: w.clone().negate() } };
  }
  // 62.6–67.3: at Sgr A* nothing of the kind: thumbs up
  function s8b(t) {
    const A = V(1.4, 1.1, 10), s = 0.32, head = A.clone().add(V(0, 0.8 * s, 0)), k = (t - 62.6) / 4.7;
    const pos = head.clone().addScaledVector(V(lerp(-0.12, -0.02, k), lerp(0.02, 0.1, k), 1).normalize(), lerp(2.3, 2.8, k) * s);
    return { cam: { pos, look: head.clone().add(V(-0.18 * s, -0.36 * s, 0)), up: V(0, 1, 0), fov: 42 },
      astro: { pos: A, fwd: V(0.12, 0, 1).normalize(), up: V(0, 1, 0), s, thumbs: [63.4, 66.9], env: 'front', warm: V(0.35, 0.3, 1) } };
  }
  // 67.3–78.8: through his eyes, looking back out: the sky squeezes into a bright circle; the horizon (a flash, a jolt);
  // then the circle shrinks to a dot (the static-observer view, as above: a sky ever further away)
  const r9 = t => 1 + (t < 71 ? lerpLog(0.45, 0.012, Math.pow(clamp((t - 67.3) / 3.7, 0, 1), 1.3)) : 0.012 * Math.exp(-(t - 71) / 1.25));
  function s9(t) {
    const u = V(0.3, 0.45, 1).normalize(), pos = u.clone().multiplyScalar(r9(t));
    const sh = 0.006 * sm(67.5, 70.9, t) + (t > 71 ? 0.025 * Math.exp(-(t - 71) / 0.35) : 0);
    return { cam: { pos, look: pos.clone().add(u), up: V(0, 1, 0), fov: 60 }, blue: sm(68.0, 70.6, t), shake: sh,
      flash: t > 71 ? 0.55 * Math.exp(-(t - 71) / 0.4) : 0, exposure: 1.25 * (1 - sm(77.6, 78.6, t)) };
  }
  // 78.8–86.5: the whole hole again under the question and the end card
  function s11(t) {
    return { cam: { pos: sph(9, 20 + (t - 78.8) * 1.5).multiplyScalar(46), look: V(0, 0.5, 0), up: V(0, 1, 0), fov: 45 }, exposure: 1.25 * sm(78.8, 79.7, t) };
  }

  function shotAt(t) {
    let S;
    if (t < 6.2) S = s1(t);
    else if (t < 16.4) S = s2(t);
    else if (t < 20.6) S = s3(t);
    else if (t < 21.8) {                        // a swoop down from above to the side view
      const a = s3(20.6).cam, b = s4(21.8).cam, k = ease((t - 20.6) / 1.2);
      S = s4(t);
      S.cam = { pos: slerpV(a.pos.clone().normalize(), b.pos.clone().sub(b.look).normalize(), k).multiplyScalar(lerpLog(a.pos.length(), b.pos.distanceTo(b.look), k)).add(a.look.clone().lerp(b.look, k)),
        look: a.look.clone().lerp(b.look, k), up: V(0, 1, 0), fov: 45 };
    }
    else if (t < 42.0) S = s4(t);
    else if (t < 50.6) S = s5(t);
    else if (t < 59.3) S = s6(t);
    else if (t < 62.6) S = s8a(t);
    else if (t < 67.3) S = s8b(t);
    else if (t < 78.8) S = s9(t);
    else S = s11(t);
    return Object.assign({ exposure: 1.25, discK: 1, discTint: [1, 1, 1], discHot: 1, merc: 0, blue: 0, flash: 0, shake: 0, grid: 0, you: 0 }, S);
  }

  return { V, sph, slerpV, Qh, shotAt, r4, th4, plane4, lamp4, BURSTS };
};
