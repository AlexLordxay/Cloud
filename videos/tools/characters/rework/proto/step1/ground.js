// the survive stand() pose and the Venus kneel pose (kneel = 1), and the figure's lowest point for each
{
  const J = a.joints;
  const setJ = (J, p) => { for (const k in p) J[k].rotation.set(...p[k]); };
  const stand = (t) => ({
    body: [0.02, 0, 0], head: [-0.05 + 0.02 * Math.sin(t * 0.7), 0.06 * Math.sin(t * 0.5), 0],
    shoulderL: [0.08, 0, -0.22], shoulderR: [0.08, 0, 0.22], elbowL: [0.35, 0, 0], elbowR: [0.35, 0, 0],
    wristL: [0.1, 0, 0], wristR: [0.1, 0, 0],
    hipL: [0.04, 0, -0.06], hipR: [0.04, 0, 0.06], kneeL: [-0.08, 0, 0], kneeR: [-0.08, 0, 0], ankleL: [0.04, 0, 0], ankleR: [0.04, 0, 0],
  });
  const mix = (p, q, k) => { const o = {}; for (const key in p) o[key] = p[key].map((v, i) => v + ((q[key] || p[key])[i] - v) * k); return o; };
  const minY = () => { a.group.position.y = 0; a.group.updateMatrixWorld(true); return new THREE.Box3().setFromObject(a.group).min.y; };
  const res = {};
  for (const lt of [2, 4, 6]) {
    a.pose(lt * 0.6); setJ(J, stand(lt)); res['stand' + lt] = minY();
    const kneel = Math.min(1, Math.max(0, (lt - 2.6) / 1.4)) >= 1 ? 1 : 1;
    a.pose(lt * 0.6);
    setJ(J, mix(mix(stand(lt), { head: [0.25, -0.3, 0], shoulderL: [0.6, 0, -0.5], elbowL: [1.8, 0, 0] }, 1),
      { body: [-0.55 - 0.3 * Math.min(1, Math.max(0, (lt - 4.2) / 1.5)), 0, 0.05], head: [0.35, 0, 0], shoulderL: [1.05, 0, -0.2], shoulderR: [1.05, 0, 0.2], elbowL: [0.2, 0, 0], elbowR: [0.2, 0, 0],
        hipL: [0.65, 0, -0.1], hipR: [0.65, 0, 0.1], kneeL: [-1.6, 0, 0], kneeR: [-1.6, 0, 0], ankleL: [0.6, 0, 0], ankleR: [0.6, 0, 0] }, kneel));
    res['kneel' + lt] = minY();
  }
  a.pose(0); res.idle0 = minY();
  const isB = Object.keys(J).map(k => k + ':' + (J[k].isBone ? 'B' : 'G')).join(' ');
  console.log('GROUND ' + JSON.stringify(res));
  console.log('JOINTS ' + Object.keys(J).length + ' ' + isB);
  let v = 0, n = 0; a.group.traverse(o => { if (o.isMesh && o.geometry && o.geometry.attributes.position) { v += o.geometry.attributes.position.count; n++; } });
  console.log('VERTS ' + v + ' meshes ' + n);
  const bw = new THREE.Vector3(); a.pose(0); a.group.updateMatrixWorld(true);
  console.log('HANDS ' + ['wristL','wristR'].map(k => J[k].localToWorld(new THREE.Vector3(0, window.__handY || -0.075, 0)).toArray().map(x => x.toFixed(3)).join(',')).join(' | '));
}
