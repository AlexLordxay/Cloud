// The Nebozvid astronaut: a character built in code (three.js), so any video can use it (scene.json:
// "include": ["characters/astronaut.js"]). Modelled after real spacewalk suits: a hard upper torso, a big life-support
// backpack with rounded edges, puffy fabric arms and legs with bellows at the elbows and knees, bearings at the
// shoulders, waist and wrists, gloves with fingers, heavy boots, a helmet with side lamps and a gold visor, hoses to a
// control box on the chest, and a small Ukrainian flag on the left shoulder. The fabric has folds in its shape and a woven,
// stitched texture (a canvas drawn in code); metal and the visor reflect an environment map; the figure shades itself (shadow map).
//
//   const a = window.__makeAstronaut(THREE);         // a.group: ~1.9 units tall, pelvis at the origin, facing -z
//   await a.ready;                                    // the emblem picture has loaded
//   a.pose(t);                                        // the free-fall idle at time t (s): limbs drift slowly
//   a.setTint(r, g, b); a.setOpacity(x);              // colour and fade for the whole figure
//   a.rim.color.value.set(…)                          // rim light on the edges (light from behind the figure)
//   const env = window.__astronautEnv(THREE, renderer, { warm: dirVector });   // reflections: dark space, a warm glow
//   scene.add(a.light(color, intensity, dir)); a.aim();   // shadow-casting lights that follow the figure (aim each frame)
//
// Joints are bones of one skeleton (a.joints.shoulderL, elbowL, wristL, hipL, kneeL, ankleL, … head, body): the arms and
// legs are each one skinned sleeve that bends smoothly at the joints, with bellows folding on the inside of a bend.
(() => {
  window.__makeAstronaut = (THREE) => {
    const mats = [];
    const rim = { color: { value: new THREE.Color(0, 0, 0) }, power: { value: 3.0 } };
    const M = (o) => {
      const m = new THREE.MeshStandardMaterial(o);
      m.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { rimColor: rim.color, rimPower: rim.power });
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform vec3 rimColor; uniform float rimPower;').replace('#include <dithering_fragment>',
          '#include <dithering_fragment>\n  float fr = pow(1.0 - clamp(dot(normalize(vNormal), normalize(vViewPosition)), 0.0, 1.0), rimPower);\n  gl_FragColor.rgb += rimColor * diffuseColor.rgb * fr;');
      };
      m.userData.base = m.color.clone(); mats.push(m); return m;
    };
    // real cloth is never a perfect solid of revolution: push the surface in and out along its normal with smooth noise
    const vh = (x, y, z) => { const v = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return v - Math.floor(v); };
    function vnoise(x, y, z) {
      const X = Math.floor(x), Y = Math.floor(y), Z = Math.floor(z), fx = x - X, fy = y - Y, fz = z - Z;
      const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy), w = fz * fz * (3 - 2 * fz), L = (a, b, k) => a + (b - a) * k;
      return L(L(L(vh(X, Y, Z), vh(X + 1, Y, Z), u), L(vh(X, Y + 1, Z), vh(X + 1, Y + 1, Z), u), v),
               L(L(vh(X, Y, Z + 1), vh(X + 1, Y, Z + 1), u), L(vh(X, Y + 1, Z + 1), vh(X + 1, Y + 1, Z + 1), u), v), w);
    }
    // Cloth texture, drawn once on a canvas: a fine weave, faint blotches of wear, and seams with stitches running along
    // the limbs (on lathe-made parts u goes round the limb and v along it, so a seam is a vertical line on the canvas).
    // The same picture, greyed, is the bump map: the weave and the seams catch the light.
    function clothTexture(seams) {
      const N = 1024, cv = document.createElement('canvas'); cv.width = cv.height = N;
      const g = cv.getContext('2d'), img = g.createImageData(N, N), d = img.data;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const weave = ((x >> 1) + (y >> 1)) % 2 ? 6 : -6, grain = (vh(x, y, 1) - 0.5) * 14;
        const wear = (vnoise(x / 90, y / 90, 3) - 0.5) * 22 + (vnoise(x / 23, y / 23, 7) - 0.5) * 8;
        const v = 236 + weave + grain + wear, i = (y * N + x) * 4;
        d[i] = v; d[i + 1] = v - 3; d[i + 2] = v - 9; d[i + 3] = 255;
      }
      g.putImageData(img, 0, 0);
      for (const u of seams) {
        const x = u * N;
        g.fillStyle = 'rgba(120,115,105,0.55)'; g.fillRect(x - 2, 0, 4, N);                         // the seam groove
        g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(x + 2, 0, 2, N);                         // its raised edge
        g.fillStyle = 'rgba(95,90,82,0.7)';
        for (let y = 0; y < N; y += 14) { g.fillRect(x - 9, y, 2, 7); g.fillRect(x + 8, y + 5, 2, 7); }   // stitches
      }
      const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.encoding = THREE.sRGBEncoding;
      const bc = document.createElement('canvas'); bc.width = bc.height = N; const bg = bc.getContext('2d'); bg.filter = 'blur(2px)'; bg.drawImage(cv, 0, 0);
      const b = new THREE.CanvasTexture(bc); b.wrapS = b.wrapT = THREE.RepeatWrapping; b.anisotropy = 8;
      return [t, b];
    }
    const [clothMap, clothBump] = clothTexture([0.25, 0.75]);
    const [plainMap, plainBump] = clothTexture([]);
    const fabric = M({ color: 0xf2eee6, roughness: 0.95, metalness: 0, map: clothMap, bumpMap: clothBump, bumpScale: 0.05 });
    const fabric2 = M({ color: 0xdedad0, roughness: 0.95, metalness: 0, map: plainMap, bumpMap: plainBump, bumpScale: 0.07 });      // a shade darker: bellows, gaskets
    const torsoCloth = M({ color: 0xf2eee6, roughness: 0.93, metalness: 0, map: plainMap, bumpMap: plainBump, bumpScale: 0.035 });   // the cloth over the hard torso: the same as the sleeves
    const cover = M({ color: 0xece8de, roughness: 0.92, metalness: 0, map: plainMap, bumpMap: plainBump, bumpScale: 0.04 });        // the cloth cover over the backpack
    const shell = M({ color: 0xeceae3, roughness: 0.6, metalness: 0.0 });          // hard parts
    const metal = M({ color: 0xc3c7cc, roughness: 0.28, metalness: 0.85 });          // bearings, valves
    const grey = M({ color: 0x6d7076, roughness: 0.6, metalness: 0.2 });
    const dark = M({ color: 0x26282c, roughness: 0.75, metalness: 0.1 });
    // the visor: gold film under a clear glossy coat (physical material), so it mirrors the light like real glass
    const visor = new THREE.MeshPhysicalMaterial({ color: 0xd9a043, metalness: 1.0, roughness: 0.06, clearcoat: 1.0, clearcoatRoughness: 0.02, envMapIntensity: 1.4 });
    visor.userData.base = visor.color.clone(); mats.push(visor);
    const gasket = M({ color: 0x2c2e33, roughness: 0.7, metalness: 0.1 });
    const lens = M({ color: 0x111316, roughness: 0.1, metalness: 0.6 });
    const blue = M({ color: 0x0057b7, roughness: 0.85 }), yellow = M({ color: 0xffd500, roughness: 0.85 }), white = M({ color: 0xf4f2ec, roughness: 0.85 });
    // the colour details (after the Apollo-era suits): silver-grey gloves with blue rubber fingertips, beige straps,
    // blue and red wrist stripes, striped hoses
    const glove = M({ color: 0xa3acba, roughness: 0.72, metalness: 0.08, map: plainMap, bumpMap: plainBump, bumpScale: 0.05 });
    const rubber = M({ color: 0x1d3f86, roughness: 0.5 }), strap = M({ color: 0xb4955f, roughness: 0.85 });
    const connBlue = M({ color: 0x1f4c9e, roughness: 0.4, metalness: 0.3 }), connRed = M({ color: 0xb02a22, roughness: 0.4, metalness: 0.3 });
    const hoseMat = (() => {
      const cv = document.createElement('canvas'); cv.width = 64; cv.height = 8; const g = cv.getContext('2d');
      g.fillStyle = '#efece6'; g.fillRect(0, 0, 64, 8); g.fillStyle = '#3a3d44'; g.fillRect(40, 0, 14, 8);
      const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(26, 1); t.encoding = THREE.sRGBEncoding;
      return M({ map: t, roughness: 0.6 });
    })();

    const at = (m, x, y, z) => { m.position.set(x, y, z); return m; };
    const mesh = (geo, mat, x = 0, y = 0, z = 0) => at(new THREE.Mesh(geo, mat), x, y, z);
    const joint = (parent, x, y, z) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };
    const lathe = (prof, seg = 48) => new THREE.LatheGeometry(prof.map(([r, y]) => new THREE.Vector2(Math.max(r, 1e-4), y)), seg);
    const ringX = (R, r, mat) => { const m = new THREE.Mesh(new THREE.TorusGeometry(R, r, 14, 48), mat); m.rotation.y = Math.PI / 2; return m; };   // axis along x
    const ringY = (R, r, mat) => { const m = new THREE.Mesh(new THREE.TorusGeometry(R, r, 14, 48), mat); m.rotation.x = Math.PI / 2; return m; };   // axis along y
    // a box with rounded edges (an extruded rounded rectangle, bevelled), centred
    function rbox(w, h, d, r) {
      const s = new THREE.Shape(), x = -w / 2 + r, y = -h / 2 + r, W = w - 2 * r, H = h - 2 * r;
      s.moveTo(x, y - r); s.lineTo(x + W, y - r); s.quadraticCurveTo(x + W + r, y - r, x + W + r, y);
      s.lineTo(x + W + r, y + H); s.quadraticCurveTo(x + W + r, y + H + r, x + W, y + H + r);
      s.lineTo(x, y + H + r); s.quadraticCurveTo(x - r, y + H + r, x - r, y + H); s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
      const bv = Math.min(r, d / 2) * 0.9;
      const g = new THREE.ExtrudeGeometry(s, { depth: Math.max(1e-3, d - 2 * bv), bevelEnabled: true, bevelThickness: bv, bevelSize: bv * 0.9, bevelSegments: 5, curveSegments: 10 });
      g.translate(0, 0, -Math.max(1e-3, d - 2 * bv) / 2); g.computeVertexNormals(); return g;
    }
    let seed = 0;
    function lumpy(geo, amp, f = 14, weight = null) {
      geo.computeVertexNormals();
      const p = geo.attributes.position, n = geo.attributes.normal, o = (seed += 3.7);
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const d = (weight ? weight(x, y, z) : 1) * amp * ((vnoise(x * f + o, y * f * 2.2, z * f) - 0.5) * 1.4 + (vnoise(x * f * 2.6, y * f * 5 + o, z * f * 2.6) - 0.5) * 0.6);
        p.setXYZ(i, x + n.getX(i) * d, y + n.getY(i) * d, z + n.getZ(i) * d);
      }
      geo.computeVertexNormals(); return geo;
    }
    const shadowed = o => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });

    // ---- the rig ----
    // The joints are bones of one skeleton. Next to a joint sit helper bones that turn by a fixed share of its rotation
    // (computed while matrices update, so a scene can set the joints however it likes after pose()). A sleeve vertex in
    // a bend is spread over [parent, 1/3, 2/3, child] with cubic Bernstein weights: the bend becomes a smooth arc that
    // keeps the sleeve's thickness (a plain two-bone blend folds it flat like a hose).
    const bones = [], skinned = [], QI = new THREE.Quaternion();
    const bone = (p, x, y, z) => { const b = new THREE.Bone(); b.position.set(x, y, z); p.add(b); bones.push(b); return b; };
    const helper = (src, k, after) => { const h = bone(src.parent, src.position.x, src.position.y, src.position.z);
      h.updateMatrix = function () { this.quaternion.slerpQuaternions(QI, src.quaternion, k); if (after) after(src); THREE.Object3D.prototype.updateMatrix.call(this); }; return h; };
    const clamp01 = x => Math.min(1, Math.max(0, x)), sstep = (a, b, x) => { const t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); };
    const cubic = t => [(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3];
    // bellows ridges across a bend band |d| < B: three soft rings, fading out at the band's ends (0..1)
    const ridgeS = (d, B) => Math.abs(d) < B ? (0.5 + 0.5 * Math.cos(4 * Math.PI * d / B)) ** 2 * Math.sin(Math.PI * (d + B) / (2 * B)) : 0;
    // the cloth's own unevenness on the skinned sleeves (a radius offset at a rest-pose point): soft lumps and shallow
    // creases across the limb; calm (0..1) quiets it in the bends, where the bellows are
    const fold = (x, y, z, calm) => (1 - 0.6 * calm) * (0.0055 * ((vnoise(x * 14 + 3.1, y * 30, z * 14) - 0.5) * 1.4 + (vnoise(x * 36, y * 70 + 5.3, z * 36) - 0.5) * 0.6)
      - 0.0045 * Math.abs(Math.sin(y * 31 + 4 * x + 3 * z)) ** 6);
    const bandEnv = (d, B) => Math.abs(d) < B ? Math.sin(Math.PI * (d + B) / (2 * B)) : 0;
    // the sleeves' cloth: the seamed fabric, shaded per vertex (darker in the bellows' valleys and on the pads)
    const limbCloth = M({ color: 0xf2eee6, roughness: 0.95, metalness: 0, map: clothMap, bumpMap: clothBump, bumpScale: 0.05, vertexColors: true });
    // the row heights of a tube: spans [from, to, step] laid end to end
    const span = (...sp) => { const out = []; sp.forEach(([a, b, st], i) => { const n = Math.max(1, Math.round((a - b) / st)); for (let k = 0; k < n; k++) out.push(a + (b - a) * k / n); if (i === sp.length - 1) out.push(b); }); return out; };
    // A skinned tube in body space, built at rest (every limb hanging straight down, so a row is a horizontal slice).
    // rows: { y, cx, cz, r(phi), w(phi) -> up to 4 [bone, weight], col(phi), phi(j) }; a vertex is
    // (cx + r sin phi, y, cz + r cos phi), phi = 2 pi j / seg unless the row maps it; the seam column is doubled.
    // morphFn(row, phi, nx, ny, nz) -> how far to push that vertex along its normal in the corrective shape (morph 0).
    function skinTube(rows, seg, morphFn) {
      const N = seg + 1, pos = [], uv = [], col = [], si = [], sw = [], idx = [], phs = [];
      let v = 0, last = null;
      for (const rw of rows) {
        const ring = []; for (let j = 0; j <= seg; j++) { const ph = rw.phi ? rw.phi(j) : 2 * Math.PI * j / seg; ring.push([ph, rw.r(ph)]); }
        const mr = ring.reduce((a, q) => a + q[1], 0) / N;
        if (last) v += Math.hypot(last[0] - rw.y, last[1] - mr); last = [rw.y, mr];
        ring.forEach(([ph, r], j) => {
          pos.push(rw.cx + r * Math.sin(ph), rw.y, rw.cz + r * Math.cos(ph)); uv.push(j / seg, v / 0.45); phs.push(ph);
          const c = rw.col ? rw.col(ph) : 1; col.push(c, c, c);
          const w = rw.w(ph, r).filter(e => e[1] > 1e-5), tot = w.reduce((a, e) => a + e[1], 0);
          for (let k = 0; k < 4; k++) { si.push(w[k] ? bones.indexOf(w[k][0]) : 0); sw.push(w[k] ? w[k][1] / tot : 0); }
        });
      }
      for (let i = 0; i < rows.length - 1; i++) for (let j = 0; j < seg; j++) { const a = i * N + j, b = a + N; idx.push(a, b, a + 1, a + 1, b, b + 1); }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
      g.setIndex(idx); g.computeVertexNormals();
      const n = g.attributes.normal, t = new THREE.Vector3();
      rows.forEach((rw, i) => {   // one normal on both copies of the seam column; a row may correct its own (fixN)
        const a = i * N, b = a + seg; t.set(n.getX(a) + n.getX(b), n.getY(a) + n.getY(b), n.getZ(a) + n.getZ(b)).normalize();
        n.setXYZ(a, t.x, t.y, t.z); n.setXYZ(b, t.x, t.y, t.z);
        if (rw.fixN) rw.fixN(n, a);
      });
      if (morphFn) {
        const mo = [];
        rows.forEach((rw, i) => { for (let j = 0; j <= seg; j++) { const k = i * N + j, nx = n.getX(k), ny = n.getY(k), nz = n.getZ(k), d = morphFn(rw, phs[k], nx, ny, nz); mo.push(nx * d, ny * d, nz * d); } });
        g.morphAttributes.position = [new THREE.Float32BufferAttribute(mo, 3)]; g.morphTargetsRelative = true;
      }
      // Box3.setFromObject (survive's placeOnGround) reads the rest-pose box and ignores skinning: a tiny box here, and
      // invisible proxy boxes on the bones stand in for the limbs
      g.boundingBox = new THREE.Box3(new THREE.Vector3(-0.01, -0.01, -0.01), new THREE.Vector3(0.01, 0.01, 0.01));
      const m = new THREE.SkinnedMesh(g, limbCloth); m.frustumCulled = false; body.add(m); skinned.push(m); return m;
    }
    const proxyMat = new THREE.MeshBasicMaterial({ visible: false });
    const proxy = (p, w, h, d, y, z = 0) => { const m = mesh(new THREE.BoxGeometry(w, h, d), proxyMat, 0, y, z); m.visible = false; p.add(m); return m; };

    const group = new THREE.Group();
    const body = bone(group, 0, 0, 0);
    const J = { body };

    /* torso */
    // hard upper torso: a shell wider than deep, from the waist bearing to the neck ring
    const hut = mesh(lathe([[0, 0.06], [0.172, 0.06], [0.176, 0.1], [0.19, 0.17], [0.215, 0.27], [0.232, 0.38], [0.236, 0.46], [0.222, 0.53], [0.185, 0.585], [0.145, 0.615], [0, 0.625]], 64), torsoCloth);
    hut.scale.set(1.26, 1, 0.9); body.add(hut);
    // (the lower torso, the briefs, is the top of the two skinned pants halves: see the legs)
    // the waist: a soft band of the suit's own cloth over the bearing (no bare metal), the torso narrowing into it
    const waist = at(ringY(0.175, 0.015, grey), 0, 0.06, 0); waist.scale.set(1.26, 1, 0.9); body.add(waist);
    // chest control box with two hoses to the backpack
    const dcmMat = M({ color: 0x41464e, roughness: 0.45, metalness: 0.35 });                      // dark anthracite, so it reads as a device
    const dcm = mesh(rbox(0.3, 0.12, 0.11, 0.025), dcmMat, 0, 0.33, -0.25); dcm.rotation.x = 0.2; body.add(dcm);
    // its display: oxygen and suit pressure in small green digits on a dark screen (a canvas, self-lit)
    const screenTex = (() => {
      const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const g = cv.getContext('2d');
      g.fillStyle = '#05100c'; g.fillRect(0, 0, 256, 128);
      g.fillStyle = '#7dffb4'; g.font = 'bold 44px "DejaVu Sans Mono", monospace'; g.textBaseline = 'middle';
      g.fillText('O\u2082 98%', 14, 38);
      g.font = 'bold 34px "DejaVu Sans Mono", monospace'; g.fillStyle = '#6fe6ff'; g.fillText('4.3 PSI', 14, 92);
      g.fillStyle = 'rgba(125,255,180,0.35)'; for (let k = 0; k < 6; k++) g.fillRect(200, 104 - k * 13, 40, 9);            // a little level bar
      g.fillStyle = '#7dffb4'; for (let k = 0; k < 5; k++) g.fillRect(200, 104 - k * 13, 40, 9);
      const t = new THREE.CanvasTexture(cv); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t;
    })();
    const scrMat = M({ color: 0x000000, emissive: 0xffffff, emissiveMap: screenTex, emissiveIntensity: 1.1, roughness: 0.15, metalness: 0 });
    dcm.add(mesh(rbox(0.1, 0.052, 0.004, 0.006), lens, 0.065, 0.012, -0.056));                          // the screen's dark frame
    const scr = mesh(new THREE.PlaneGeometry(0.09, 0.045), scrMat, 0.065, 0.012, -0.0585); scr.rotation.y = Math.PI; dcm.add(scr);
    for (const [x, y] of [[-0.11, 0.015], [-0.065, 0.015], [-0.02, 0.015]]) { const k = mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.02, 14), metal, x, 0.33 + y, -0.31); k.rotation.x = Math.PI / 2 + 0.2; body.add(k); }
    // Connector boxes sewn onto the torso, a striped hose from the control box into each. A box sits on a cloth patch
    // that lies on the surface (the torso at height y is an ellipse A × B); its nipple points up, the hose comes down onto it.
    function port(x, y, A, B, path) {
      const q = Math.sqrt(1 - (x / A) ** 2), zs = -B * q, ang = Math.atan(B * x / (A * A * q));
      const mount = joint(body, x, y, zs); mount.rotation.y = Math.PI - ang;                          // local +z = out of the suit
      mount.add(mesh(lumpy(rbox(0.07, 0.07, 0.01, 0.012), 0.0015, 20), cover, 0, 0, 0.002));          // the sewn-on patch
      mount.add(mesh(rbox(0.05, 0.05, 0.028, 0.008), grey, 0, 0, 0.018));                             // the connector box
      mount.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.017, 0.017, 0.016, 18), metal), 0, 0.03, 0.018));
      const top = new THREE.Vector3(0, 0.04, 0.018).applyMatrix4(new THREE.Matrix4().compose(mount.position, mount.quaternion, new THREE.Vector3(1, 1, 1)));
      body.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([...path(top), top]), 40, 0.014, 10, false), hoseMat));
    }
    for (const sd of [-1, 1]) {
      // two from the box's sides up into the upper chest, in front of the shoulders (clear of the arms)
      port(sd * 0.215, 0.42, 0.2948, 0.2106, t => [new THREE.Vector3(sd * 0.13, 0.32, -0.285), new THREE.Vector3(sd * 0.175, 0.37, -0.275), new THREE.Vector3(t.x * 0.97, t.y + 0.045, t.z - 0.03)]);
      // two down into the belly, just above the belt
      port(sd * 0.15, 0.11, 0.219, 0.157, t => [new THREE.Vector3(sd * 0.08, 0.29, -0.28), new THREE.Vector3(sd * 0.11, 0.22, -0.24), new THREE.Vector3(t.x * 0.97, t.y + 0.05, t.z - 0.025)]);
    }
    // the backpack's harness: beige straps over the shoulders down to the control box
    for (const sd of [-1, 1]) {
      const c = new THREE.CatmullRomCurve3([new THREE.Vector3(sd * 0.13, 0.5, 0.22), new THREE.Vector3(sd * 0.155, 0.6, 0.1), new THREE.Vector3(sd * 0.16, 0.6, -0.08), new THREE.Vector3(sd * 0.145, 0.5, -0.2), new THREE.Vector3(sd * 0.13, 0.4, -0.235)]);
      const st = new THREE.Mesh(new THREE.TubeGeometry(c, 40, 0.012, 8, false), strap); st.scale.set(1, 1, 1); body.add(st);
    }
    // a coiled safety tether on the right of the belt: it hangs from a D-ring on the belt, its hook clipped to a loop below
    { const X = 0.266, Z = -0.005;   // on the belt's side (the belt is 0.22 out there): the ring sits on it, the coil hangs just outside the suit
      const dr = at(new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.0048, 8, 20), metal), 0.24, 0.05, Z); body.add(dr);
      const pts = []; for (let k = 0; k <= 160; k++) { const a = k / 160 * Math.PI * 2 * 5; pts.push(new THREE.Vector3(X + Math.cos(a) * 0.022, 0.03 - k / 160 * 0.1, Z + Math.sin(a) * 0.022)); }
      body.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 480, 0.0052, 6, false), dark));
      const hook = at(new THREE.Mesh(new THREE.TorusGeometry(0.014, 0.0042, 8, 20, Math.PI * 1.6), metal), X, -0.085, Z); hook.rotation.y = 0; body.add(hook);
      const tab = mesh(rbox(0.03, 0.04, 0.03, 0.006), strap, 0.248, -0.1, Z); tab.rotation.y = Math.PI / 2; body.add(tab); }   // a cloth loop sewn on the suit

    /* life-support backpack (+z side) */
    const pack = joint(body, 0, 0.37, 0.25);
    const bend = (g, k) => { const p = g.attributes.position; for (let i = 0; i < p.count; i++) p.setZ(i, p.getZ(i) - k * p.getX(i) * p.getX(i) - 0.3 * k * p.getY(i) * p.getY(i)); g.computeVertexNormals(); return g; };
    pack.add(mesh(lumpy(bend(rbox(0.46, 0.56, 0.18, 0.06), 0.35), 0.004, 9), cover));
    pack.add(mesh(rbox(0.42, 0.11, 0.16, 0.04), shell, 0, 0.3, -0.005));                // top cover, a little set apart
    pack.add(mesh(new THREE.BoxGeometry(0.43, 0.01, 0.165), grey, 0, 0.245, 0));       // the seam under it
    pack.add(mesh(lumpy(bend(rbox(0.34, 0.28, 0.03, 0.03), 0.35), 0.003, 12), cover, 0, 0.0, 0.09));   // a padded flap on the back
    for (const s of [-1, 1]) pack.add(mesh(new THREE.BoxGeometry(0.028, 0.48, 0.01), grey, s * 0.14, -0.01, 0.106));   // straps over it
        pack.add(mesh(rbox(0.08, 0.05, 0.02, 0.008), grey, 0, -0.2, 0.1));
    for (const s of [-1, 1]) {
      const h = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.011, 10, 24, Math.PI), grey);   // handles on the top edges
      h.position.set(s * 0.15, 0.36, 0.0); h.scale.setScalar(0.85); pack.add(h);
      pack.add(mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.035, 16), metal, s * 0.16, -0.3, 0.0));    // valves underneath
      pack.add(mesh(new THREE.BoxGeometry(0.016, 0.4, 0.15), grey, s * 0.234, 0.0, 0.0));                  // side rails
    }

    /* neck ring, helmet with side lamps and the gold visor */
    const head = bone(body, 0, 0.625, -0.01); J.head = head;
    body.add(at(ringY(0.148, 0.026, metal), 0, 0.625, -0.01));   // the neck ring stays on the suit: only the helmet turns
    body.add(at(ringY(0.16, 0.012, grey), 0, 0.595, -0.01));
    // the helmet shell with the window cut out of it (triangles whose centre falls inside the window are dropped)
    const P0 = Math.PI * 1.13, PL = Math.PI * 0.74, T0 = Math.PI * 0.2, TL = Math.PI * 0.46;
    const shellGeo = (() => {
      const g = new THREE.SphereGeometry(0.188, 96, 64).toNonIndexed(), p = g.attributes.position, keep = [];
      const inWin = (x, y, z) => { const r = Math.hypot(x, y, z), th = Math.acos(y / r); let ph = Math.atan2(z, -x); if (ph < 0) ph += Math.PI * 2;
        return th > T0 && th < T0 + TL && ph > P0 && ph < P0 + PL; };
      for (let i = 0; i < p.count; i += 3) {
        const cx = (p.getX(i) + p.getX(i + 1) + p.getX(i + 2)) / 3, cy = (p.getY(i) + p.getY(i + 1) + p.getY(i + 2)) / 3, cz = (p.getZ(i) + p.getZ(i + 1) + p.getZ(i + 2)) / 3;
        if (!inWin(cx, cy, cz)) for (let k = 0; k < 3; k++) keep.push(p.getX(i + k), p.getY(i + k), p.getZ(i + k));
      }
      const out = new THREE.BufferGeometry(); out.setAttribute('position', new THREE.Float32BufferAttribute(keep, 3));
      const nrm = keep.map((v, i) => v / 0.188); out.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3)); return out;   // a sphere's normals are smooth: position / radius
    })();
    const helmet = mesh(shellGeo, shell, 0, 0.16, 0.0); helmet.scale.set(1, 1.03, 1.06); head.add(helmet);
    // the visor covers the front (-z) of the helmet: phi centred on 1.5π in three's sphere parametrisation
    // The visor sits recessed in the window cut in the shell; a thick dark rubber gasket lines the window's edge and
    // covers the depth between the shell and the glass.
    const vis = mesh(new THREE.SphereGeometry(0.177, 72, 48, P0 - 0.06, PL + 0.12, T0 - 0.05, TL + 0.1), visor, 0, 0.16, 0);   // set back inside the shell
    vis.scale.set(1, 1.03, 1.06); head.add(vis);
    {
      const pts = [], r = 0.1855, sp = (ph, th) => new THREE.Vector3(-r * Math.cos(ph) * Math.sin(th), r * Math.cos(th), r * Math.sin(ph) * Math.sin(th));
      const n = 24, e = 0.01;   // walk round the window's edge (a rectangle in angles), corners rounded by the curve
      for (let k = 0; k < n; k++) pts.push(sp(P0 + e + (PL - 2 * e) * k / n, T0 + e));
      for (let k = 0; k < n; k++) pts.push(sp(P0 + PL - e, T0 + e + (TL - 2 * e) * k / n));
      for (let k = 0; k < n; k++) pts.push(sp(P0 + PL - e - (PL - 2 * e) * k / n, T0 + TL - e));
      for (let k = 0; k < n; k++) pts.push(sp(P0 + e, T0 + TL - e - (TL - 2 * e) * k / n));
      const rim = mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 200, 0.0095, 12, true), gasket, 0, 0.16, 0);
      rim.scale.set(1, 1.03, 1.06); head.add(rim);
    }
    const brow = mesh(new THREE.SphereGeometry(0.195, 56, 20, Math.PI * 1.1, Math.PI * 0.8, Math.PI * 0.16, Math.PI * 0.05), shell, 0, 0.16, 0); brow.scale.set(1, 1.03, 1.06); head.add(brow);
    // Left of the helmet: a lamp — a cylinder on a bracket, a glowing lens with a soft halo, a row of small LEDs under it.
    // Right: a sensor/camera pod — a dark body, a big glass lens in a metal ring, a red indicator, a thin antenna.
    const glows = [];
    const glowTex = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d');
      const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,244,215,1)'); gr.addColorStop(0.25, 'rgba(255,236,200,0.45)'); gr.addColorStop(1, 'rgba(255,230,190,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(cv); })();
    const lampLight = M({ color: 0xfff6e6, emissive: 0xfff0d2, emissiveIntensity: 2.2, roughness: 0.2 });
    const ledMat = M({ color: 0xdff0ff, emissive: 0xcfe8ff, emissiveIntensity: 1.6, roughness: 0.3 });
    const redLed = M({ color: 0xff3a2a, emissive: 0xff2a1a, emissiveIntensity: 2.0, roughness: 0.3 });
    {
      const lamp = joint(head, -0.196, 0.19, -0.035);
      lamp.add(mesh(rbox(0.03, 0.05, 0.05, 0.008), grey, 0.012, -0.005, 0.02));                                         // bracket
      const body1 = mesh(new THREE.CylinderGeometry(0.03, 0.026, 0.12, 28), shell, -0.012, 0.0, -0.02); body1.rotation.x = Math.PI / 2; lamp.add(body1);
      const bezel = mesh(new THREE.TorusGeometry(0.029, 0.0055, 10, 28), metal, -0.012, 0.0, -0.081); lamp.add(bezel);
      const lensL = mesh(new THREE.CircleGeometry(0.025, 28), lampLight, -0.012, 0.0, -0.0815); lensL.rotation.y = Math.PI; lamp.add(lensL);
      for (let k = 0; k < 4; k++) lamp.add(mesh(new THREE.SphereGeometry(0.0045, 10, 8), ledMat, -0.012, -0.045, -0.05 + k * 0.016));   // LED row
      lamp.add(mesh(rbox(0.02, 0.014, 0.075, 0.004), grey, -0.012, -0.045, -0.026));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.85 }));
      halo.scale.setScalar(0.13); halo.position.set(-0.012, 0, -0.09); lamp.add(halo); glows.push(halo);
    }
    {
      const pod = joint(head, 0.192, 0.2, -0.03);
      pod.add(mesh(rbox(0.03, 0.05, 0.05, 0.008), grey, -0.012, -0.008, 0.02));                                         // bracket
      pod.add(mesh(rbox(0.05, 0.055, 0.09, 0.014), dcmMat, 0.01, 0, -0.01));                                              // dark body
      const ring = mesh(new THREE.TorusGeometry(0.019, 0.005, 10, 24), metal, 0.01, 0.002, -0.056); pod.add(ring);
      const glass = mesh(new THREE.SphereGeometry(0.017, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), lens, 0.01, 0.002, -0.056); glass.rotation.x = -Math.PI / 2; pod.add(glass);
      pod.add(mesh(new THREE.SphereGeometry(0.004, 10, 8), redLed, 0.03, 0.02, -0.055));                                    // a red "recording" light
      const ant = mesh(new THREE.CylinderGeometry(0.0022, 0.0022, 0.11, 6), metal, 0.022, 0.08, 0.02); pod.add(ant);
      pod.add(mesh(new THREE.SphereGeometry(0.0055, 10, 8), dark, 0.022, 0.136, 0.02));
    }

    // a cloth pocket with a flap and a press stud, lying on a limb's outside (local +z of the joint faces out)
    function pocket(parent, x, y, z, rotY, w, h, tilt = 0) {
      const pk = joint(parent, x, y, z); pk.rotation.set(tilt, rotY, 0);
      pk.add(mesh(lumpy(rbox(w, h, 0.022, 0.012), 0.002, 20), fabric2));
      pk.add(mesh(rbox(w + 0.004, h * 0.32, 0.026, 0.01), cover, 0, h * 0.4, 0.004));
      pk.add(mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.008, 12), metal, 0, h * 0.37, 0.02).rotateX(Math.PI / 2));
      return pk;
    }

    /* arms */
    // Each arm is one skinned sleeve from inside the torso's side to the wrist ring. Its root stays with the torso, the
    // shoulder band (cubic over the torso, two helpers and the shoulder) lets the arm swing out of it with no edge, and the
    // elbow band bends round with bellows on the inside and a pad over the back. The forearm ends in a gauntlet and the
    // hand turns below its lip at the wrist pivot.
    const EY = 0.05, EB = 0.09, ER = 0.082;   // the elbow pivot's height in the torso, the bend band's half-length, the radius
    const upperR = y => { const u = (0.47 - y) / 0.42; return 0.082 + 0.02 * Math.exp(-(((u - 0.2) / 0.18) ** 2)); };   // full where it leaves the torso
    const foreR = y => { const u = clamp01((EY - y) / 0.3); return (0.078 - 0.016 * u) * (1 + 0.05 * Math.sin(Math.PI * u)); };
    const armR = (s, y, ph) => {
      const d = y - EY, prof = upperR(y) + (foreR(y) - upperR(y)) * sstep(EB, -EB, d);
      const pm = Math.abs(d) < EB ? sstep(0.3, 0.75, Math.cos(ph)) * Math.exp(-((d / 0.06) ** 2)) : 0;   // the elbow pad, +z
      const base = prof * (1 + 0.1 * ridgeS(d, EB) * (1 - pm)) + ER * 0.2 * pm;
      return { r: base + fold(s * 0.25 + base * Math.sin(ph), y, base * Math.cos(ph), bandEnv(d, EB)), base, pm };
    };
    // the shade of the cloth in a bend: darker in the bellows' valleys, the pad a little darker too
    const bendCol = (d, B, pm) => { if (Math.abs(d) >= B) return 1; const env = Math.sin(Math.PI * (d + B) / (2 * B)), sh = (0.5 + 0.5 * Math.cos(4 * Math.PI * d / B)) ** 2;
      const c = 1 - env * (0.05 + 0.07 * (1 - sh)); return c + (0.92 - c) * pm * env; };
    // the corrective shape of a bend (morph 0, grows with the angle): cloth bunches on the inside, the outside stays full
    const bendMorph = (d, B, R, inside, ins, outs) => { const g = Math.exp(-((d / (0.9 * B)) ** 2)); return R * g * (0.22 * ins * ins + 0.1 * outs) + R * 0.035 * ridgeS(d, B) * ins; };
    const quad = t => [(1 - t) ** 2, 2 * t * (1 - t), t * t];
    const spread = (bs, ws) => bs.map((b, i) => [b, ws[i]]);
    // a flat patch bent round a limb of radius r (its local +z points out of the limb)
    const wrapPlane = (w, h, r) => { const g = new THREE.PlaneGeometry(w, h, 12, 1), p = g.attributes.position;
      for (let i = 0; i < p.count; i++) { const x = p.getX(i); p.setZ(i, -(r - Math.sqrt(r * r - x * x))); } g.computeVertexNormals(); return g; };
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const sh = bone(body, s * 0.25, 0.47, 0), el = bone(sh, 0, -0.42, 0), wr = bone(el, 0, -0.36, 0);
      let arm = null;
      const elH1 = helper(el, 1 / 3, src => { if (arm) arm.morphTargetInfluences[0] = sstep(0, 2.1, src.rotation.x); }), elH2 = helper(el, 2 / 3);
      // The shoulder is a ball joint: the sleeve turns with the arm as a whole, its open top (a ring round the pivot)
      // always inside a round shoulder cap of the suit, and it leaves the cap through a soft bearing ring.
      const rows = span([0.47, EY + EB, 0.007], [EY + EB, EY - EB, 0.0025], [EY - EB, -0.25, 0.008]).map(y => {
        const w = y > EY + EB ? [[sh, 1]] : y > EY - EB ? spread([sh, elH1, elH2, el], cubic((EY + EB - y) / (2 * EB))) : [[el, 1]];
        return { y, cx: s * 0.25, cz: 0, r: ph => armR(s, y, ph).r, w: () => w, col: ph => bendCol(y - EY, EB, armR(s, y, ph).pm) };
      });
      const cap = mesh(new THREE.SphereGeometry(0.112, 56, 40), torsoCloth, s * 0.25, 0.47, 0); body.add(cap);
      sh.add(at(ringY(0.097, 0.011, fabric2), 0, -0.058, 0));
      arm = skinTube(rows, 48, (rw, ph, nx, ny, nz) => bendMorph(rw.y - EY, EB, ER, 1, Math.max(0, -nz), Math.max(0, nz)));
      proxy(sh, 0.2, 0.42, 0.2, -0.21); proxy(el, 0.16, 0.32, 0.16, -0.16);
      if (s < 0) {   // the flag on the outside of the left upper arm, bent round the sleeve
        const r = armR(s, 0.47 - 0.265, 1.5 * Math.PI).base + 0.005, f = joint(sh, -(r + 0.002), -0.265, 0); f.rotation.y = -Math.PI / 2;
        f.add(mesh(wrapPlane(0.112, 0.08, r + 0.001), white, 0, 0, -0.001));
        f.add(mesh(wrapPlane(0.1, 0.034, r + 0.002), blue, 0, 0.017, 0), mesh(wrapPlane(0.1, 0.034, r + 0.002), yellow, 0, -0.017, 0));
      }
      if (s < 0) {   // the cuff checklist on the left forearm: a little book of cards on a strap
        const ck = joint(el, 0, -0.19, -(armR(s, EY - 0.19, Math.PI).base + 0.012)); ck.rotation.y = Math.PI;
        ck.add(mesh(rbox(0.085, 0.062, 0.018, 0.006), grey));
        for (let k = 0; k < 3; k++) ck.add(mesh(new THREE.BoxGeometry(0.075, 0.052, 0.002), white, 0, 0, 0.011 + k * 0.0025));
      }
      // the wrist disconnect: a dark ring with a coloured stripe (blue on the left, red on the right, as on real suits)
      el.add(at(ringY(0.064, 0.0105, metal), 0, -0.295, 0));                                   // a slim wrist ring, the sleeve's own width
      el.add(at(ringY(0.0655, 0.0042, s < 0 ? connBlue : connRed), 0, -0.306, 0));
      // the gauntlet: a flared cuff, open below, with a rolled lip; the hand turns under it
      el.add(mesh(lathe([[0.052, -0.349], [0.056, -0.345], [0.066, -0.334], [0.072, -0.318], [0.068, -0.303], [0.058, -0.29]], 48), glove));
      el.add(at(ringY(0.052, 0.0035, glove), 0, -0.349, 0));
      // the glove: a full palm with a plate on the back, jointed fingers with blue rubber tips. The wrist bone is the
      // palm's base; a ball at the pivot fills the gauntlet's opening at any wrist angle.
      const hand = wr;
      hand.add(mesh(new THREE.SphereGeometry(0.045, 32, 24), glove));
      // a rounded, padded hand: an ellipsoid palm with a fuller back, not a flat box
      const palm = mesh(lumpy(new THREE.SphereGeometry(1, 40, 30), 0.012, 3), glove, 0, -0.052, 0); palm.scale.set(0.058, 0.064, 0.04); hand.add(palm);
      const backH = mesh(new THREE.SphereGeometry(1, 32, 24), glove, 0, -0.06, 0.012); backH.scale.set(0.052, 0.05, 0.03); hand.add(backH);
      for (let i = 0; i < 4; i++) {
        const fg = joint(hand, (i - 1.5) * 0.025 * -s, -0.1, 0.004);
        fg.rotation.set(0.55 + 0.1 * i, 0, -s * (i - 1.5) * 0.06);                                    // a relaxed, half-closed hand
        const len = i === 1 || i === 2 ? 0.034 : 0.028, r = i === 3 ? 0.0145 : 0.0165;
        fg.add(mesh(new THREE.CapsuleGeometry(r, len, 8, 16), glove, 0, -len / 2 - 0.006, 0));
        const tip = joint(fg, 0, -len - 0.013, 0); tip.rotation.x = 0.7;
        tip.add(mesh(new THREE.CapsuleGeometry(r * 0.95, 0.018, 8, 16), glove, 0, -0.012, 0));
        tip.add(mesh(new THREE.SphereGeometry(r * 1.02, 16, 12, 0, Math.PI * 2, Math.PI * 0.25, Math.PI * 0.75), rubber, 0, -0.023, 0));   // blue rubber tip
      }
      const th = joint(hand, s * 0.052, -0.035, -0.016); th.rotation.set(0.5, 0, -s * 0.8);
      th.add(mesh(new THREE.CapsuleGeometry(0.018, 0.028, 8, 16), glove, 0, -0.026, 0));
      const tt = joint(th, 0, -0.05, 0); tt.rotation.x = 0.5;
      tt.add(mesh(new THREE.CapsuleGeometry(0.017, 0.014, 8, 16), glove, 0, -0.012, 0));
      tt.add(mesh(new THREE.SphereGeometry(0.0175, 16, 12, 0, Math.PI * 2, Math.PI * 0.25, Math.PI * 0.75), rubber, 0, -0.022, 0));
      J['shoulder' + L] = sh; J['elbow' + L] = el; J['wrist' + L] = wr;
    }

    /* legs */
    // the boot: a side profile with a rounded toe and heel, extruded and bevelled, on a thicker ridged sole
    const bootShape = new THREE.Shape();
    bootShape.moveTo(0.07, 0.0); bootShape.lineTo(-0.15, 0.0);
    bootShape.quadraticCurveTo(-0.235, 0.0, -0.232, 0.05); bootShape.quadraticCurveTo(-0.225, 0.1, -0.13, 0.115);
    bootShape.quadraticCurveTo(-0.085, 0.13, -0.075, 0.2); bootShape.lineTo(0.07, 0.2);
    bootShape.quadraticCurveTo(0.095, 0.1, 0.085, 0.03); bootShape.quadraticCurveTo(0.082, 0.0, 0.07, 0.0);
    const bootGeo = new THREE.ExtrudeGeometry(bootShape, { depth: 0.1, bevelEnabled: true, bevelThickness: 0.028, bevelSize: 0.024, bevelSegments: 6, curveSegments: 14 });
    bootGeo.translate(0, -0.2, -0.05); bootGeo.rotateY(-Math.PI / 2); bootGeo.scale(1.12, 1.05, 1.05); bootGeo.computeVertexNormals();
    // Each leg is one skinned half of the pants, from under the waist ring to inside the boot cuff. At the top its cross
    // section is half of the briefs (a D: the briefs' ellipse cut at the middle), lower down it becomes the round thigh;
    // the middle seam stays with the torso, so the two halves always meet. Bends: hip, knee (bellows, a pad in front),
    // ankle (high up the shin: the foot turns inside the boot).
    const briefP = [[0.08, -0.27], [0.13, -0.255], [0.162, -0.22], [0.182, -0.16], [0.19, -0.08], [0.183, 0.0], [0.173, 0.06], [0.16, 0.12]];
    const rb = y => { y = Math.max(y, -0.2); for (let i = 1; i < briefP.length; i++) if (y <= briefP[i][1]) { const [r0, y0] = briefP[i - 1], [r1, y1] = briefP[i]; return r0 + (r1 - r0) * (y - y0) / (y1 - y0); } return briefP[briefP.length - 1][0]; };
    const HY = -0.13, KY = -0.68, KB = 0.11, KR = 0.1, AY = -1.24;
    const thighR = y => { const u = clamp01((HY - y) / 0.55); return (0.128 - 0.024 * u) * (1 + 0.06 * Math.sin(Math.PI * u)); };
    const shinR = (y, ph) => { const u = clamp01((KY - y) / 0.5); return (0.105 - 0.02 * u) * (1 + 0.1 * Math.sin(Math.PI * u)) * (1 + 0.06 * Math.max(0, Math.cos(ph))); };
    const legR = (s, y, ph) => {
      const dx = Math.sin(ph), dz = Math.cos(ph), cx = s * 0.105, cz = -0.035;
      // the distance from the thigh's centre to the edge of the briefs' half (the ellipse, or the middle plane x = 0)
      const A = 1.26 * rb(y), Bz = 0.9 * rb(y), qa = dx * dx / (A * A) + dz * dz / (Bz * Bz), qb = 2 * (cx * dx / (A * A) + cz * dz / (Bz * Bz)), qc = cx * cx / (A * A) + cz * cz / (Bz * Bz) - 1;
      let E = (-qb + Math.sqrt(Math.max(0, qb * qb - 4 * qa * qc))) / (2 * qa);
      if (s * dx < -1e-6) E = Math.min(E, 0.105 / -(s * dx));
      const m = sstep(-0.14, -0.36, y), d = y - KY;
      let r = E + ((thighR(y) + (shinR(y, ph) - thighR(y)) * sstep(KB, -KB, d)) - E) * m;
      if (s * dx < -1e-6) r = Math.min(r, (0.105 - 0.004 * m) / -(s * dx));   // the thighs press together, never through
      const pm = Math.abs(d) < KB ? sstep(0.3, 0.75, -Math.cos(ph)) * Math.exp(-((d / 0.08) ** 2)) : 0;   // the knee pad, -z
      const base = r * (1 + 0.1 * ridgeS(d, KB) * (1 - pm)) + KR * 0.22 * pm;
      return { r: base + fold(cx + base * dx, y, cz + base * dz, Math.max(bandEnv(d, KB), 1 - sstep(-0.05, -0.2, y))), base, pm, m };
    };
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const hp = bone(body, s * 0.105, HY, -0.035), kn = bone(hp, 0, KY - HY, 0.02), an = bone(kn, 0, AY - KY, -0.02);
      let leg = null;
      const hpH1 = helper(hp, 1 / 3), hpH2 = helper(hp, 2 / 3);
      const knH1 = helper(kn, 1 / 3, src => { if (leg) leg.morphTargetInfluences[0] = sstep(0, 2.2, -src.rotation.x); }), knH2 = helper(kn, 2 / 3);
      const anH = helper(an, 0.5);
      const rows = span([0.07, -0.1, 0.008], [-0.1, -0.3, 0.0025], [-0.3, KY + KB, 0.008], [KY + KB, KY - KB, 0.0025], [KY - KB, -1.0, 0.008], [-1.0, -1.1, 0.004], [-1.1, AY + 0.09, 0.008]).map(y => ({
        y, cx: s * 0.105, cz: -0.035, r: ph => legR(s, y, ph).r, col: ph => bendCol(y - KY, KB, legR(s, y, ph).pm),
        w: (ph, r) => {
          if (y > -0.1) return [[body, 1]];
          if (y > -0.3) {   // the hip: the middle seam is pinned to the torso until the leg is round
            const x = s * 0.105 + r * Math.sin(ph), m = legR(s, y, ph).m, p = sstep(0, 0.035, s * x) * (1 - m) + m;
            return spread([body, hpH1, hpH2, hp], cubic(clamp01((-0.1 - y) / 0.2) * p));
          }
          if (y > KY + KB) return [[hp, 1]];
          if (y > KY - KB) return spread([hp, knH1, knH2, kn], cubic((KY + KB - y) / (2 * KB)));
          if (y > -1.0) return [[kn, 1]];
          if (y > -1.1) return spread([kn, anH, an], quad((-1.0 - y) / 0.1));
          return [[an, 1]];
        },
      }));
      leg = skinTube(rows, 56, (rw, ph, nx, ny, nz) => bendMorph(rw.y - KY, KB, KR, 1, Math.max(0, nz), Math.max(0, -nz)));
      proxy(hp, 0.25, 0.55, 0.25, -0.28); proxy(kn, 0.21, 0.5, 0.21, -0.27);
      pocket(hp, s * (legR(s, HY - 0.3, s * Math.PI / 2).base + 0.008), -0.3, 0, s * Math.PI / 2, s < 0 ? 0.1 : 0.12, 0.12, 0);   // thigh pockets (the right one wider)
      pocket(kn, s * (legR(s, KY - 0.2, s * Math.PI / 2).base + 0.008), -0.2, -0.02, s * Math.PI / 2, 0.075, 0.1);              // and a smaller one on each shin
      // the boot: the ankle pivot sits inside it, 0.127 above the sole
      an.add(mesh(lumpy(lathe([[0, -0.02], [0.094, -0.02], [0.1, 0.03], [0.092, 0.08]], 48), 0.004), fabric2, 0, 0.13, 0));   // a cloth cuff over the boot top, open above
      an.add(at(ringY(0.096, 0.015, metal), 0, 0.14, 0));
      an.add(mesh(bootGeo, shell, 0, 0.13, 0));
      an.add(mesh(rbox(0.175, 0.04, 0.34, 0.016), dark, 0, -0.09, -0.078));                      // sole
      for (let k = 0; k < 6; k++) an.add(mesh(new THREE.BoxGeometry(0.17, 0.01, 0.018), grey, 0, -0.112, 0.06 - k * 0.055));   // tread
      an.add(mesh(new THREE.BoxGeometry(0.185, 0.024, 0.07), grey, 0, 0.02, 0.02));               // strap
      J['hip' + L] = hp; J['knee' + L] = kn; J['ankle' + L] = an;
    }
    proxy(body, 0.48, 0.4, 0.34, -0.07);   // the briefs

    /* the Nebozvid emblem: a round patch with the site's wordmark (characters/emblem.js, made by emblem.py) */
    const emblemImg = new Image(), emblemTex = new THREE.Texture(emblemImg);
    emblemTex.encoding = THREE.sRGBEncoding; emblemTex.anisotropy = 8;
    const ready = new Promise(ok => { emblemImg.onload = () => { emblemTex.needsUpdate = true; ok(); }; emblemImg.onerror = () => ok(); });
    if (window.__astronautEmblem) emblemImg.src = window.__astronautEmblem; else emblemImg.onerror();
    const emblemMat = M({ map: emblemTex, transparent: true, roughness: 0.75, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2 });
    // a disc bent to lie on a surface: z pushed back by the surface's curvature (k) over x
    const patch = (rad, k) => { const g = new THREE.CircleGeometry(rad, 48), p = g.attributes.position; for (let i = 0; i < p.count; i++) p.setZ(i, -k * p.getX(i) * p.getX(i)); g.computeVertexNormals(); return g; };
    // on the left of the chest, above the control box: set on the torso's surface there (an ellipse 0.297 × 0.209 at
    // this height), turned to its normal and bent to its curve
    const cx = -0.1, ca = 0.297, cb = 0.209, cz = -cb * Math.sqrt(1 - (cx / ca) ** 2), slope = Math.atan(cb * cx / (ca * ca * Math.sqrt(1 - (cx / ca) ** 2)));
    const chest = mesh(patch(0.055, cb / (ca * ca) * 0.9), emblemMat, cx, 0.49, cz - 0.006); chest.rotation.set(-0.08, Math.PI - slope, 0, 'YXZ'); body.add(chest);
    { const tx = 0.11, tz = -cb * Math.sqrt(1 - (tx / ca) ** 2), ts = Math.atan(cb * tx / (ca * ca * Math.sqrt(1 - (tx / ca) ** 2)));
      const tag = joint(body, tx, 0.5, tz - 0.004); tag.rotation.set(-0.08, Math.PI - ts, 0, 'YXZ');   // a name tag on the right of the chest
      tag.add(mesh(rbox(0.1, 0.032, 0.006, 0.004), grey)); tag.add(mesh(new THREE.PlaneGeometry(0.084, 0.012), white, 0, 0, 0.0035)); }
    const back = mesh(patch(0.085, 0.35), emblemMat, 0, 0.03, 0.127); pack.add(back);                                                // on the backpack flap

    // bind the sleeves to the skeleton at rest (every bone made, nothing turned yet)
    group.updateMatrixWorld(true);
    const skeleton = new THREE.Skeleton(bones);
    skinned.forEach(m => m.bind(skeleton));
    shadowed(group);

    // The free-fall rest pose (arms afloat, knees bent), the two sides a little different, each joint drifting slowly.
    const w = (t, p, ph) => Math.sin(t * 2 * Math.PI / p + ph);
    function pose(t) {
      for (const s of [-1, 1]) {
        const L = s < 0 ? 'L' : 'R', ph = s < 0 ? 0 : 1.9, a = s < 0 ? 1 : -1;
        J['shoulder' + L].rotation.set(0.35 + 0.08 * a + 0.09 * w(t, 5.3, ph), 0.1 * s, s * (0.8 + 0.12 * a + 0.1 * w(t, 6.1, ph + 1)));
        J['elbow' + L].rotation.set(0.75 + 0.12 * w(t, 4.4, ph + 2), 0, 0);
        J['wrist' + L].rotation.set(0.2 + 0.12 * w(t, 3.7, ph), 0.3 * s, s * 0.15);
        J['hip' + L].rotation.set(0.32 + 0.14 * a + 0.06 * w(t, 6.7, ph + 0.5), 0, s * (0.1 + 0.03 * w(t, 7.3, ph)));
        J['knee' + L].rotation.set(-0.75 - 0.3 * a + 0.1 * w(t, 5.9, ph + 2.6), 0, 0);
        J['ankle' + L].rotation.set(0.3 + 0.05 * w(t, 4.9, ph), 0, 0);
      }
      J.head.rotation.set(-0.1 + 0.04 * w(t, 8.1, 0.3), 0.05 * w(t, 9.7, 1), 0);
      J.body.rotation.set(0.1 + 0.03 * w(t, 7.7, 0), 0, 0.03 * w(t, 11.3, 2));
    }
    pose(0);

    // shadow-casting lights that follow the figure (each keeps it inside its shadow camera): a.light(color, k, dir)
    const lights = [];
    function light(color, intensity, dir) {
      const l = new THREE.DirectionalLight(color, intensity);
      l.castShadow = true; l.shadow.mapSize.set(2048, 2048); l.shadow.bias = -0.0015; l.shadow.normalBias = 0.035;
      Object.assign(l.shadow.camera, { left: -1.3, right: 1.3, top: 1.3, bottom: -1.3, near: 0.1, far: 10 });
      l.shadow.radius = 4;
      l.userData.dir = (dir || new THREE.Vector3(0, 0.6, -1)).clone().normalize();
      lights.push(l); return l;
    }
    function aim() {
      group.updateMatrixWorld();
      const c = group.getWorldPosition(new THREE.Vector3());
      for (const l of lights) { l.position.copy(c).addScaledVector(l.userData.dir, 4); l.target.position.copy(c); l.target.updateMatrixWorld(); }
    }
    return {
      group, joints: J, materials: mats, pose, rim, light, aim, lights, ready,
      setTint(r, g, b) { const c = new THREE.Color(r, g, b); for (const m of mats) m.color.copy(m.userData.base).multiply(c); },
      // opaque until it fades: a transparent material lets the parts behind show through
      setOpacity(x) { for (const g of glows) g.material.opacity = 0.85 * x; const tr = x < 0.999; for (const m of mats) { if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; } m.opacity = x; m.depthWrite = !tr; } },
    };
  };

  // An environment for reflections: dark space and a warm glow (e.g. a hot disc) from `warm`.
  window.__astronautEnv = (THREE, renderer, opts = {}) => {
    const warm = (opts.warm || new THREE.Vector3(0, 0.15, -1)).clone().normalize();
    const sc = new THREE.Scene();
    sc.add(new THREE.Mesh(new THREE.SphereGeometry(10, 64, 32), new THREE.ShaderMaterial({
      uniforms: { w: { value: warm } }, side: THREE.BackSide,
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform vec3 w; varying vec3 vD;
        void main(){ float m = max(dot(vD, w), 0.0);
          vec3 c = vec3(0.012, 0.014, 0.022) + vec3(1.0, 0.62, 0.3) * (pow(m, 6.0) * 1.2 + pow(m, 40.0) * 4.0)
                 + vec3(0.06, 0.07, 0.1) * max(vD.y, 0.0);
          gl_FragColor = vec4(c, 1.0); }`,
    })));
    const pm = new THREE.PMREMGenerator(renderer);
    const tex = pm.fromScene(sc, 0.02).texture; pm.dispose();
    return tex;
  };
})();
