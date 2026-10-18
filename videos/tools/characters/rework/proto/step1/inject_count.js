{
  const rows = [];
  a.group.traverse(m => { if (m.isMesh && m.visible) rows.push([m.geometry.type, m.geometry.attributes.position.count, m.parent === a.joints.body ? 'body' : (Object.keys(a.joints).find(k => a.joints[k] === m.parent) || '-')]); });
  const by = {}; rows.forEach(([t, n]) => { by[t] = (by[t] || 0) + n; });
  console.log('COUNT ' + JSON.stringify(by) + ' total ' + rows.reduce((s, r) => s + r[1], 0) + ' meshes ' + rows.length);
  console.log('BIG ' + JSON.stringify(rows.sort((x, y) => y[1] - x[1]).slice(0, 12)));
}
