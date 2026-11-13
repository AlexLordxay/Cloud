// Planet parade, 16 Nov 2026 — ENGLISH labels (copy of parade_site/cam.js): the site's Solar System from above. The camera rises from the Earth to a
// view over the inner system out to Jupiter, then rays go out from the Earth — to the Sun, and one by one to Mercury,
// Venus, Mars and Jupiter: all four lie on the same side of the Sun (west of it, as seen from here), so they rise before
// it and stand together in the dawn. The site's distances are stylised (log), so the rays' angles are only roughly the
// real ones (real elongations −17°, −30°, −86°, −88°; here about −30°, −36°, −77°, −71°): the side is what matters.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp;
  const IDS = ['mercury', 'venus', 'mars', 'jupiter'];
  const COL = { sun: [255, 214, 120], mercury: [205, 196, 186], venus: [255, 226, 160], mars: [255, 140, 100], jupiter: [235, 200, 160] };
  const NAME = { sun: 'Sun', earth: 'Earth', mercury: 'Mercury', venus: 'Venus', mars: 'Mars', jupiter: 'Jupiter' };
  const RAY_T = { sun: 2.9, mercury: 4.0, venus: 4.7, mars: 5.4, jupiter: 6.1 };   // when each ray grows (s; the voice: «Із Землі всі чотири…»)
  const SHOT2 = 11.3;   // the second shot: along the line of sight to Mars and Jupiter, and how far apart they really are
  let rays = {}, labels = {}, fan = null, ready = false;

  function label(T, text, col, cw = 512) {
    const c = document.createElement('canvas'); c.width = cw; c.height = 128;
    const g = c.getContext('2d'); g.font = 'bold 60px "DejaVu Sans", "Liberation Sans", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.shadowColor = 'rgba(0,0,0,0.9)'; g.shadowBlur = 14; g.fillStyle = `rgb(${col.join(',')})`; g.fillText(text, cw / 2, 64);
    const m = new T.SpriteMaterial({ map: new T.CanvasTexture(c), transparent: true, depthTest: false, depthWrite: false, sizeAttenuation: false });
    const s = new T.Sprite(m); s.scale.set(0.2 * cw / 512, 0.05, 1); s.renderOrder = 20; return s;
  }
  window.__sceneSetup = async (r) => {
    const s = r.state, T = r.THREE;
    s.index = r.BODIES.indexOf(r.byId.sun); s.mode = 'focus'; s.flight = null; s.rate = 0;
    if (r.kuiperBelt) r.kuiperBelt.visible = false;
    for (const id of ['sun', ...IDS]) {
      const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(12), 3)); g.setIndex([0, 1, 2, 0, 2, 3]);
      const c = COL[id], m = new T.MeshBasicMaterial({ color: new T.Color(c[0] / 255, c[1] / 255, c[2] / 255), transparent: true, opacity: 0, depthTest: false, side: T.DoubleSide });
      const l = new T.Mesh(g, m); l.renderOrder = 15; l.frustumCulled = false; r.scene.add(l); rays[id] = l;
    }
    for (const id of ['sun', 'earth', ...IDS]) { const sp = label(T, NAME[id], id === 'earth' ? [140, 200, 255] : COL[id]); sp.material.opacity = 0; r.scene.add(sp); labels[id] = sp; }
    // the morning side: a faint wedge between the outermost rays (filled once the rays are out)
    const fg = new T.BufferGeometry(); fg.setAttribute('position', new T.BufferAttribute(new Float32Array(9 * 24), 3));
    fan = new T.Mesh(fg, new T.MeshBasicMaterial({ color: 0x9cc2ff, transparent: true, opacity: 0, depthTest: false, side: T.DoubleSide }));
    fan.renderOrder = 14; fan.frustumCulled = false; r.scene.add(fan);
    ready = true;
  };

  let gap = null, gapLabel = null;
  function shot2(r, u) {
    const T = r.THREE, V = T.Vector3, B = r.byId, E = B.earth.world.clone(), M = B.mars.world.clone(), J = B.jupiter.world.clone();
    if (!gap) {
      const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(12), 3)); g.setIndex([0, 1, 2, 0, 2, 3]);
      gap = new T.Mesh(g, new T.MeshBasicMaterial({ color: 0xf7c66b, transparent: true, opacity: 0, depthTest: false, side: T.DoubleSide })); gap.renderOrder = 16; gap.frustumCulled = false; r.scene.add(gap);
      gapLabel = label(T, '≈ 592 million km', [247, 198, 107], 680); gapLabel.scale.set(0.34 * 680 / 512, 0.085, 1); r.scene.add(gapLabel);
    }
    const dir = J.clone().sub(E).normalize(), side = new V(-dir.z, 0, dir.x).normalize();
    // from just behind the Earth (Mars in front of Jupiter: together, as in the sky) swinging out to the side, where the
    // gap between them opens up along the line of sight
    const k = ease(Math.min(1, Math.max(0, (u - 0.5) / 2.6)));
    const mid = E.clone().lerp(J, 0.5), L = E.distanceTo(J);
    const p0 = E.clone().addScaledVector(dir, -9).add(new V(0, 2.2, 0)).addScaledVector(side, 1.2);
    // … up over the plane: the Earth at the bottom, Jupiter at the top, Mars between, the gap lit
    const mid2 = E.clone().lerp(J, 0.5);
    const p1 = mid2.clone().addScaledVector(dir, -L * 0.1).add(new V(0, L * 1.5, 0));
    const pos = p0.clone().lerp(p1, k);
    const look = J.clone().lerp(mid2, k);
    const up = new V(0, 1, 0).lerp(dir, k).normalize();
    const cam = r.camera; cam.position.copy(pos); cam.up.copy(up); cam.lookAt(look); r.controls.target.copy(look);
    for (const id in rays) rays[id].material.opacity = id === 'mars' || id === 'jupiter' ? 0.35 * smooth((u - 2.2) / 0.6) : 0;
    const g = smooth((u - 2.4) / 0.9), a = gap.geometry.attributes.position, end = M.clone().lerp(J, g), w = side.clone().multiplyScalar(0.35);
    a.setXYZ(0, M.x + w.x, M.y + 0.05, M.z + w.z); a.setXYZ(1, end.x + w.x, end.y + 0.05, end.z + w.z); a.setXYZ(2, end.x - w.x, end.y + 0.05, end.z - w.z); a.setXYZ(3, M.x - w.x, M.y + 0.05, M.z - w.z); a.needsUpdate = true;
    gap.material.opacity = 0.9 * smooth((u - 2.3) / 0.3);
    gapLabel.position.copy(M.clone().lerp(J, 0.5)).addScaledVector(side, -L * 0.075); gapLabel.material.opacity = smooth((u - 3.0) / 0.5);
  }
  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, T = r.THREE, V = T.Vector3, t = window.__vt() - (window.__t0 || 0);
    const B = r.byId, E = B.earth.world.clone(), S = new V(0, 0, 0), J = B.jupiter.world.clone();
    // the overview frame: Earth at the bottom, Jupiter at the top, the Sun between
    const upDir = J.clone().sub(E); upDir.y = 0; upDir.normalize();
    const span = E.distanceTo(J);
    const right = new V(-upDir.z, 0, upDir.x);
    // framed on the box round the Sun, the Earth, Mars and Jupiter (all in, with their labels)
    const pts = [S, E, B.mars.world, J, B.venus.world, B.mercury.world];
    const us = pts.map(p => p.clone().sub(E).dot(upDir)), rs = pts.map(p => p.clone().sub(E).dot(right));
    const u0 = Math.min(...us), u1 = Math.max(...us), r0 = Math.min(...rs), r1 = Math.max(...rs);
    const center = E.clone().addScaledVector(upDir, (u0 + u1) / 2).addScaledVector(right, (r0 + r1) / 2); center.y = 0;
    const hNeed = Math.max((u1 - u0 + 14) / 2 / Math.tan(22.5 * Math.PI / 180), (r1 - r0 + 16) / 2 / Math.tan(22.5 * Math.PI / 180) / (r.camera.aspect || 0.5625));
    const over = { pos: center.clone().addScaledVector(upDir, -hNeed * 0.12).add(new V(0, hNeed, 0)), look: center.clone(), up: upDir };
    // the opening: close over the Earth, rising and turning to the overview
    const k = ease(Math.min(1, t / 3.4));
    const near = { pos: E.clone().add(new V(0, 9, 0)).addScaledVector(upDir, -7), look: E.clone() };
    const pos = near.pos.clone().lerp(over.pos, k), look = near.look.clone().lerp(over.look, ease(Math.min(1, t / 2.8)));
    pos.addScaledVector(upDir, -span * 0.03 * smooth((t - 9) / 4)).y += span * 0.04 * smooth((t - 9) / 4);   // a slow drift at the end
    const cam = r.camera; cam.position.copy(pos); cam.up.copy(upDir); cam.lookAt(look); r.controls.target.copy(look);
    if (Math.abs(cam.near - 0.5) > 0.01) { cam.near = 0.5; cam.updateProjectionMatrix(); }
    // rays from the Earth: grow out over 0.6 s, through the body and a little beyond
    for (const id of ['sun', ...IDS]) {
      const P = (id === 'sun' ? S : B[id].world).clone(), g = smooth((t - RAY_T[id]) / 0.6);
      const end = E.clone().lerp(P, g * 1.12), a = rays[id].geometry.attributes.position;
      const dir = end.clone().sub(E), side = new V(-dir.z, 0, dir.x).normalize().multiplyScalar(span * 0.0035);
      a.setXYZ(0, E.x + side.x, E.y, E.z + side.z); a.setXYZ(1, end.x + side.x, end.y, end.z + side.z);
      a.setXYZ(2, end.x - side.x, end.y, end.z - side.z); a.setXYZ(3, E.x - side.x, E.y, E.z - side.z); a.needsUpdate = true;
      rays[id].material.opacity = 0.9 * smooth((t - RAY_T[id]) / 0.25);
    }
    // the wedge between the Sun's ray and the farthest-out planet ray (the morning side of the sky)
    const fk = smooth((t - 6.9) / 0.8) * 0.16 * (t < SHOT2 ? 1 : 0), pa = fan.geometry.attributes.position, sunA = Math.atan2(S.z - E.z, S.x - E.x);
    const ang = IDS.map(id => Math.atan2(B[id].world.z - E.z, B[id].world.x - E.x));
    const rel = a0 => ((a0 - sunA + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;
    const far = ang.reduce((m, a0) => Math.abs(rel(a0)) > Math.abs(rel(m)) ? a0 : m, sunA), R0 = span * 1.25;
    for (let i = 0; i < 24; i++) {
      const a0 = sunA + rel(far) * i / 24, a1 = sunA + rel(far) * (i + 1) / 24;
      pa.setXYZ(i * 3, E.x, E.y, E.z); pa.setXYZ(i * 3 + 1, E.x + Math.cos(a0) * R0, E.y, E.z + Math.sin(a0) * R0); pa.setXYZ(i * 3 + 2, E.x + Math.cos(a1) * R0, E.y, E.z + Math.sin(a1) * R0);
    }
    pa.needsUpdate = true; fan.material.opacity = fk;
    // labels next to the bodies
    for (const id of ['sun', 'earth', ...IDS]) {
      const b = B[id], sp = labels[id], P = b.world.clone(), off = (b.radius || 1) * (id === 'sun' ? 1.5 : 2.2) + span * 0.02;
      sp.position.copy(P).addScaledVector(upDir, -off);
      const tIn = id === 'earth' ? 1.2 : id === 'sun' ? RAY_T.sun : RAY_T[id] + 0.3;
      sp.material.opacity = smooth((t - tIn) / 0.4) * (t < SHOT2 || id === 'mars' || id === 'jupiter' || id === 'earth' ? 1 : 0);
    }
    if (t >= SHOT2) shot2(r, t - SHOT2);
    for (const x of r.BODIES) if (x.orbitLine) { const inner = ['mercury', 'venus', 'earth', 'mars', 'jupiter'].includes(x.id); x.orbitLine.visible = inner; if (inner) x.orbitLine.material.opacity = 0.32; }
  };
})();
