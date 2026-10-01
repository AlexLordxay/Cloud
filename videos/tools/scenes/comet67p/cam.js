// "Story with a hero": comet 67P/Churyumov–Gerasimenko — found by Kyiv astronomers in 1969, reached by Rosetta in 2014,
// Philae's bouncing landing, the comet's "song" and its tail in 2015.
// The scene drives the simulated date itself (DATES below); the camera follows the comet.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  const ms = s => Date.parse(s);

  // Simulated date along the video: [t, date]; eased between keys.
  const DATES = [
    [0, ms('1969-08-20T00:00:00Z')], [19, ms('1969-11-01T00:00:00Z')],
    [20.5, ms('2004-03-02T00:00:00Z')], [34, ms('2014-08-06T00:00:00Z')],
    [41, ms('2014-11-12T13:00:00Z')], [52, ms('2014-11-12T19:00:00Z')],
    [56.5, ms('2015-08-13T00:00:00Z')], [72, ms('2015-09-20T00:00:00Z')],
  ];
  function simDate(t) {
    for (let i = 0; i < DATES.length - 1; i++) {
      const [ta, da] = DATES[i], [tb, db] = DATES[i + 1];
      if (t <= tb) return da + (db - da) * ease((t - ta) / (tb - ta));
    }
    return DATES[DATES.length - 1][1];
  }

  let philae = null, head = null, site = null, marker = null;
  window.__sceneSetup = async (r) => {
    const s = r.state, T = r.THREE, c = r.byId.cg67p;
    s.index = r.BODIES.indexOf(c); s.mode = 'focus'; s.flight = null;
    s.rate = 0; s.simMs = simDate(0);
    head = c.mesh.children.find(o => o.isMesh);
    // Philae: a small soft light (no 3D model on the site), parented to the comet's head lobe where it really landed.
    const cv = document.createElement('canvas'); cv.width = cv.height = 64;
    const g = cv.getContext('2d'), grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.25, 'rgba(210,230,255,0.8)'); grd.addColorStop(1, 'rgba(160,200,255,0)');
    g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
    philae = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(cv), transparent: true, depthWrite: false, blending: T.AdditiveBlending }));
    philae.visible = false;
    head.add(philae);
    // The real nucleus is darker than coal (albedo ~6 %): dim the shared material for the close-ups.
    c.mesh.material.color.multiplyScalar(0.62);
    // A thin ring marking the comet in the wide shots, where it is only a few pixels.
    const mc = document.createElement('canvas'); mc.width = mc.height = 128;
    const mg = mc.getContext('2d'); mg.strokeStyle = 'rgba(170,205,255,0.9)'; mg.lineWidth = 5; mg.beginPath(); mg.arc(64, 64, 52, 0, Math.PI * 2); mg.stroke();
    marker = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(mc), transparent: true, depthWrite: false, depthTest: false }));
    r.scene.add(marker);
  };

  // Points on the head lobe: a direction in its local frame, at height h (in head radii) above the surface.
  function onHead(r, dir, h) {
    const R = r.byId.cg67p.radius * 0.7;
    return dir.clone().normalize().multiplyScalar(R * (1 + h));
  }

  window.__recCam = () => {
    const r = window.__rec, T = r.THREE, V = T.Vector3, t = window.__vt() - (window.__t0 || 0);
    const c = r.byId.cg67p, P = c.world.clone(), sunDir = P.clone().negate().normalize();
    r.state.simMs = simDate(t + 1 / 30);   // the date for the next frame
    // The nucleus turns slowly while we approach; it holds still during the landing so the site stays in view.
    if (t > 34 && t < 39.5) c.mesh.rotation.y += 0.004;

    // Orbit lines: 67P's orbit stands out; everything fades as we close in on the nucleus.
    const far = 1 - smooth((t - 30) / 4) + smooth((t - 60) / 6);
    const ofar = Math.min(1, far) * (1 - smooth((t - 15) / 3) + smooth((t - 19.5) / 1.5));
    for (const x of r.BODIES) if (x.orbitLine) {
      const mine = x === c;
      x.orbitLine.visible = true;
      x.orbitLine.material.opacity = (mine ? 0.6 : x.baseOpacity * 0.9) * Math.max(mine ? Math.min(1, far) : ofar, 0.0);
    }

    // Philae: fixed landing site picked once, facing the Sun and the camera, so the touchdown is lit.
    if (t > 38.5 && !site) {
      const inv = new T.Quaternion().copy(head.getWorldQuaternion(new T.Quaternion())).invert();
      const d1 = sunDir.clone().applyQuaternion(inv).add(new V(0, 0.6, 0)).normalize();
      const axis = new V(0, 0, 1).cross(d1).normalize();
      site = { d1, d2: d1.clone().applyAxisAngle(axis, 38 * D), d3: d1.clone().applyAxisAngle(axis, 52 * D) };
    }
    let pPos = null;
    if (site) {
      // 41–44 s descent, 44–47.5 first bounce (~1 km up), 47.5–48.6 a small hop into the shadow of a cliff.
      let dir = site.d1, h = 0, glow = 1;
      if (t < 41) { h = 2.5; glow = 0; }
      else if (t < 44) h = lerp(2.5, 0, smooth((t - 41) / 3));
      else if (t < 47.5) { const u = (t - 44) / 3.5; dir = site.d1.clone().lerp(site.d2, u); h = 1.6 * u * (1 - u); }
      else if (t < 48.6) { const u = (t - 47.5) / 1.1; dir = site.d2.clone().lerp(site.d3, u); h = 0.35 * u * (1 - u); }
      else { dir = site.d3; glow = Math.max(0.25, 1 - (t - 48.6) / 2); }
      glow *= (t > 40 ? smooth((t - 40) / 1) : 0) * (1 - smooth((t - 52) / 1.5));
      philae.position.copy(onHead(r, dir, h + 0.03));
      const sz = c.radius * 0.06 * (0.85 + 0.15 * Math.sin(t * 6));
      philae.scale.set(sz / 0.85, sz / 0.85, 1);   // undo most of the head lobe's squash
      philae.material.opacity = glow;
      philae.visible = glow > 0.01;
      pPos = philae.getWorldPosition(new V());
    }

    // Camera.
    const up = new V(0, 1, 0), side = new V().crossVectors(sunDir, up).normalize();
    let pos, look;
    const wideA = new V(40, 260, 300), wideB = new V(-60, 330, 210);
    if (t < 7.2) {                               // hook: the inner Solar System from above, 67P's orbit highlighted
      const e = ease(t / 7.2);
      pos = wideA.clone().multiplyScalar(lerp(1.15, 0.95, e)); look = new V(0, 0, 0).lerp(P, 0.35);
    } else if (t < 19) {                         // 1969: fly to the comet
      const e = ease((t - 7.2) / 11.8);
      const near = P.clone().addScaledVector(side, 12).addScaledVector(up, 7).addScaledVector(sunDir, 6);
      pos = wideA.clone().multiplyScalar(0.95).lerp(near, Math.pow(e, 1.6)); look = new V(0, 0, 0).lerp(P, 0.35 + 0.65 * e);
    } else if (t < 34) {                         // 2004 → 2014: ten years of chase, seen from far above
      const e = ease((t - 19) / 15);
      pos = wideB.clone().applyAxisAngle(up, e * 0.5); look = new V(0, 0, 0).lerp(P, 0.25);
      if (t < 20.5) {                            // glide out of the 1969 close view
        const from = P.clone().addScaledVector(side, 12).addScaledVector(up, 7).addScaledVector(sunDir, 6);
        const w = smooth((t - 19) / 1.5);
        pos = from.lerp(pos, w); look = P.clone().lerp(look, w);
      }
    } else if (t < 41) {                         // arrival: down to the rubber-duck nucleus
      const e = ease((t - 34) / 7);
      const from = wideB.clone().applyAxisAngle(up, 0.5);
      const near = P.clone().addScaledVector(sunDir, 0.42).addScaledVector(side, 0.32).addScaledVector(up, 0.22);
      pos = from.lerp(near, Math.pow(e, 0.35)); look = new V(0, 0, 0).lerp(P, 0.25 + 0.75 * smooth((t - 34) / 2.2));
    } else if (t < 52) {                         // Philae's landing, the camera watching the site
      const target = pPos || P;
      const n = target.clone().sub(P).normalize();
      const e = smooth((t - 41) / 4);
      const base = P.clone().addScaledVector(sunDir, 0.42).addScaledVector(side, 0.32).addScaledVector(up, 0.22);
      const watch = P.clone().addScaledVector(n.clone().add(sunDir).normalize(), 0.46).addScaledVector(side, 0.1);
      pos = base.lerp(watch, e); look = P.clone().lerp(target, 0.35 * e);
    } else {                                     // 2015: the comet wakes up near the Sun; pull back to see the tail
      const e = ease((t - 52) / 20);
      const target = P;
      const back = P.clone().addScaledVector(side, lerp(0.5, 15, e)).addScaledVector(up, lerp(0.3, 6, e)).addScaledVector(sunDir, lerp(0.4, 7, e));
      pos = back; look = target.clone().addScaledVector(sunDir, -lerp(0, 5, e));
    }
    // The marker ring: only on the wide shots.
    const mOn = (1 - smooth((t - 12) / 2)) + smooth((t - 20.5) / 1) * (1 - smooth((t - 33.5) / 1.2));
    marker.position.copy(P);
    const md = pos.distanceTo(P);
    marker.scale.set(md * 0.05, md * 0.05, 1);
    marker.material.opacity = Math.min(1, Math.max(0, mOn)) * 0.85;
    marker.visible = marker.material.opacity > 0.01;
    const cam = r.camera;
    cam.position.copy(pos); cam.up.set(0, 1, 0); cam.lookAt(look);
    r.controls.target.copy(look);
    const dist = pos.distanceTo(P);
    const near = Math.max(0.002, Math.min(0.5, (dist - c.radius * 1.3) * 0.3));
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };
})();
