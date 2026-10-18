// Prototype (critic's proof of concept, not production): a skinned EVA glove built in code for three r147.
// Runs inside handview.js's page after a.pose(t). Replaces the old hand group under each wrist joint.
// Hand frame: fingers along -y, palm faces -z, thumb on the s*x side (same as the current model).
const T = THREE;
const gloveMat = a.materials.find(m => m.color && m.color.getHex() === 0xa3acba);
const rubberMat = a.materials.find(m => m.color && m.color.getHex() === 0x1d3f86);
const sstep = (e0, e1, x) => { const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0))); return t * t * (3 - 2 * t); };
const G2 = (dx, dy, sx, sy) => Math.exp(-((dx / sx) ** 2 + (dy / sy) ** 2));
const TEX = 0.5;   // metres of surface per texture repeat, as on the sleeves (so the weave has the same scale)

// One finger: a tapered tube along local -y, closed by a rounded tip, skinned to [palm, b1, b2, b3].
// L: phalanx lengths (the last includes the rounded tip); R: radius at MCP, PIP, DIP, and at the tip.
function fingerGeo(L, R, opts = {}) {
  R = R.map(r => r * (opts.k || 1.15)); const seg = 22, J = [0, L[0], L[0] + L[1]], Lt = L[0] + L[1] + L[2], u0 = -(opts.inside || 1.6) * R[0];
  const rTip = R[3], uCap = Lt - rTip;
  const rad = u => {   // radius along the finger: a taper through the joints, a little fuller over each joint (cloth bunching)
    let r;
    if (u <= 0) r = R[0]; else if (u < J[1]) r = R[0] + (R[1] - R[0]) * u / J[1];
    else if (u < J[2]) r = R[1] + (R[2] - R[1]) * (u - J[1]) / L[1]; else r = R[2] + (R[3] - R[2]) * Math.min(1, (u - J[2]) / (uCap - J[2]));
    return r * (1 + 0.06 * Math.exp(-(((u - J[1]) / (0.5 * R[1])) ** 2)) + 0.05 * Math.exp(-(((u - J[2]) / (0.5 * R[2])) ** 2)));
  };
  const us = []; const nBody = 44; for (let i = 0; i <= nBody; i++) us.push([u0 + (uCap - u0) * i / nBody, 1]);
  for (let i = 1; i <= 10; i++) { const th = i / 10 * Math.PI / 2; us.push([uCap + rTip * Math.sin(th), Math.cos(th)]); }
  const pos = [], uv = [], si = [], sw = [], uvals = [];
  let arc = 0, prevU = us[0][0];
  for (const [u, k] of us) {
    const r = (k === 1 ? rad(u) : rTip * k); arc += Math.abs(u - prevU); prevU = u;
    for (let j = 0; j <= seg; j++) {
      const ph = j / seg * Math.PI * 2, c = Math.cos(ph), sn = Math.sin(ph);
      const zf = sn < 0 ? 0.84 : 0.94;                         // flatter on the palm side (finger pads), rounder on the back
      const pad = sn < 0 && k < 1 ? 1 + 0.12 * (1 - k) : 1;    // the fingertip pad pushes out a little on the palm side
      pos.push(r * c, -u, r * sn * zf * pad);
      uv.push(ph * R[0] / TEX, arc / TEX);
      uvals.push([u, sn]);
      // skin weights: rigid inside each phalanx, a smooth blend across each joint (half-width ~ half a radius)
      const bones = [0, 1, 2, 3], jp = [0, J[1], J[2]];
      let a0 = 0, a1 = 0, w1 = 1;
      let seg_ = u < 0 ? 0 : u < J[1] ? 1 : u < J[2] ? 2 : 3;
      a0 = seg_; a1 = seg_; w1 = 0;
      for (let q = 0; q < 3; q++) { const h = (q === 0 ? 1.1 : 0.75) * R[q]; if (Math.abs(u - jp[q]) < h) { a0 = q; a1 = q + 1; w1 = sstep(-h, h, u - jp[q]); } }
      si.push(bones[a0], bones[a1], 0, 0); sw.push(1 - w1, w1, 0, 0);
    }
  }
  const rows = us.length, idxG = [], idxR = [];
  const capStart = J[2] + 0.5 * L[2];
  for (let i = 0; i < rows - 1; i++) for (let j = 0; j < seg; j++) {
    const A = i * (seg + 1) + j, B = A + seg + 1, C = A + 1, D = B + 1;
    const [u, sn] = uvals[A];
    // the rubber cap: a thimble cut obliquely, reaching further down on the pad side than on the back
    const rubber = opts.rubber !== false && u > capStart - 0.0005;
    (rubber ? idxR : idxG).push(A, B, C, C, B, D);
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  g.setAttribute('skinIndex', new T.Uint16BufferAttribute(si, 4));
  g.setAttribute('skinWeight', new T.Float32BufferAttribute(sw, 4));
  g.setIndex(idxG.concat(idxR)); g.addGroup(0, idxG.length, 0); g.addGroup(idxG.length, idxR.length, 1);
  g.computeVertexNormals();
  return { g, J };
}

// The palm: a rounded slab (a superellipsoid), flatter on the palm side, with a thenar and a hypothenar pad,
// a shallow hollow in the middle, knuckle bumps on the back and the knuckle line as an arc.
function palmGeo(s, mcps) {
  const g = new T.SphereGeometry(1, 56, 40), p = g.attributes.position, e = 0.7;
  const sp = v => Math.sign(v) * Math.pow(Math.abs(v), e);
  for (let i = 0; i < p.count; i++) {
    const X = sp(p.getX(i)), Y = sp(p.getY(i)), Z = sp(p.getZ(i));
    const top = 0.012, t = (1 - Y) / 2;                                    // 0 at the wrist, 1 at the knuckles
    let x = X * (0.046 + 0.007 * t);
    const bottom = -0.1 + 4.0 * x * x - (Z < 0 ? 0.014 * (-Z) : 0);                                     // the knuckle line: an arc, the middle finger's lowest
    let y = top + (bottom - top) * t;
    let z = Z * (Z < 0 ? 0.021 : 0.024) * (1 - 0.25 * Math.max(0, t - 0.8) / 0.2);
    if (Z < 0) {                                                            // the palm side
      z -= 0.011 * G2(x - s * 0.027, y + 0.038, 0.02, 0.03) * (-Z);         // thenar pad (ball of the thumb)
      z -= 0.006 * G2(x + s * 0.03, y + 0.06, 0.014, 0.032) * (-Z);         // hypothenar pad
      z -= 0.004 * G2(x, y + 0.092, 0.05, 0.008) * (-Z);                    // the pad row under the fingers
      z += 0.004 * G2(x, y + 0.062, 0.02, 0.022) * (-Z);                    // a shallow hollow in the middle
    } else for (const m of mcps) z += 0.0035 * G2(x - m.x, y - m.y - 0.004, 0.008, 0.012) * Z;   // knuckles on the back
    p.setXYZ(i, x, y, z);
  }
  const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 0.3 / TEX, uv.getY(i) * 0.13 / TEX);
  g.computeVertexNormals(); return g;
}

const FING = [   // name, MCP x (times s), MCP y, fan (times s), phalanx lengths, radii [MCP, PIP, DIP, tip]
  ['index', 0.0335, -0.098, 0.07, [0.044, 0.026, 0.023], [0.0112, 0.0102, 0.0094, 0.0088]],
  ['middle', 0.011, -0.1045, 0.015, [0.048, 0.029, 0.024], [0.0116, 0.0106, 0.0097, 0.009]],
  ['ring', -0.0125, -0.1015, -0.04, [0.045, 0.028, 0.023], [0.011, 0.0101, 0.0093, 0.0087]],
  ['little', -0.034, -0.0925, -0.1, [0.035, 0.021, 0.02], [0.0098, 0.009, 0.0083, 0.0078]],
];
window.GL = {};
for (const side of ['L', 'R']) {
  const s = side === 'L' ? -1 : 1, wr = a.joints['wrist' + side];
  const old = wr.children.find(c => c.isGroup); old.visible = false;
  const hand = new T.Group(); hand.position.set(0, -0.085, 0); wr.add(hand);
  const mcps = FING.map(f => ({ x: s * f[1], y: f[2] }));
  const palm = new T.Mesh(palmGeo(s, mcps), gloveMat); hand.add(palm);
  a.group.updateMatrixWorld(true);
  const H = { hand, fingers: [], thumb: null };
  for (const [name, mx, my, fan, L, R] of FING) {
    const root = new T.Group(); root.position.set(s * mx, my + 0.004, 0.001); root.rotation.z = s * fan; hand.add(root);
    const b1 = new T.Bone(), b2 = new T.Bone(), b3 = new T.Bone();
    root.add(b1); b2.position.y = -L[0]; b1.add(b2); b3.position.y = -L[1]; b2.add(b3);
    const { g } = fingerGeo(L, R);
    const m = new T.SkinnedMesh(g, [gloveMat, rubberMat]); root.add(m);
    a.group.updateMatrixWorld(true);
    m.bind(new T.Skeleton([hand, b1, b2, b3]));
    m.frustumCulled = false; m.castShadow = m.receiveShadow = true;
    H.fingers.push({ name, root, b: [b1, b2, b3], fan });
  }
  // the thumb: from inside the thenar pad, pointing down, out and forward, turned on its own axis so its pad
  // faces the fingers (opposition); three bones: metacarpal (CMC), proximal (MCP), distal (IP)
  {
    const root = new T.Group(); root.position.set(s * 0.026, -0.02, -0.006); hand.add(root);
    const d = new T.Vector3(s * 0.5, -0.78, -0.38).normalize();            // where the thumb points at rest
    const pad = new T.Vector3(-s * 0.8, -0.1, -0.55).normalize();            // where its pad faces (across the palm)
    const yA = d.clone().negate(), zA = pad.clone().negate().addScaledVector(yA, pad.dot(yA)).normalize(), xA = new T.Vector3().crossVectors(yA, zA);
    root.quaternion.setFromRotationMatrix(new T.Matrix4().makeBasis(xA, yA, zA));
    const L = [0.042, 0.032, 0.03], R = [0.0165, 0.0128, 0.0118, 0.0108];
    const b1 = new T.Bone(), b2 = new T.Bone(), b3 = new T.Bone();
    root.add(b1); b2.position.y = -L[0]; b1.add(b2); b3.position.y = -L[1]; b2.add(b3);
    const { g } = fingerGeo(L, R, { inside: 0.8, k: 1.0 });
    const m = new T.SkinnedMesh(g, [gloveMat, rubberMat]); root.add(m);
    a.group.updateMatrixWorld(true);
    m.bind(new T.Skeleton([hand, b1, b2, b3]));
    m.frustumCulled = false; m.castShadow = m.receiveShadow = true;
    H.thumb = { root, b: [b1, b2, b3] };
  }
  window.GL[side] = H;
  F[side].hand = hand;
}
// Hand shapes: per finger [MCP, PIP, DIP] flexion (+x curls toward the palm), spread multiplier; thumb [CMC flex, CMC abd, MCP, IP]
const SHAPES = {
  relaxed: { f: [[0.3, 0.45, 0.25], [0.4, 0.55, 0.3], [0.5, 0.65, 0.35], [0.6, 0.75, 0.4]], spread: 1, th: [0.15, 0.0, 0.15, 0.2] },
  open: { f: [[0.02, 0.03, 0.02], [0.02, 0.03, 0.02], [0.02, 0.03, 0.02], [0.02, 0.03, 0.02]], spread: 1.6, th: [-0.25, 0.45, 0.0, 0.05] },
  fist: { f: [[1.35, 1.55, 0.7], [1.4, 1.6, 0.7], [1.4, 1.6, 0.7], [1.35, 1.55, 0.7]], spread: 0.2, th: [0.5, -0.1, 0.45, 0.45] },
  point: { f: [[0.05, 0.05, 0.03], [1.4, 1.6, 0.7], [1.4, 1.6, 0.7], [1.35, 1.55, 0.7]], spread: 0.5, th: [0.5, -0.1, 0.45, 0.45] },
  thumbsUp: { f: [[1.35, 1.55, 0.7], [1.4, 1.6, 0.7], [1.4, 1.6, 0.7], [1.35, 1.55, 0.7]], spread: 0.2, th: [-0.35, 0.35, -0.1, 0.0] },
};
window.setHand = (side, name) => {
  const H = GL[side], S = SHAPES[name], s = side === 'L' ? -1 : 1;
  H.fingers.forEach((f, i) => { f.root.rotation.z = s * f.fan * S.spread; f.b.forEach((b, k) => b.rotation.x = S.f[i][k]); });
  const t = H.thumb.b; t[0].rotation.set(S.th[0], 0, S.th[1]); t[1].rotation.x = S.th[2]; t[2].rotation.x = S.th[3];
};
