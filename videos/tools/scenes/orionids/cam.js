// Orionids and Halley's comet: the comet's 1986 pass, Mark Twain's two Halley years (1835 → 1910), the dust it leaves on
// its orbit, the Earth crossing that trail every October, meteors over night-time Ukraine, and the comet's return in 2061.
// The scene drives the simulated date itself (DATES below). The comet, its orbit and the planets are the site's own;
// the dust trail and the meteors exist only in the video.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const ms = s => Date.parse(s), DAY = 86400000;
  // Perihelia of the site's Halley (one fixed period: 1835.1, 1910.6, 1986.1, 2061.6 — within months of the real ones).
  const A = 17.86, PERIOD = 360 / (0.9856076686 / Math.pow(A, 1.5)) * DAY, P1986 = (2446470.96 - 2440587.5) * DAY;
  const peri = k => P1986 + k * PERIOD;
  const year = t => 1970 + t / (365.2425 * DAY);

  // Simulated date along the video: [t, date, curve]; the curve shapes the segment that ends at that key.
  const io = ease, iin = x => x * x, soft = x => 0.7 * x + 0.3 * ease(x);
  const DATES = [
    // Near the Sun the comet is fast: an even, slow pace keeps the tails continuous (a quick one leaves them dotted).
    [0, ms('1986-01-14T00:00:00Z')], [15, ms('1986-03-06T00:00:00Z'), soft],
    [15.001, peri(-2) - 12 * DAY], [25, peri(-1) + 40 * DAY, io],               // Mark Twain: 1835 → 1910
    [25.001, ms('2026-10-21T20:30:00Z')], [61, ms('2026-10-22T01:30:00Z'), x => x],   // the night of the peak
    [61.001, ms('2026-10-22T01:30:00Z')], [66.5, peri(1), io],                  // → 2061
    [72, peri(1) + 45 * DAY, iin],
  ];
  function simDate(t) {
    for (let i = 0; i < DATES.length - 1; i++) {
      const [ta, da] = DATES[i], [tb, db, f = x => x] = DATES[i + 1];
      if (t <= tb) return da + (db - da) * f(Math.min(1, Math.max(0, (t - ta) / (tb - ta))));
    }
    return DATES[DATES.length - 1][1];
  }
  // For the year counters in captions.py.
  window.__years = () => ({ twain: [year(DATES[2][1]), year(DATES[3][1])], back: [year(DATES[6][1]), year(DATES[7][1])] });

  let marker = null, dust = null, meteors = null, orbit = null;

  // The orbit, from the site's own orbit line: world points, cumulative length, and the point nearest the Earth crossing.
  function readOrbit(r) {
    const H = r.byId.halley, V = r.THREE.Vector3, g = H.orbitLine.geometry.attributes.position;
    H.orbitLine.updateMatrixWorld(true);
    const pts = [], len = [0];
    for (let i = 0; i < g.count; i++) pts.push(new V().fromBufferAttribute(g, i).applyMatrix4(H.orbitLine.matrixWorld));
    for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + pts[i].distanceTo(pts[i - 1]));
    let pi = 0, ai = 0;
    pts.forEach((p, i) => { if (p.length() < pts[pi].length()) pi = i; if (p.length() > pts[ai].length()) ai = i; });
    const n = new V();
    for (let i = 0; i < pts.length; i += 50) n.add(new V().crossVectors(pts[i], pts[(i + 50) % pts.length]));
    return { pts, len, total: len[len.length - 1], peri: pts[pi], aph: pts[ai], n: n.normalize() };
  }
  function orbitAt(s, out) {
    const L = orbit.total, len = orbit.len;
    s = ((s % L) + L) % L;
    let lo = 0, hi = len.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (len[m] > s) hi = m; else lo = m; }
    const k = (s - len[lo]) / Math.max(1e-9, len[hi] - len[lo]);
    return out.copy(orbit.pts[lo]).lerp(orbit.pts[hi], k);
  }

  // Dust: the trail along the whole orbit (drifting slowly the way the comet goes) and, around the place where the
  // Earth crosses it, a swarm streaming past the Earth from the Orionid radiant.
  function makeDust(r, crossS, radiant) {
    const T = r.THREE, V = T.Vector3, N = 14000, NS = 2600;
    const pos = new Float32Array(N * 3), alpha = new Float32Array(N), size = new Float32Array(N);
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(pos, 3));
    g.setAttribute('alpha', new T.BufferAttribute(alpha, 1));
    g.setAttribute('size', new T.BufferAttribute(size, 1));
    const u = { scale: { value: 1 }, fade: { value: 0 }, swarm: { value: 0 } };
    const m = new T.ShaderMaterial({
      uniforms: u,
      vertexShader: 'attribute float alpha; attribute float size; uniform float scale, fade, swarm; varying float vA; void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); float s = size * scale / -mv.z; gl_PointSize = clamp(s, 1.4, 7.0); vA = alpha * (size > 0.5 ? swarm : fade) * min(1.0, s * s / 2.0 + 0.35); gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'varying float vA; void main(){ vec2 c = gl_PointCoord - 0.5; float d = dot(c, c) * 4.0; if (d > 1.0) discard; float f = 1.0 - d; gl_FragColor = vec4(vec3(1.0, 0.86, 0.66), vA * f * f); }',
      transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    });
    const pts = new T.Points(g, m);
    pts.frustumCulled = false;
    r.scene.add(pts);
    const gauss = () => { let s = 0; for (let i = 0; i < 6; i++) s += Math.random(); return (s - 3) / 1.0; };
    const P = [];
    for (let i = 0; i < N; i++) {
      if (i < N - NS) {
        // On the orbit: 70 % anywhere along it, 30 % bunched up around the crossing (where it matters for the story).
        const s = Math.random() < 0.7 ? Math.random() * orbit.total : crossS + gauss() * 14;
        P.push({ s, a: gauss(), b: gauss(), j: Math.random() });
        size[i] = 0.25 + Math.random() * 0.2;
        alpha[i] = 0.25 + Math.random() * 0.35;
      } else {
        // The swarm: a box around the crossing, flowing along the radiant direction.
        P.push({ x: (Math.random() - 0.5) * 2, y: (Math.random() - 0.5) * 2, z: Math.random(), j: Math.random() });
        size[i] = 0.55 + Math.random() * 0.4;
        alpha[i] = 0.3 + Math.random() * 0.4;
      }
    }
    const p = new V(), q = new V(), tan = new V(), w1 = new V(), w2 = new V(), sw1 = new V(), sw2 = new V();
    sw1.crossVectors(radiant, new V(0, 1, 0)).normalize(); sw2.crossVectors(radiant, sw1).normalize();
    return {
      u,
      update(t, earth) {
        u.scale.value = r.renderer.domElement.height / (2 * Math.tan(r.camera.fov * D / 2));
        if (u.fade.value <= 0 && u.swarm.value <= 0) { pts.visible = false; return; }
        pts.visible = true;
        for (let i = 0; i < N; i++) {
          const o = P[i], k = i * 3;
          if (o.s != null) {
            const s = o.s + t * 1.2;                              // slow drift along the orbit
            orbitAt(s, p); orbitAt(s + 0.5, q);
            tan.subVectors(q, p).normalize();
            w1.crossVectors(tan, orbit.n).normalize(); w2.crossVectors(tan, w1);
            // Thin far from the Sun's neighbourhood, wide where the Earth crosses (the real stream is millions of km across).
            const dc = Math.abs(((s - crossS) % orbit.total + orbit.total * 1.5) % orbit.total - orbit.total / 2);
            const wide = 0.7 + 4.2 * Math.exp(-dc * dc / (2 * 18 * 18));
            p.addScaledVector(w1, o.a * wide).addScaledVector(w2, o.b * wide * 0.8);
          } else {
            // Swarm: 14 units across, 24 long, streaming 3 units/s past the Earth; fades in and out at the ends.
            const z = ((o.z + t * 0.125) % 1);
            p.copy(earth).addScaledVector(sw1, o.x * 7).addScaledVector(sw2, o.y * 7).addScaledVector(radiant, (0.5 - z) * 24);
            alpha[i] = (0.3 + o.j * 0.4) * Math.min(1, Math.min(z, 1 - z) * 6);
          }
          pos[k] = p.x; pos[k + 1] = p.y; pos[k + 2] = p.z;
        }
        g.attributes.position.needsUpdate = true;
        g.attributes.alpha.needsUpdate = true;
      },
    };
  }

  // Meteors: short streaks in the upper atmosphere over Ukraine, flying away from the radiant, each lasting ~0.5 s.
  function makeMeteors(r, radiant) {
    const T = r.THREE, V = T.Vector3, N = 24;
    const pos = new Float32Array(N * 4 * 3), uv = new Float32Array(N * 4 * 2), al = new Float32Array(N * 4), idx = [];
    for (let i = 0; i < N; i++) {
      uv.set([0, 0, 0, 1, 1, 0, 1, 1], i * 8);
      idx.push(i * 4, i * 4 + 2, i * 4 + 1, i * 4 + 1, i * 4 + 2, i * 4 + 3);
    }
    const g = new T.BufferGeometry();
    g.setAttribute('position', new T.BufferAttribute(pos, 3));
    g.setAttribute('uv', new T.BufferAttribute(uv, 2));
    g.setAttribute('al', new T.BufferAttribute(al, 1));
    g.setIndex(idx);
    const m = new T.ShaderMaterial({
      vertexShader: 'attribute float al; varying vec2 vUv; varying float vA; void main(){ vUv = uv; vA = al; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      // u: 0 at the tail, 1 at the head; v across. A thin bright core, greenish-white at the head, fading to the tail.
      fragmentShader: 'varying vec2 vUv; varying float vA; void main(){ float x = abs(vUv.y - 0.5) * 2.0; float core = exp(-x * x * 9.0); float along = pow(vUv.x, 1.6) * (1.0 - smoothstep(0.93, 1.0, vUv.x)); vec3 c = mix(vec3(1.0, 0.82, 0.55), vec3(0.85, 1.0, 0.9), vUv.x); gl_FragColor = vec4(c * core * along * vA * 2.4, 1.0); }',
      transparent: true, depthWrite: false, depthTest: false, side: T.DoubleSide, blending: T.AdditiveBlending,
    });
    const mesh = new T.Mesh(g, m);
    mesh.frustumCulled = false;
    mesh.renderOrder = 10;   // over the cloud deck and the atmosphere shell (which sits above them and would hide them);
                             // no depth test: they only appear on the side of the Earth facing the camera
    r.scene.add(mesh);
    // A fixed list: start time, place (lat, lon) and brightness. ~1.3 per second, a couple of bright ones.
    const list = [];
    let tt = 41.2;
    while (tt < 66) {
      list.push({ t: tt, lat: 45.5 + Math.random() * 7.5, lon: 24 + Math.random() * 15, b: Math.random() < 0.12 ? 1.0 : 0.45 + Math.random() * 0.35, l: 0.8 + Math.random() * 0.5 });
      tt += 0.35 + Math.random() * 0.75;
    }
    const v = new V(), a = new V(), b = new V(), side = new V(), cd = new V();
    return {
      update(t, geo, cam) {
        let n = 0;
        al.fill(0);
        for (const e of list) {
          const k = (t - e.t) / 0.7;
          if (k < 0 || k > 1 || n >= N) continue;
          // Path: from 118 km down along the flight direction (−radiant); the head runs, the tail follows and fades.
          const start = geo(e.lat, e.lon, 1 + 118 / 6371);
          const L = r.byId.earth.radius * 0.06 * e.l;   // ~3× the real ~100 km, so a trail reads at this scale
          const head = Math.min(1, k * 1.5), tail = Math.max(0, k * 1.5 - 0.6);
          a.copy(start).addScaledVector(radiant, -L * tail);
          b.copy(start).addScaledVector(radiant, -L * head);
          cd.subVectors(cam.position, b).normalize();
          side.crossVectors(radiant, cd).normalize();
          const wid = cam.position.distanceTo(b) * 0.0042;
          const i = n * 12;
          pos.set([a.x - side.x * wid, a.y - side.y * wid, a.z - side.z * wid, a.x + side.x * wid, a.y + side.y * wid, a.z + side.z * wid,
            b.x - side.x * wid, b.y - side.y * wid, b.z - side.z * wid, b.x + side.x * wid, b.y + side.y * wid, b.z + side.z * wid], i);
          const f = e.b * Math.min(1, k * 8) * (1 - smooth((k - 0.55) / 0.45));
          al.fill(f, n * 4, n * 4 + 4);
          n++;
        }
        g.attributes.position.needsUpdate = true;
        g.attributes.al.needsUpdate = true;
      },
    };
  }

  let radiant = null, crossS = 0, crossT = null;
  window.__sceneSetup = async (r) => {
    const s = r.state, T = r.THREE, V = T.Vector3, H = r.byId.halley;
    s.index = r.BODIES.indexOf(H); s.mode = 'focus'; s.flight = null;
    s.rate = 0; s.simMs = simDate(0);
    orbit = readOrbit(r);
    // Orionid radiant: RA 6h20m, Dec +16°, turned into the scene's ecliptic axes (x → equinox, y → ecliptic north).
    const ra = 95 * D, de = 16 * D, eps = 23.44 * D;
    const xe = Math.cos(de) * Math.cos(ra), ye = Math.cos(de) * Math.sin(ra), ze = Math.sin(de);
    radiant = new V(xe, -ye * Math.sin(eps) + ze * Math.cos(eps), -(ye * Math.cos(eps) + ze * Math.sin(eps))).normalize();
    // The point on the orbit nearest the Earth on the night of the peak.
    s.simMs = ms('2026-10-21T23:00:00Z'); window.__step(1 / 30);
    const E = r.byId.earth.world;
    let best = 1e9;
    orbit.pts.forEach((p, i) => { const d = p.distanceTo(E); if (d < best) { best = d; crossS = orbit.len[i]; } });
    crossT = orbitAt(crossS + 0.5, new V()).sub(orbitAt(crossS - 0.5, new V())).normalize();
    s.simMs = simDate(0);
    dust = makeDust(r, crossS, radiant);
    meteors = makeMeteors(r, radiant);
    // A thin ring marking the comet in the wide shots, where it is only a few pixels.
    const mc = document.createElement('canvas'); mc.width = mc.height = 128;
    const mg = mc.getContext('2d'); mg.strokeStyle = 'rgba(170,205,255,0.9)'; mg.lineWidth = 5; mg.beginPath(); mg.arc(64, 64, 52, 0, Math.PI * 2); mg.stroke();
    marker = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(mc), transparent: true, depthWrite: false, depthTest: false }));
    r.scene.add(marker);
    // No aurora: over night-time Ukraine it would compete with the meteors.
    const Ea = r.byId.earth;
    for (const m of Ea.tiltGroup.children) if (m.geometry && m.geometry.parameters && Math.abs(m.geometry.parameters.radius - Ea.radius * 1.025) < 1e-6) m.visible = false;
  };

  // A point above the Earth at (lat, lon), h Earth radii from the centre, in world coordinates.
  function geoOf(r, lat, lon, h) {
    const E = r.byId.earth, q = E.mesh.getWorldQuaternion(new r.THREE.Quaternion());
    const l = new r.THREE.Vector3(Math.cos(lat * D) * Math.cos(lon * D), Math.sin(lat * D), -Math.cos(lat * D) * Math.sin(lon * D));
    return l.applyQuaternion(q).multiplyScalar(E.radius * h).add(E.world);
  }

  // The whole orbit seen from above its plane, the Sun at the top of the frame.
  function overview(r, k, dist) {
    const V = r.THREE.Vector3, axis = orbit.peri.clone().sub(orbit.aph).normalize();
    const mid = orbit.peri.clone().lerp(orbit.aph, 0.5);
    const n = orbit.n.clone().multiplyScalar(orbit.n.y < 0 ? -1 : 1);
    const pos = mid.clone().addScaledVector(n, dist);
    pos.addScaledVector(axis, -dist * 0.12).sub(mid).applyAxisAngle(axis, lerp(-0.12, 0.12, k)).add(mid);
    return { pos, look: mid.clone().addScaledVector(axis, 6), up: axis };
  }

  window.__recCam = () => {
    if (!marker) return;   // the site is still loading; the scene isn't set up yet
    const r = window.__rec, T = r.THREE, V = T.Vector3, t = window.__vt() - (window.__t0 || 0);
    const H = r.byId.halley, E = r.byId.earth, P = H.world.clone(), C = E.world.clone();
    r.state.simMs = simDate(t + 1 / 30);   // the date for the next frame
    const geo = (lat, lon, h) => geoOf(r, lat, lon, h);
    const sunDir = P.clone().negate().normalize();
    const n = orbit.n.clone().multiplyScalar(orbit.n.y < 0 ? -1 : 1);

    let pos, look, up = new V(0, 1, 0);
    if (t < 15) {
      // 1986: close to the comet as it swings round the Sun, tails streaming away; then back to see its path.
      const pd = orbit.peri.clone().normalize();
      const close = { pos: P.clone().addScaledVector(n, 34).addScaledVector(sunDir, 3), look: P.clone().addScaledVector(sunDir, -3.5) };
      const far = { pos: n.clone().multiplyScalar(175).addScaledVector(P, 0.45), look: P.clone().multiplyScalar(0.45) };
      const w = ease((t - 7) / 8);
      pos = close.pos.lerp(far.pos, w); look = close.look.lerp(far.look, w);
      // The tail straight up the frame while close, settling to the Sun-at-the-top framing of the wide shots.
      up = sunDir.clone().negate().lerp(pd, smooth((t - 5) / 6)).normalize();
    } else if (t < 25) {
      ({ pos, look, up } = overview(r, (t - 15) / 10, 255));
    } else if (t < 45.5) {
      // The trail, then down to the Earth flying through it, and on to night-time Ukraine.
      const k = (t - 25) / 9;
      // Looking along the trail towards the Earth: the dust runs past the camera and on into the planet's path.
      const k1 = smooth(k);
      const wide = { pos: C.clone().addScaledVector(crossT, lerp(34, 26, k1)).addScaledVector(n, lerp(9, 7, k1)).addScaledVector(C.clone().normalize(), 6),
        look: C.clone().addScaledVector(n, 2) };
      if (t < 34) ({ pos, look } = wide);
      else {
        // First straight in until the Earth fills the frame (so the Sun stays hidden behind it), then round over the
        // globe to above Ukraine, settling lower. One direction all the way: no swing back.
        const end = geo(51.5, 31.5, 1.6), endLook = geo(49.6, 31.5, 1.0), R = E.radius;
        const d0 = wide.pos.distanceTo(C), dIn = 2.6 * R;
        const dist = Math.exp(lerp(Math.log(d0), Math.log(dIn), ease((t - 34) / 5.5))) * lerp(1, end.distanceTo(C) / dIn, smooth((t - 39) / 6.5));
        const dir = wide.pos.clone().sub(C).normalize().lerp(end.clone().sub(C).normalize(), smooth((t - 37.5) / 8)).normalize();
        pos = C.clone().addScaledVector(dir, dist);
        look = wide.look.clone().lerp(C, smooth((t - 34) / 3)).lerp(endLook, smooth((t - 39.5) / 6));
      }
      up = t < 38 ? n : n.clone().lerp(geo(90, 0, 1).sub(C).normalize(), smooth((t - 38) / 7.5)).normalize();
    } else if (t < 61) {
      // Over Ukraine at night: slowly lower, the meteors flashing through the upper atmosphere.
      const e = smooth((t - 45.5) / 15.5);
      // Seen almost straight down: the radiant is high in the south-east, so from here the trails show their length.
      pos = geo(lerp(51.5, 51, e), lerp(31.5, 32, e), lerp(1.6, 1.38, e));
      look = geo(lerp(49.6, 49.2, e), lerp(31.5, 32, e), 1.0);
      up = geo(90, 0, 1).sub(C).normalize();
    } else {
      ({ pos, look, up } = overview(r, 1 - (t - 61) / 11, lerp(260, 200, ease((t - 61) / 11))));
    }

    // Orbit lines: Halley's stands out in the wide shots, the Earth's while it crosses the trail.
    const hOn = t < 15 ? smooth((t - 7) / 3) : t < 25 ? 1 : t < 44 ? 0.5 * (1 - smooth((t - 33) / 3)) : t < 61 ? 0 : 1;
    const eOn = t >= 25 && t < 44 ? 1 - smooth((t - 34) / 2.5) : 0;
    const oOn = t < 15 ? smooth((t - 7) / 3) * 0.6 : t < 25 ? 0.8 : t < 61 ? 0 : 0.8;
    for (const x of r.BODIES) if (x.orbitLine) {
      const o = x === H ? 0.6 * hOn : x === E ? Math.max(0.5 * eOn, x.baseOpacity * oOn) : x.parent ? 0 : x.baseOpacity * oOn;
      x.orbitLine.visible = o > 0.003; x.orbitLine.material.opacity = o;
    }
    r.asteroidBelt.visible = r.kuiperBelt.visible = false;

    // Dust and meteors.
    dust.u.fade.value = t < 25 ? 0 : t < 61 ? smooth((t - 25.6) / 3) * (1 - smooth((t - 40) / 3)) : 0.55 * smooth((t - 61.6) / 2);
    dust.u.swarm.value = t >= 25 && t < 61 ? smooth((t - 33) / 3) * (1 - smooth((t - 42) / 2.5)) : 0;
    dust.update(t, C);

    // The marker ring: only in the wide shots.
    const mOn = t < 15 ? smooth((t - 10) / 2) : t < 25 ? 1 : t < 61 ? 0 : 1 - smooth((t - 65) / 1.5);
    marker.position.copy(P);
    const md = pos.distanceTo(P);
    marker.scale.set(md * 0.05, md * 0.05, 1);
    marker.material.opacity = Math.min(1, Math.max(0, mOn)) * 0.85;
    marker.visible = marker.material.opacity > 0.01;

    const cam = r.camera;
    cam.position.copy(pos); cam.up.copy(up); cam.lookAt(look);
    r.controls.target.copy(look);
    meteors.update(t, geo, cam);
    const dE = pos.distanceTo(C) - E.radius * 1.05, dH = pos.distanceTo(P) - H.radius * 2;
    const near = Math.max(0.002, Math.min(0.5, Math.min(dE, dH) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
