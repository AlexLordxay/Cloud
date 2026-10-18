{
  const clamp = x => Math.min(1, Math.max(0, x)), smooth = x => { x = clamp(x); return x * x * (3 - 2 * x); };
  const J = a.joints;
  const setJ = (J, p) => { for (const k in p) J[k].rotation.set(...p[k]); };
  const stand = (t, s = 1) => ({
    body: [0.02, 0, 0], head: [-0.05 + 0.02 * Math.sin(t * 0.7), 0.06 * Math.sin(t * 0.5), 0],
    shoulderL: [0.08, 0, -0.22], shoulderR: [0.08, 0, 0.22], elbowL: [0.35, 0, 0], elbowR: [0.35, 0, 0],
    wristL: [0.1, 0, 0], wristR: [0.1, 0, 0],
    hipL: [0.04, 0, -0.06], hipR: [0.04, 0, 0.06], kneeL: [-0.08, 0, 0], kneeR: [-0.08, 0, 0], ankleL: [0.04, 0, 0], ankleR: [0.04, 0, 0],
  });
  const mix = (p, q, k) => { const o = {}; for (const key in p) o[key] = p[key].map((v, i) => v + ((q[key] || p[key])[i] - v) * k); return o; };
  const minY = () => { a.group.position.y = 0; a.group.updateMatrixWorld(true); return new THREE.Box3().setFromObject(a.group).min.y; };
  const out = {};
  a.pose(1.2); setJ(J, stand(2)); out.stand = minY();
  const lt = 6, kneel = 1;
  a.pose(3.6);
  setJ(J, mix(mix(stand(lt), { head: [0.25, -0.3, 0], shoulderL: [0.6, 0, -0.5], elbowL: [1.8, 0, 0] }, smooth((lt - 1.6) / 0.6)),
    { body: [-0.55 - 0.3 * smooth((lt - 4.2) / 1.5), 0, 0.05], head: [0.35, 0, 0], shoulderL: [1.05, 0, -0.2], shoulderR: [1.05, 0, 0.2], elbowL: [0.2, 0, 0], elbowR: [0.2, 0, 0],
      hipL: [0.65, 0, -0.1], hipR: [0.65, 0, 0.1], kneeL: [-1.6, 0, 0], kneeR: [-1.6, 0, 0], ankleL: [0.6, 0, 0], ankleR: [0.6, 0, 0] }, kneel));
  out.kneel = minY();
  // the lowest rendered point (skinning aware): the sole meshes and the lowest skinned vertex
  const v = new THREE.Vector3(); let lowSole = 1e9, lowSkin = 1e9, lowRigid = 1e9;
  a.group.traverse(m => { if (!m.isMesh || !m.visible) return; const p = m.geometry.attributes.position; if (!p) return;
    for (let i = 0; i < p.count; i += 1) { v.fromBufferAttribute(p, i); if (m.isSkinnedMesh) { m.boneTransform(i, v); v.applyMatrix4(m.matrixWorld); lowSkin = Math.min(lowSkin, v.y); } else { v.applyMatrix4(m.matrixWorld); lowRigid = Math.min(lowRigid, v.y); } } });
  out.kneelRenderedRigid = lowRigid; out.kneelRenderedSkin = lowSkin;
  out.isBone = Object.keys(J).map(k => k + ':' + !!J[k].isBone).join(',');
  out.keys = Object.keys(J).length;
  let nv = 0; a.group.traverse(m => { if (m.isMesh && m.visible) nv += m.geometry.attributes.position.count; }); out.verts = nv;
  console.log('GROUND ' + JSON.stringify(out));
}
