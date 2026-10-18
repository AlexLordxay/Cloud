{
  const J = a.joints, Y = window.__HY !== undefined ? window.__HY : -0.15;
  for (const t of [0, 3]) { a.pose(t); a.group.updateMatrixWorld(true);
    console.log('HANDS t=' + t + ' ' + ['wristL', 'wristR', 'ankleL', 'ankleR', 'head'].map(k => {
      const off = k.startsWith('wrist') ? [0, Y, 0] : [0, 0, 0];
      return k + ' ' + J[k].localToWorld(new THREE.Vector3(...off)).toArray().map(x => x.toFixed(3)).join(','); }).join(' | ')); }
}
