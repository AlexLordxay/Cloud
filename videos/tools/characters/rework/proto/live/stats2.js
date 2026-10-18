window.__poseMode = () => {};
// Prototype (scratch only): a livelier idle + gesture layer, monkeypatched onto `a`. Pure functions of t, no state.
{
  const J = a.joints, TAU = Math.PI * 2;
  const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x)), sm = x => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
  const hash = n => { const v = Math.sin(n * 127.1 + 311.7) * 43758.5453; return v - Math.floor(v); };
  // finger joints (not exposed by astronaut.js today): hand group = the wrist's child group; 4 fingers then the thumb
  const H = {};
  for (const L of ['L', 'R']) {
    const hand = J['wrist' + L].children.find(c => c.isGroup), gs = hand.children.filter(c => c.isGroup);
    H[L] = { hand, f: gs.slice(0, 4).map(g => ({ base: g, tip: g.children.find(c => c.isGroup), rest: g.rotation.clone() })), th: { base: gs[4], tip: gs[4].children.find(c => c.isGroup) } };
  }
  // hand shape: curl[0..3] per finger (0 open .. 1 fist), spread, thumb: 'rest' | 'up' | 'tuck' | 'open'
  a.hand = (L, curl, spread = 0, thumb = 'rest', k = 1) => {
    const s = L === 'L' ? -1 : 1, h = H[L];
    h.f.forEach((f, i) => {
      const c = Array.isArray(curl) ? curl[i] : curl;
      const bx = 0.05 + 1.25 * c, tx = 0.1 + 1.35 * c, bz = -s * (i - 1.5) * (0.06 + 0.12 * spread);
      f.base.rotation.set(f.base.rotation.x + (bx - f.base.rotation.x) * k, 0, f.base.rotation.z + (bz - f.base.rotation.z) * k);
      f.tip.rotation.x += (tx - f.tip.rotation.x) * k;
    });
    const T = { rest: [0.5, 0, -s * 0.8, 0.5], up: [-0.1, 0, s * 1.35, 0.0], tuck: [1.0, 0, -s * 0.35, 0.9], open: [0.15, 0, -s * 1.1, 0.15] }[thumb];
    const b = h.th.base.rotation; b.set(b.x + (T[0] - b.x) * k, 0, b.z + (T[2] - b.z) * k); h.th.tip.rotation.x += (T[3] - h.th.tip.rotation.x) * k;
  };

  // ---- the idle: a few shared drivers; each joint follows one of them, later down the chain (overlap) ----
  a.idle2 = (t) => {
    const ph = x => x + 0.22 * Math.sin(x);                                  // inhale a bit quicker than exhale
    const breath = d => Math.sin(ph(TAU * (t - d) / 4.6));                     // ~13 breaths a minute
    const drift = (p, o, d = 0) => Math.sin(TAU * (t - d) / p + o);
    const B = breath(0);
    // torso: breath pitch + a slow drift; the head keeps the horizon (counter-rolls part of the body roll)
    const bx = 0.05 + 0.012 * B + 0.025 * drift(10.3, 0), bz = 0.03 * drift(12.9, 1.3), by = 0.035 * drift(15.1, 2.2);
    J.body.rotation.set(bx, by, bz);
    // glances: a new (yaw, pitch) every ~5 s, reached in ~1 s, held; deterministic from t
    const slot = 5.2, n = Math.floor(t / slot), u = sm((t - n * slot) / 1.1);
    const g = i => [0.45 * (hash(i) - 0.5) * 2 * (hash(i + 9) > 0.35 ? 1 : 0.2), -0.12 + 0.22 * (hash(i + 3) - 0.5)];
    const g0 = g(n - 1), g1 = g(n);
    const yaw = g0[0] + (g1[0] - g0[0]) * u, pit = g0[1] + (g1[1] - g0[1]) * u;
    J.head.rotation.set(pit + 0.015 * breath(0.35) - 0.5 * (bx - 0.05), yaw - 0.4 * by, -0.6 * bz + 0.03 * (g1[0] - g0[0]) * Math.sin(Math.PI * u), 'XYZ');
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R', o = s < 0 ? 0 : 2.4, A = s < 0 ? 1 : -1;     // A: the two sides a little different
      const arm = d => drift(7.9 + 0.6 * A, o, d), leg = d => drift(11.7 + 0.8 * A, o + 1, d);
      // arms afloat in front (after NASA's neutral body posture, a little more open so the silhouette reads from behind)
      J['shoulder' + L].rotation.set(0.42 + 0.05 * A + 0.06 * arm(0) + 0.015 * B, 0.12 * s, s * (0.74 + 0.06 * A + 0.05 * arm(0.6) + 0.025 * breath(0.2)));
      J['elbow' + L].rotation.set(1.05 + 0.12 * A + 0.1 * arm(0.5), 0, 0);
      J['wrist' + L].rotation.set(0.22 + 0.09 * arm(1.0), s * 0.55, s * (0.12 + 0.05 * arm(1.3)));
      J['hip' + L].rotation.set(0.62 + 0.08 * A + 0.05 * leg(0), 0, s * (0.12 + 0.03 * leg(0.8)));
      J['knee' + L].rotation.set(-0.95 - 0.18 * A - 0.08 * leg(0.7), 0, 0);
      J['ankle' + L].rotation.set(-0.22 + 0.06 * leg(1.4), 0, s * 0.04);
      // fingers: relaxed, half-curled, more curl toward the little finger; a slow ripple runs across them
      const c = [0, 1, 2, 3].map(i => 0.3 + 0.07 * i + 0.06 * Math.sin(TAU * t / 6.3 - i * 0.5 + o) + 0.03 * arm(1.5));
      a.hand(L, c, 0.25 + 0.1 * arm(1.8), 'rest');
    }
  };

  // ---- gestures: layer on top of whatever pose is set; k 0..1 is the blend (ease it in the scene) ----
  const V = (x) => Array.isArray(x) ? new THREE.Vector3(...x) : x.clone();
  const qOf = (o) => o.quaternion.clone();
  const blendQ = (o, q, k) => o.quaternion.slerp(q, k);
  const blendE = (o, v, k) => o.rotation.set(o.rotation.x + (v[0] - o.rotation.x) * k, o.rotation.y + (v[1] - o.rotation.y) * k, o.rotation.z + (v[2] - o.rotation.z) * k);
  // the arm's rest frame: bone along -y, elbow folds toward -z. Build a shoulder quaternion from (bone dir, fold dir) in body space.
  const armQ = (dir, fold) => {
    const y = dir.clone().normalize().negate(), z = fold.clone().addScaledVector(dir, -fold.dot(dir) / dir.lengthSq()).normalize().negate(), x = new THREE.Vector3().crossVectors(y, z);
    return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  };
  // wave: upper arm out and up, forearm up, palm to the viewer; the forearm swings in the frontal plane, the hand lags behind
  a.wave = (t, k = 1, L = 'R', hz = 1.3) => {
    const s = L === 'L' ? -1 : 1, w = Math.sin(TAU * hz * t), wl = Math.sin(TAU * hz * t - 0.9);
    blendQ(J['shoulder' + L], armQ(new THREE.Vector3(s, 0.35, -0.25), new THREE.Vector3(0, 1, 0)), k);
    blendE(J['elbow' + L], [1.55 + 0.35 * w, 0, 0], k);
    blendE(J['wrist' + L], [0, s * 1.5, 0.22 * s * wl], k);
    a.hand(L, [0.08, 0.06, 0.08, 0.12], 0.8, 'open', k);
    J.body.rotation.z += -s * 0.012 * w * k;                                                  // free fall: the body answers the arm
    J.head.rotation.z += s * 0.08 * k; 
  };
  // point: the arm straight at a world point, index out, palm down; the head follows, the body turns a little
  a.point = (target, k = 1, L = 'R') => {
    const sh = J['shoulder' + L], P = J.body.worldToLocal(V(target)), d = P.sub(sh.position).normalize();
    d.y += 0.06; d.normalize();
    blendQ(sh, armQ(d, new THREE.Vector3(0, -1, 0).addScaledVector(d, 0.3)), k);
    blendE(J['elbow' + L], [0.12, 0, 0], k);
    blendE(J['wrist' + L], [0.05, 0, 0], k);
    a.hand(L, [0.0, 0.95, 1.0, 1.0], 0.0, 'tuck', k);
  };
  a.thumbsUp = (k = 1, L = 'R') => {
    const s = L === 'L' ? -1 : 1;
    blendE(J['shoulder' + L], [0.75, 0, s * 0.28], k);
    blendE(J['elbow' + L], [1.35, 0, 0], k);
    blendE(J['wrist' + L], [0.1, s * Math.PI / 2, 0], k);
    a.hand(L, 1.0, 0, 'up', k);
  };
  // look at a world point: the head takes most of it (clamped like a real neck), the body the rest
  a.lookAt = (target, k = 1) => {
    a.group.updateMatrixWorld(true);
    const P = J.body.worldToLocal(V(target)).sub(J.head.position).sub(new THREE.Vector3(0, 0.16, 0));
    const yaw = Math.atan2(-P.x, -P.z), pit = Math.atan2(P.y, Math.hypot(P.x, P.z));
    const hy = clamp(yaw, -0.75, 0.75), hp = clamp(pit, -0.45, 0.35);
    blendE(J.head, [hp, hy, 0], k);
    J.body.rotation.y += 0.3 * (yaw - hy + 0.2 * hy) * k;
  };
  if (window.__poseMode) window.__poseMode();
}
{
  const V = () => new THREE.Vector3();
  const rec = [];
  const dt = 1 / 30;
  for (let i = 0; i <= 30 * 24; i++) {
    const t = i * dt; a.pose(t); a.idle2(t); a.group.updateMatrixWorld(true);
    const hl = a.joints.wristL.localToWorld(new THREE.Vector3(0, -0.15, 0)), hr = a.joints.wristR.localToWorld(new THREE.Vector3(0, -0.15, 0));
    const el = a.joints.elbowL.getWorldPosition(V()), kn = a.joints.kneeL.getWorldPosition(V()), an = a.joints.ankleL.getWorldPosition(V()), anR = a.joints.ankleR.getWorldPosition(V());
    const hd = a.joints.head.localToWorld(new THREE.Vector3(0, 0.16, -1)).sub(a.joints.head.localToWorld(new THREE.Vector3(0, 0.16, 0)));
    rec.push({ t, hl, hr, el, kn, an, anR, hd });
  }
  const rng = k => { const xs = rec.map(r => r[k]); const mn = V().set(1e9,1e9,1e9), mx = V().set(-1e9,-1e9,-1e9); xs.forEach(v => { mn.min(v); mx.max(v); }); return mx.sub(mn).toArray().map(v => v.toFixed(3)); };
  const spd = k => { let m = 0, s = 0; for (let i = 1; i < rec.length; i++) { const v = rec[i][k].distanceTo(rec[i - 1][k]) / dt; m = Math.max(m, v); s += v; } return [m.toFixed(3), (s / (rec.length - 1)).toFixed(3)]; };
  console.log('range xyz (m) hand L', rng('hl'), 'hand R', rng('hr'), 'elbowL', rng('el'), 'kneeL', rng('kn'), 'ankleL', rng('an'), 'ankleR', rng('anR'));
  console.log('speed max/mean (m/s) hand L', spd('hl'), 'hand R', spd('hr'), 'ankleL', spd('an'));
  // head direction range in degrees
  const yaw = rec.map(r => Math.atan2(-r.hd.x, -r.hd.z) * 57.3), pit = rec.map(r => Math.asin(r.hd.y) * 57.3);
  console.log('head yaw deg', Math.min(...yaw).toFixed(1), Math.max(...yaw).toFixed(1), 'pitch deg', Math.min(...pit).toFixed(1), Math.max(...pit).toFixed(1));
  // L-R correlation of hand height
  const ly = rec.map(r => r.hl.y), ry = rec.map(r => r.hr.y);
  const mean = a => a.reduce((s, v) => s + v, 0) / a.length, ml = mean(ly), mr = mean(ry);
  let c = 0, vl = 0, vr = 0; for (let i = 0; i < ly.length; i++) { c += (ly[i] - ml) * (ry[i] - mr); vl += (ly[i] - ml) ** 2; vr += (ry[i] - mr) ** 2; }
  console.log('corr handL.y vs handR.y', (c / Math.sqrt(vl * vr)).toFixed(3));
  // world pos of hands at rest relative to shoulders/head
  a.pose(0); a.idle2(0); a.group.updateMatrixWorld(true);
  const hl = a.joints.wristL.localToWorld(new THREE.Vector3(0, -0.15, 0)), hr = a.joints.wristR.localToWorld(new THREE.Vector3(0, -0.15, 0));
  console.log('t0 hand L', hl.toArray().map(v=>v.toFixed(2)), 'hand R', hr.toArray().map(v=>v.toFixed(2)), 'head', a.joints.head.getWorldPosition(V()).toArray().map(v=>v.toFixed(2)));
  const bb = new THREE.Box3().setFromObject(a.group); console.log('bbox', bb.min.toArray().map(v=>v.toFixed(2)), bb.max.toArray().map(v=>v.toFixed(2)));
  // fingers: are there any finger joints exposed?
  const hand = a.joints.wristL.children.find(c => c.isGroup);
  console.log('hand children groups', hand.children.filter(c => c.isGroup).length, 'joint keys', Object.keys(a.joints).join(','));
}
