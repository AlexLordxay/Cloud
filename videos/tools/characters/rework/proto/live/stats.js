{
  const V = () => new THREE.Vector3();
  const rec = [];
  const dt = 1 / 30;
  for (let i = 0; i <= 30 * 24; i++) {
    const t = i * dt; a.pose(t); a.group.updateMatrixWorld(true);
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
  a.pose(0); a.group.updateMatrixWorld(true);
  const hl = a.joints.wristL.localToWorld(new THREE.Vector3(0, -0.15, 0)), hr = a.joints.wristR.localToWorld(new THREE.Vector3(0, -0.15, 0));
  console.log('t0 hand L', hl.toArray().map(v=>v.toFixed(2)), 'hand R', hr.toArray().map(v=>v.toFixed(2)), 'head', a.joints.head.getWorldPosition(V()).toArray().map(v=>v.toFixed(2)));
  const bb = new THREE.Box3().setFromObject(a.group); console.log('bbox', bb.min.toArray().map(v=>v.toFixed(2)), bb.max.toArray().map(v=>v.toFixed(2)));
  // fingers: are there any finger joints exposed?
  const hand = a.joints.wristL.children.find(c => c.isGroup);
  console.log('hand children groups', hand.children.filter(c => c.isGroup).length, 'joint keys', Object.keys(a.joints).join(','));
}
