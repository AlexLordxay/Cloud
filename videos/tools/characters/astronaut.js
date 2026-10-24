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
    const M = (o, Kind = THREE.MeshStandardMaterial) => {
      const m = new Kind(o);
      m.color.convertSRGBToLinear(); m.emissive.convertSRGBToLinear();   // the hex colours are sRGB: lit in linear space they keep their real shade
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
    function clothTexture(seams, quilt = 0) {
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
        g.fillStyle = 'rgba(95,90,82,0.35)';
        for (let y = 0; y < N; y += 14) { g.fillRect(x - 9, y, 2, 7); g.fillRect(x + 8, y + 5, 2, 7); }   // stitches
      }
      if (quilt) {   // quilting: puffed diamonds with stitched lines between them
        for (let cy = 0; cy < N; cy += quilt) for (let cx = 0; cx < N; cx += quilt) {
          const gr = g.createRadialGradient(cx + quilt / 2, cy + quilt / 2, 0, cx + quilt / 2, cy + quilt / 2, quilt * 0.7);
          gr.addColorStop(0, 'rgba(255,255,255,0.08)'); gr.addColorStop(1, 'rgba(0,0,0,0.07)'); g.fillStyle = gr; g.fillRect(cx, cy, quilt, quilt); }
        g.strokeStyle = 'rgba(120,114,104,0.22)'; g.lineWidth = 2.5; g.setLineDash([8, 7]);
        for (let k = -N; k < 2 * N; k += quilt) { g.beginPath(); g.moveTo(k, 0); g.lineTo(k + N, N); g.stroke(); g.beginPath(); g.moveTo(k, N); g.lineTo(k + N, 0); g.stroke(); }
        g.setLineDash([]);
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
    const [quiltMap, quiltBump] = clothTexture([], 170);
    const quilted = M({ color: 0xece8de, roughness: 0.92, metalness: 0, map: quiltMap, bumpMap: quiltBump, bumpScale: 0.08 });   // its quilted thermal cover
    const shell = M({ color: 0xeceae3, roughness: 0.6, metalness: 0.0 });          // hard parts
    const helmetMat = M({ color: 0xeeece6, roughness: 0.35, metalness: 0, clearcoat: 0.6, clearcoatRoughness: 0.2 }, THREE.MeshPhysicalMaterial);   // the helmet: a lacquered shell
    const metal = M({ color: 0xc3c7cc, roughness: 0.28, metalness: 0.85 });          // bearings, valves
    const grey = M({ color: 0x6d7076, roughness: 0.6, metalness: 0.2 });
    const dark = M({ color: 0x26282c, roughness: 0.75, metalness: 0.1 });
    // the visor: gold film under a clear glossy coat (physical material), so it mirrors the light like real glass
    const visor = new THREE.MeshPhysicalMaterial({ color: 0xd9a043, metalness: 1.0, roughness: 0.06, clearcoat: 1.0, clearcoatRoughness: 0.02, envMapIntensity: 1.4 });
    visor.color.convertSRGBToLinear(); visor.userData.base = visor.color.clone(); mats.push(visor);
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
    // a machined metal bearing band (axis along y): chamfered rims and a groove round its middle
    const machined = M({ color: 0xc3c7cc, roughness: 0.4, metalness: 0.7 });
    const band = (R, h, d, mat = machined) => { const c = 0.3 * d;
      return new THREE.Mesh(lathe([[R - d, -h / 2], [R - 0.3 * d, -h / 2], [R, -h / 2 + c], [R, -0.15 * h], [R - 0.25 * d, -0.1 * h], [R - 0.25 * d, 0.1 * h], [R, 0.15 * h], [R, h / 2 - c], [R - 0.3 * d, h / 2], [R - d, h / 2]], 64), mat); };
    // small latches round a band: at angles angs on an ellipse (R·sx, R·sz), facing out
    const latches = (parent, R, y, angs, sx = 1, sz = 1) => angs.forEach(a => {
      const x = Math.sin(a) * R * sx, z = Math.cos(a) * R * sz, l = mesh(rbox(0.03, 0.02, 0.015, 0.004), grey, x, y, z);
      l.rotation.y = Math.atan2(x / (sx * sx), z / (sz * sz)); parent.add(l); });
    // Normals smoothed across faces that meet at less than creaseDeg (area-weighted), sharp across real edges: a bevel
    // reads as one rounded surface, not as bands
    function smoothNormals(geo, creaseDeg = 50) {
      if (geo.index) geo = geo.toNonIndexed();
      const p = geo.attributes.position, nF = p.count / 3, fn = [], map = new Map(), cos = Math.cos(creaseDeg * Math.PI / 180), a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
      const key = i => Math.round(p.getX(i) * 1e5) + ',' + Math.round(p.getY(i) * 1e5) + ',' + Math.round(p.getZ(i) * 1e5);
      for (let f = 0; f < nF; f++) {
        a.fromBufferAttribute(p, 3 * f); b.fromBufferAttribute(p, 3 * f + 1); c.fromBufferAttribute(p, 3 * f + 2);
        const n = new THREE.Vector3().crossVectors(b.clone().sub(a), c.clone().sub(a)); fn.push([n, n.clone().normalize()]);
        for (let k = 0; k < 3; k++) { const kk = key(3 * f + k); if (!map.has(kk)) map.set(kk, []); map.get(kk).push(f); }
      }
      const out = new Float32Array(p.count * 3), t = new THREE.Vector3();
      for (let i = 0; i < p.count; i++) {
        const f0 = Math.floor(i / 3); t.set(0, 0, 0);
        for (const f of map.get(key(i))) if (fn[f][1].dot(fn[f0][1]) > cos) t.add(fn[f][0]);
        t.normalize(); out[3 * i] = t.x; out[3 * i + 1] = t.y; out[3 * i + 2] = t.z;
      }
      geo.setAttribute('normal', new THREE.BufferAttribute(out, 3)); return geo;
    }
    // texture coordinates projected along each face's main axis, scale metres per repeat (no stretching on box sides)
    function boxUV(g, scale = 0.5) {
      const p = g.attributes.position, n = g.attributes.normal, uv = new Float32Array(p.count * 2);
      for (let i = 0; i < p.count; i++) { const ax = Math.abs(n.getX(i)), ay = Math.abs(n.getY(i)), az = Math.abs(n.getZ(i)), x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const [u, v] = az >= ax && az >= ay ? [x, y] : ax >= ay ? [z, y] : [x, z]; uv[2 * i] = u / scale + 0.37; uv[2 * i + 1] = v / scale + 0.61; }
      g.setAttribute('uv', new THREE.BufferAttribute(uv, 2)); return g;
    }
    // a box with rounded edges (an extruded rounded rectangle, bevelled), centred
    function rbox(w, h, d, r) {
      const s = new THREE.Shape(), x = -w / 2 + r, y = -h / 2 + r, W = w - 2 * r, H = h - 2 * r;
      s.moveTo(x, y - r); s.lineTo(x + W, y - r); s.quadraticCurveTo(x + W + r, y - r, x + W + r, y);
      s.lineTo(x + W + r, y + H); s.quadraticCurveTo(x + W + r, y + H + r, x + W, y + H + r);
      s.lineTo(x, y + H + r); s.quadraticCurveTo(x - r, y + H + r, x - r, y + H); s.lineTo(x - r, y); s.quadraticCurveTo(x - r, y - r, x, y - r);
      const bv = Math.min(r, d / 2) * 0.9;
      const g = new THREE.ExtrudeGeometry(s, { depth: Math.max(1e-3, d - 2 * bv), bevelEnabled: true, bevelThickness: bv, bevelSize: bv * 0.9, bevelSegments: 5, curveSegments: 10 });
      g.translate(0, 0, -Math.max(1e-3, d - 2 * bv) / 2); return smoothNormals(g);
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
    const waist = at(band(0.18, 0.03, 0.01), 0, 0.06, 0); waist.scale.set(1.26, 1, 0.9); body.add(waist);
    latches(body, 0.182, 0.06, [0.5, -0.5, Math.PI - 0.6, Math.PI + 0.6], 1.26, 0.9);
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
    const scrMat = M({ color: 0x000000, emissive: 0xffffff, emissiveMap: screenTex, emissiveIntensity: 0.55, roughness: 0.15, metalness: 0 });
    dcm.add(mesh(rbox(0.1, 0.052, 0.004, 0.006), lens, 0.065, 0.012, -0.056));                          // the screen's dark frame
    const scr = mesh(new THREE.PlaneGeometry(0.09, 0.045), scrMat, 0.065, 0.012, -0.0585); scr.rotation.y = Math.PI; dcm.add(scr);
    // its controls, on the face (dcm-local, the face at z -0.055): a knurled oxygen knob, two toggle switches behind
    // guards, a red purge knob, two status lights over the screen and a little printed label strip
    { const F = -0.055, face = (m, x, y, z = 0) => { m.position.set(x, y, F + z); dcm.add(m); return m; };
      const knurl = (() => { const g = new THREE.CylinderGeometry(0.016, 0.016, 0.016, 96, 1), p = g.attributes.position;
        for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), a = Math.atan2(z, x), r = Math.hypot(x, z); if (r > 1e-4) { const k = (r + 0.0012 * Math.max(0, Math.cos(24 * a))) / r; p.setX(i, x * k); p.setZ(i, z * k); } }
        g.computeVertexNormals(); return g; })();
      face(new THREE.Mesh(knurl, metal), -0.105, 0.016, -0.008).rotation.x = Math.PI / 2;
      face(new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.012, 0.004, 32), dark), -0.105, 0.016, -0.018).rotation.x = Math.PI / 2;   // its cap
      for (const x of [-0.064, -0.034]) {
        face(new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.007, 0.006, 20), machined), x, 0.018, -0.003).rotation.x = Math.PI / 2;
        const lever = new THREE.Group(); face(lever, x, 0.018, -0.006); lever.rotation.x = -0.45;
        lever.add(mesh(new THREE.CylinderGeometry(0.0018, 0.0022, 0.018, 10), metal, 0, 0.009, 0), mesh(new THREE.SphereGeometry(0.0032, 12, 8), metal, 0, 0.018, 0));
        for (const g of [-1, 1]) face(mesh(rbox(0.003, 0.026, 0.014, 0.0012), dark), x + g * 0.011, 0.016, -0.007);   // the guards
      }
      face(new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.012, 0.012, 28), connRed), -0.085, -0.026, -0.006).rotation.x = Math.PI / 2;   // purge
      face(new THREE.Mesh(new THREE.TorusGeometry(0.013, 0.0022, 8, 28), machined), -0.085, -0.026, -0.001);
      face(new THREE.Mesh(new THREE.SphereGeometry(0.0035, 10, 8), M({ color: 0x40ff80, emissive: 0x30ff70, emissiveIntensity: 1.4 })), 0.04, 0.046, -0.001);
      face(new THREE.Mesh(new THREE.SphereGeometry(0.0035, 10, 8), M({ color: 0xffb030, emissive: 0xffa020, emissiveIntensity: 1.2 })), 0.055, 0.046, -0.001);
      const label = (txt, x, y) => { const cv = document.createElement('canvas'); cv.width = 96; cv.height = 32; const g = cv.getContext('2d');
        g.fillStyle = '#d8dde4'; g.font = 'bold 22px "DejaVu Sans", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, 48, 17);
        const t = new THREE.CanvasTexture(cv); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8;
        face(new THREE.Mesh(new THREE.PlaneGeometry(0.03, 0.01), M({ map: t, transparent: true, roughness: 0.6 })), x, y, -0.0006).rotation.y = Math.PI; };
      label('O\u2082', -0.105, -0.006); label('H\u2082O', -0.064, -0.001); label('FAN', -0.034, -0.001); label('PURGE', -0.085, -0.045);
    }
    // Connector boxes sewn onto the torso, a striped hose from the control box into each. A box sits on a cloth patch
    // that lies on the surface (the torso at height y is an ellipse A × B); its nipple points up, the hose comes down onto it.
    function port(x, y, A, B, path) {
      const q = Math.sqrt(1 - (x / A) ** 2), zs = -B * q, ang = Math.atan(B * x / (A * A * q));
      const mount = joint(body, x, y, zs); mount.rotation.y = Math.PI - ang;                          // local +z = out of the suit
      mount.add(mesh(lumpy(rbox(0.07, 0.07, 0.01, 0.012), 0.0015, 20), cover, 0, 0, 0.002));          // the sewn-on patch
      mount.add(mesh(rbox(0.05, 0.05, 0.028, 0.008), grey, 0, 0, 0.018));                             // the connector box
      mount.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.018, 28), machined), 0, 0.032, 0.018));   // a quick-disconnect fitting
      mount.add(at(new THREE.Mesh(new THREE.TorusGeometry(0.0205, 0.0035, 8, 28), x < 0 ? connBlue : connRed), 0, 0.034, 0.018).rotateX(Math.PI / 2));   // its coloured collar
      mount.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.02, 0.008, 28), metal), 0, 0.045, 0.018));
      const top = new THREE.Vector3(0, 0.048, 0.018).applyMatrix4(new THREE.Matrix4().compose(mount.position, mount.quaternion, new THREE.Vector3(1, 1, 1)));
      body.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([...path(top), top]), 40, 0.014, 10, false), hoseMat));
    }
    for (const sd of [-1, 1]) {
      // two from the box's sides up into the upper chest, in front of the shoulders (clear of the arms)
      port(sd * 0.215, 0.42, 0.2948, 0.2106, t => [new THREE.Vector3(sd * 0.13, 0.32, -0.285), new THREE.Vector3(sd * 0.175, 0.37, -0.275), new THREE.Vector3(t.x * 0.97, t.y + 0.045, t.z - 0.03)]);
      // two down into the belly, just above the belt
      port(sd * 0.15, 0.11, 0.219, 0.157, t => [new THREE.Vector3(sd * 0.08, 0.29, -0.28), new THREE.Vector3(sd * 0.11, 0.22, -0.24), new THREE.Vector3(t.x * 0.97, t.y + 0.05, t.z - 0.025)]);
    }
    // Flat webbing along a curve lying on the body: its width across the curve and along the surface (the surface's
    // outward direction taken from a centre point), its thickness out of the surface
    function webbing(pts, W = 0.032, th = 0.003, centre = new THREE.Vector3(0, 0.35, 0), mat = strap, n = 60) {
      const c = new THREE.CatmullRomCurve3(pts), pos = [], idx = [];
      for (let i = 0; i <= n; i++) {
        const p = c.getPoint(i / n), T = c.getTangent(i / n), o = p.clone().sub(centre).normalize(), w = new THREE.Vector3().crossVectors(T, o).normalize();
        o.crossVectors(w, T).normalize();
        for (const [a, b] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { const q = p.clone().addScaledVector(w, a * W / 2).addScaledVector(o, b * th / 2); pos.push(q.x, q.y, q.z); }
      }
      for (let i = 0; i < n; i++) for (let k = 0; k < 4; k++) { const a = 4 * i + k, b = 4 * i + (k + 1) % 4; idx.push(a, b, a + 4, b, b + 4, a + 4); }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
      return new THREE.Mesh(g, mat);
    }
    // the backpack's harness: beige webbing over the shoulders down to the control box, buckled at both ends
    for (const sd of [-1, 1]) {
      body.add(webbing([new THREE.Vector3(sd * 0.13, 0.5, 0.215), new THREE.Vector3(sd * 0.155, 0.605, 0.1), new THREE.Vector3(sd * 0.16, 0.605, -0.08), new THREE.Vector3(sd * 0.148, 0.5, -0.205), new THREE.Vector3(sd * 0.135, 0.42, -0.232)]));
      const bk = mesh(rbox(0.04, 0.03, 0.007, 0.005), machined, sd * 0.133, 0.405, -0.238); bk.rotation.x = 0.35; body.add(bk);   // the buckle at the box
      bk.add(mesh(new THREE.BoxGeometry(0.03, 0.006, 0.004), dark, 0, 0.002, -0.004));
    }
    // a coiled safety tether on the right of the belt: it hangs from a D-ring on the belt, its hook clipped to a loop below
    { const X = 0.266, Z = -0.005;   // on the belt's side (the belt is 0.22 out there): the ring sits on it, the coil hangs just outside the suit
      const dr = at(new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.0048, 8, 20), metal), 0.24, 0.05, Z); body.add(dr);
      const pts = []; for (let k = 0; k <= 160; k++) { const a = k / 160 * Math.PI * 2 * 5; pts.push(new THREE.Vector3(X + Math.cos(a) * 0.022, 0.03 - k / 160 * 0.1, Z + Math.sin(a) * 0.022)); }
      body.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 480, 0.0052, 6, false), dark));
      const hook = at(new THREE.Mesh(new THREE.TorusGeometry(0.014, 0.0042, 8, 20, Math.PI * 1.6), metal), X, -0.085, Z); hook.rotation.y = 0; body.add(hook);
      const tab = mesh(rbox(0.03, 0.04, 0.03, 0.006), strap, 0.248, -0.1, Z); tab.rotation.y = Math.PI / 2; body.add(tab); }   // a cloth loop sewn on the suit

    /* life-support backpack (+z side), the SAFER jetpack under it */
    const pack = joint(body, 0, 0.37, 0.265);
    const bend = (g, k) => { const p = g.attributes.position; for (let i = 0; i < p.count; i++) p.setZ(i, p.getZ(i) - k * p.getX(i) * p.getX(i) - 0.3 * k * p.getY(i) * p.getY(i)); g.computeVertexNormals(); return g; };
    pack.add(mesh(boxUV(lumpy(bend(rbox(0.5, 0.58, 0.2, 0.065), 0.32), 0.003, 9), 0.6), quilted));             // the body under its quilted thermal cover
    pack.add(mesh(rbox(0.46, 0.1, 0.18, 0.04), shell, 0, 0.3, -0.004));                            // the lid, flush on top
    pack.add(mesh(rbox(0.47, 0.008, 0.186, 0.004), dark, 0, 0.248, -0.004));                       // its seam
    pack.add(mesh(bend(rbox(0.506, 0.006, 0.206, 0.003), 0.32), dark, 0, -0.09, 0));               // the split between the two units
    pack.add(mesh(boxUV(lumpy(bend(rbox(0.34, 0.28, 0.03, 0.03), 0.32), 0.003, 12)), cover, 0, 0.0, 0.1));   // a padded flap on the back
    for (const s of [-1, 1]) pack.add(mesh(bend(new THREE.BoxGeometry(0.028, 0.48, 0.01, 1, 24, 1), 0.32), grey, s * 0.14, -0.01, 0.117));   // straps over it, lying on it
    pack.add(mesh(rbox(0.08, 0.05, 0.02, 0.008), grey, 0, -0.2, 0.11));
    { const lt = (() => { const cv = document.createElement('canvas'); cv.width = 512; cv.height = 64; const g = cv.getContext('2d');   // a stencilled name
        g.fillStyle = 'rgba(25,26,30,0.88)'; g.font = 'bold 46px "DejaVu Sans", sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('НЕБОЗВІД-01', 256, 34);
        const t = new THREE.CanvasTexture(cv); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t; })();
      pack.add(mesh(new THREE.PlaneGeometry(0.22, 0.0275), M({ map: lt, transparent: true, roughness: 0.9, polygonOffset: true, polygonOffsetFactor: -2 }), 0, 0.195, 0.1)); }
    for (const s of [-1, 1]) {
      const h = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.011, 10, 24, Math.PI), grey);   // handles on the top edges
      h.position.set(s * 0.15, 0.36, 0.0); h.scale.setScalar(0.85); pack.add(h);
      pack.add(mesh(new THREE.BoxGeometry(0.016, 0.4, 0.15), grey, s * 0.254, 0.0, 0.0));               // side rails
    }
    // the radio antenna on the top right (it sways a little after the body moves: see pose)
    const antenna = joint(pack, 0.19, 0.35, 0.03);
    antenna.add(mesh(new THREE.CylinderGeometry(0.009, 0.011, 0.016, 16), grey, 0, 0.008, 0), mesh(new THREE.CylinderGeometry(0.0022, 0.0026, 0.17, 8), metal, 0, 0.1, 0), mesh(new THREE.SphereGeometry(0.0055, 10, 8), dark, 0, 0.187, 0));
    // SAFER, the small rescue jetpack under the backpack: a box, two towers up the pack's sides, clusters of thruster nozzles
    const safer = joint(body, 0, 0.0, 0.265);
    safer.add(mesh(rbox(0.46, 0.11, 0.17, 0.03), shell), mesh(rbox(0.465, 0.008, 0.175, 0.004), grey, 0, 0.02, 0));
    const nozzle = (parent, x, y, z, dir) => { const n = mesh(new THREE.CylinderGeometry(0.0045, 0.0095, 0.014, 14, 1, true), dark, x, y, z);
      n.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize().negate()); parent.add(n);
      parent.add(at(new THREE.Mesh(new THREE.TorusGeometry(0.0095, 0.0015, 6, 14), metal), x - dir.x * 0.007, y - dir.y * 0.007, z - dir.z * 0.007)); };
    for (const s of [-1, 1]) {
      safer.add(mesh(rbox(0.05, 0.3, 0.12, 0.015), shell, s * 0.276, 0.135, 0));
      for (const y of [-0.01, 0.28]) {
        nozzle(safer, s * 0.302, y, 0.03, new THREE.Vector3(s, 0, 0)); nozzle(safer, s * 0.276, y, 0.062, new THREE.Vector3(0, 0, 1));
        nozzle(safer, s * 0.276, y + (y < 0 ? -0.006 : 0.006), -0.035, new THREE.Vector3(0, y < 0 ? -1 : 1, 0));
      }
    }
    safer.add(mesh(rbox(0.06, 0.03, 0.02, 0.006), M({ color: 0xf2c200, roughness: 0.6 }), 0.17, -0.045, 0.06));   // the yellow release handle

    /* neck ring, helmet with side lamps and the gold visor */
    const head = bone(body, 0, 0.625, -0.01); J.head = head;
    body.add(at(band(0.175, 0.045, 0.014), 0, 0.615, -0.01));   // the neck ring stays on the suit: only the helmet turns
    { const nk = joint(body, 0, 0.615, -0.01); latches(nk, 0.177, 0, [Math.PI / 4, -Math.PI / 4, 3 * Math.PI / 4, -3 * Math.PI / 4]); }
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
    const helmet = mesh(shellGeo, helmetMat, 0, 0.16, 0.0); helmet.scale.set(1, 1.03, 1.06); head.add(helmet);
    // The visor covers the front (-z) of the helmet (phi centred on 1.5π in three's sphere parametrisation). It bulges out
    // of the shell, as on an EVA visor assembly: a housing lip runs round the window and a thin dark seal lines it.
    const VIS = { r: 0.197, center: new THREE.Vector3(0, 0.16, -0.012), scale: new THREE.Vector3(1, 1.03, 1.06), P0, PL, T0, TL };
    const vis = mesh(new THREE.SphereGeometry(VIS.r, 72, 48, P0 - 0.06, PL + 0.12, T0 - 0.05, TL + 0.1), visor); vis.position.copy(VIS.center);
    vis.scale.copy(VIS.scale); head.add(vis);
    const winEdge = (r, e) => { const pts = [], sp = (ph, th) => new THREE.Vector3(-r * Math.cos(ph) * Math.sin(th), r * Math.cos(th), r * Math.sin(ph) * Math.sin(th)), n = 24;
      for (let k = 0; k < n; k++) pts.push(sp(P0 + e + (PL - 2 * e) * k / n, T0 + e));       // round the window's edge (a rectangle in angles)
      for (let k = 0; k < n; k++) pts.push(sp(P0 + PL - e, T0 + e + (TL - 2 * e) * k / n));
      for (let k = 0; k < n; k++) pts.push(sp(P0 + PL - e - (PL - 2 * e) * k / n, T0 + TL - e));
      for (let k = 0; k < n; k++) pts.push(sp(P0 + e, T0 + TL - e - (TL - 2 * e) * k / n));
      return new THREE.CatmullRomCurve3(pts, true); };
    for (const [r, e, tube, mat] of [[0.197, -0.005, 0.012, helmetMat], [0.203, 0.018, 0.0042, gasket]]) {   // the housing lip, the seal
      const m = mesh(new THREE.TubeGeometry(winEdge(r, e), 240, tube, 14, true), mat, 0, 0.16, 0); m.scale.copy(VIS.scale); head.add(m); }
    // pivot bosses at the temples (the visor assembly turns on them; the lamp and the camera mount on them), screwed on
    for (const sd of [-1, 1]) {
      const bo = joint(head, sd * 0.188, 0.165, -0.02); bo.rotation.z = Math.PI / 2;
      bo.add(mesh(new THREE.CylinderGeometry(0.035, 0.037, 0.016, 40), helmetMat, 0, sd * 0.008, 0), mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.004, 6), machined, 0, sd * 0.017, 0));
    }
    const brow = mesh(new THREE.SphereGeometry(0.2, 56, 20, Math.PI * 1.1, Math.PI * 0.8, Math.PI * 0.13, Math.PI * 0.06), helmetMat, 0, 0.16, 0);   // the eyeshade ridge over the visor brow.scale.set(1, 1.03, 1.06); head.add(brow);
    // Left of the helmet: a lamp — a cylinder on a bracket, a glowing lens with a soft halo, a row of small LEDs under it.
    // Right: a sensor/camera pod — a dark body, a big glass lens in a metal ring, a red indicator, a thin antenna.
    const glows = []; let glowK = 1;
    const glowTex = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 128; const g = cv.getContext('2d');
      const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,244,215,1)'); gr.addColorStop(0.25, 'rgba(255,236,200,0.45)'); gr.addColorStop(1, 'rgba(255,230,190,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(cv); })();
    const lampLight = M({ color: 0xfff6e6, emissive: 0xfff0d2, emissiveIntensity: 2.2, roughness: 0.2 });
    const ledMat = M({ color: 0xdff0ff, emissive: 0xcfe8ff, emissiveIntensity: 1.6, roughness: 0.3 });
    const redLed = M({ color: 0xff3a2a, emissive: 0xff2a1a, emissiveIntensity: 2.0, roughness: 0.3 });
    {
      const lamp = joint(head, -0.214, 0.2, -0.035);
      lamp.add(mesh(rbox(0.03, 0.05, 0.05, 0.008), grey, 0.012, -0.005, 0.02));                                         // bracket
      const body1 = mesh(new THREE.CylinderGeometry(0.03, 0.026, 0.12, 28), shell, -0.012, 0.0, -0.02); body1.rotation.x = Math.PI / 2; lamp.add(body1);
      const bezel = mesh(new THREE.TorusGeometry(0.029, 0.0055, 10, 28), metal, -0.012, 0.0, -0.081); lamp.add(bezel);
      const lensL = mesh(new THREE.CircleGeometry(0.025, 28), lampLight, -0.012, 0.0, -0.0815); lensL.rotation.y = Math.PI; lamp.add(lensL);
      for (let k = 0; k < 4; k++) lamp.add(mesh(new THREE.SphereGeometry(0.0045, 10, 8), ledMat, -0.012, -0.045, -0.05 + k * 0.016));   // LED row
      lamp.add(mesh(rbox(0.02, 0.014, 0.075, 0.004), grey, -0.012, -0.045, -0.026));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.85 }));
      halo.scale.setScalar(0.13); halo.position.set(-0.012, 0, -0.09); lamp.add(halo); glows.push(halo);
      const fw = new THREE.Vector3(), tc = new THREE.Vector3();   // the glow shows only while the lamp faces the camera
      halo.onBeforeRender = (r, sc, cam) => { lamp.getWorldDirection(fw).negate(); halo.getWorldPosition(tc); tc.subVectors(cam.position, tc).normalize();
        halo.material.opacity = 0.85 * glowK * sstep(0, 0.4, fw.dot(tc)); };
    }
    {
      const pod = joint(head, 0.21, 0.205, -0.03);
      pod.add(mesh(rbox(0.03, 0.05, 0.05, 0.008), grey, -0.012, -0.008, 0.02));                                         // bracket
      pod.add(mesh(rbox(0.05, 0.055, 0.09, 0.014), dcmMat, 0.01, 0, -0.01));                                              // dark body
      const ring = mesh(new THREE.TorusGeometry(0.019, 0.005, 10, 24), metal, 0.01, 0.002, -0.056); pod.add(ring);
      const glass = mesh(new THREE.SphereGeometry(0.017, 20, 14, 0, Math.PI * 2, 0, Math.PI / 2), lens, 0.01, 0.002, -0.056); glass.rotation.x = -Math.PI / 2; pod.add(glass);
      pod.add(mesh(new THREE.SphereGeometry(0.004, 10, 8), redLed, 0.03, 0.02, -0.055));                                    // a red "recording" light
    }

    // a cloth pocket with a flap and a press stud, lying on a limb's outside (local +z of the joint faces out)
    const bendTo = (g, R) => { const p = g.attributes.position; for (let i = 0; i < p.count; i++) p.setZ(i, p.getZ(i) - p.getX(i) ** 2 / (2 * R)); return smoothNormals(g); };   // wrap round a limb of radius R
    function pocket(parent, x, y, z, rotY, w, h, tilt = 0, R = 0.11) {
      const pk = joint(parent, x, y, z); pk.rotation.set(tilt, rotY, 0);
      pk.add(mesh(bendTo(lumpy(rbox(w, h, 0.022, 0.012), 0.002, 20), R), fabric2));
      pk.add(mesh(bendTo(rbox(w + 0.006, h * 0.34, 0.026, 0.01), R), cover, 0, h * 0.4, 0.006));   // the flap overhangs a little
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
    // ---- the gloves ----
    // A finger is a chain of three rigid phalanges, each a tapered capsule whose rounded ends are centred on its joints:
    // neighbouring phalanges share the same ball at a joint, so a finger bends to any angle with no gap and no pinch, the
    // ball showing as the knuckle on the outside of the bend. A little wider than deep. The last phalanx ends in a rounded
    // tip whose distal half is blue rubber, flush with the cloth. UVs in metres, so the weave matches the sleeves.
    const TEX = 0.5;
    // a lathe along -y between ball centres y0 and y1 (radii r0, r1), from angle a0 at the top ball to a1 at the bottom
    // one (0 = pole, pi/2 = the equator); open where an angle stops short of the pole
    function phalanx(r0, r1, y0, y1, a0 = 0, a1 = 0, mat = glove, nl = 10, puff = 0.09) {
      const pts = [];
      if (a0 < Math.PI / 2) for (let i = 0; i <= 8; i++) { const a = a0 + (Math.PI / 2 - a0) * i / 8; pts.push([r0 * Math.sin(a), y0 + r0 * Math.cos(a)]); }
      else pts.push([r0, y0]);
      for (let i = 1; i < nl; i++) { const u = i / nl; pts.push([(r0 + (r1 - r0) * u) * (1 + puff * Math.sin(Math.PI * u)), y0 + (y1 - y0) * u]); }   // puffed between the joints
      if (a1 < Math.PI / 2) for (let i = 0; i <= 8; i++) { const a = Math.PI / 2 - (Math.PI / 2 - a1) * i / 8; pts.push([r1 * Math.sin(a), y1 - r1 * Math.cos(a)]); }
      else pts.push([r1, y1]);
      const g = lathe(pts.reverse(), 24), uv = g.attributes.uv, len = Math.abs(y0 - y1) + r0 + r1, circ = Math.PI * (r0 + r1);
      for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * circ / TEX, uv.getY(i) * len / TEX);
      const m = new THREE.Mesh(g, mat); m.scale.x = 1.06; return m;
    }
    // a finger on bones [b1, b2, b3]: L phalanx lengths (the last with the tip), R radii at MCP, PIP, DIP and the tip
    function finger(bs, L, R) {
      bs[0].add(phalanx(R[0], R[1], 0, -L[0]));
      bs[1].add(phalanx(R[1], R[2], 0, -L[1], 0, Math.PI / 2));
      const yt = -(L[2] - R[3]);
      bs[1].add(phalanx(R[2], R[2], -L[1], -L[1], 0, 0, glove, 2, 0));   // the ball at the last joint, carried by the middle phalanx
      // the last phalanx: the rubber is a thimble, cut at a slant, reaching up the pad (-z) and over just the tip behind
      const tip = phalanx(R[2], R[3], 0, yt, 0, 0, [glove, rubber], 18, 0.05), g = tip.geometry, p = g.attributes.position, ix = g.index.array, gl = [], rb = [];
      for (let i = 0; i < ix.length; i += 3) {
        let y = 0, z = 0; for (let k = 0; k < 3; k++) { y += p.getY(ix[i + k]) / 3; z += p.getZ(ix[i + k]) / 3; }
        (y - yt < 0.004 - 0.75 * z ? rb : gl).push(ix[i], ix[i + 1], ix[i + 2]);
      }
      g.setIndex(gl.concat(rb)); g.clearGroups(); g.addGroup(0, gl.length, 0); g.addGroup(gl.length, rb.length, 1);
      bs[2].add(tip);
    }
    // The palm and the roots of the fingers and the thumb as ONE surface, so a finger grows out of the hand instead of
    // sitting on it: a distance field (the palm slab, smoothly welded to a short capsule at the root of each finger and
    // to the thumb's metacarpal, with fillets where they meet) turned into a mesh by surface nets, at rest. Past the
    // fillet each capsule sinks just under the finger's own rigid phalanx, so the two meet at a grazing angle and no edge
    // shows. Skinned: the palm to the wrist, the finger roots (and the palm's rim over them) to their fingers, the ball
    // of the thumb to the thumb, so the hand still bends as before.
    function gloveGeo(s, F, wr, T) {
      const G2 = (dx, dy, sx, sy) => Math.exp(-((dx / sx) ** 2 + (dy / sy) ** 2));
      const smin = (a, b, k) => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
      // the capsules: a finger's root (to 0.72 of its first phalanx), the thumb's metacarpal; radius as the phalanx's,
      // a hair fuller near the hand, a little thinner where it hides under the phalanx
      const caps = F.map(f => ({ a: new THREE.Vector3(f.x, f.y + 0.004, -0.002), dir: new THREE.Vector3(Math.sin(s * f.fan), -Math.cos(s * f.fan), 0), L: f.L[0], r0: f.R[0], r1: f.R[1], len: 0.72 * f.L[0], bone: f.b1 }));
      caps.push({ a: T.pos.clone(), dir: T.d.clone(), L: T.L[0], r0: T.R[0], r1: T.R[1], len: 0.75 * T.L[0], bone: T.t1 });
      const capD = (c, x, y, z) => {
        const vx = x - c.a.x, vy = y - c.a.y, vz = z - c.a.z, h = vx * c.dir.x + vy * c.dir.y + vz * c.dir.z, hc = Math.min(c.len, Math.max(0, h)), u = hc / c.L;
        const r = (c.r0 + (c.r1 - c.r0) * u) * (1 + 0.09 * Math.sin(Math.PI * u)) + 0.0006 - 0.0018 * sstep(0.45, 0.7, u);
        return [Math.hypot(vx - c.dir.x * hc, vy - c.dir.y * hc, vz - c.dir.z * hc) - r, h];
      };
      const palmD = (x, y, z) => {
        const yw = y - 4 * x * x, t = clamp01((0.012 - yw) / 0.125);                // y bent so the knuckle line is an arc
        const hx = 0.05 + 0.004 * t, zb = 0.025 - 0.009 * sstep(0.2, 1, t), zf = -0.021 + 0.004 * sstep(0.6, 1, t);   // the back slopes to the knuckles
        const r = 0.014, qx = Math.abs(x) - hx + r, qy = Math.abs(yw + 0.0505) - 0.0625 + r, qz = Math.abs(z - (zb + zf) / 2) - (zb - zf) / 2 + r;
        let d = Math.hypot(Math.max(qx, 0), Math.max(qy, 0), Math.max(qz, 0)) + Math.min(Math.max(qx, qy, qz), 0) - r;
        if (z < 0) d -= (0.014 * G2(x - s * 0.028, y + 0.036, 0.022, 0.032) + 0.008 * G2(x + s * 0.032, y + 0.06, 0.015, 0.034) - 0.005 * G2(x, y + 0.062, 0.02, 0.022)) * sstep(0, -0.015, z);   // thenar, hypothenar, the hollow
        return smin(d, Math.hypot(x, y, z / 0.85) - 0.044, 0.01);                   // the wrist rounds into a bulb (hidden in the cuff)
      };
      const sd = (x, y, z) => { let d = palmD(x, y, z); for (const c of caps) d = smin(d, capD(c, x, y, z)[0], 0.009); return d; };
      // surface nets on a 1.25 mm grid
      const h = 0.00125, x0 = -0.085, y0 = -0.165, z0 = -0.065, nx = Math.ceil(0.17 / h) + 1, ny = Math.ceil(0.235 / h) + 1, nz = Math.ceil(0.115 / h) + 1;
      const f = new Float32Array(nx * ny * nz), id = (i, j, k) => i + nx * (j + ny * k);
      for (let k = 0; k < nz; k++) for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) f[id(i, j, k)] = sd(x0 + i * h, y0 + j * h, z0 + k * h);
      const vix = new Int32Array((nx - 1) * (ny - 1) * (nz - 1)).fill(-1), cid = (i, j, k) => i + (nx - 1) * (j + (ny - 1) * k), P = [];
      const E = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]], C = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]];
      for (let k = 0; k < nz - 1; k++) for (let j = 0; j < ny - 1; j++) for (let i = 0; i < nx - 1; i++) {
        const v = C.map(([a, b, c]) => f[id(i + a, j + b, k + c)]); let neg = 0; for (const q of v) if (q < 0) neg++;
        if (neg === 0 || neg === 8) continue;
        let sx = 0, sy = 0, sz = 0, n = 0;
        for (const [a, b] of E) if ((v[a] < 0) !== (v[b] < 0)) { const t = v[a] / (v[a] - v[b]); sx += C[a][0] + (C[b][0] - C[a][0]) * t; sy += C[a][1] + (C[b][1] - C[a][1]) * t; sz += C[a][2] + (C[b][2] - C[a][2]) * t; n++; }
        vix[cid(i, j, k)] = P.length / 3; P.push(x0 + (i + sx / n) * h, y0 + (j + sy / n) * h, z0 + (k + sz / n) * h);
      }
      const grad = (x, y, z, e = 0.0003) => [sd(x + e, y, z) - sd(x - e, y, z), sd(x, y + e, z) - sd(x, y - e, z), sd(x, y, z + e) - sd(x, y, z - e)];
      const nV = P.length / 3, N = new Float32Array(P.length);
      for (let q = 0; q < nV; q++) {   // settle each vertex on the surface, then take the field's gradient as its normal
        let x = P[3 * q], y = P[3 * q + 1], z = P[3 * q + 2];
        for (let it = 0; it < 2; it++) { const d = sd(x, y, z), g = grad(x, y, z), l2 = (g[0] ** 2 + g[1] ** 2 + g[2] ** 2) / (0.0006 ** 2) || 1; x -= d * g[0] / 0.0006 / l2; y -= d * g[1] / 0.0006 / l2; z -= d * g[2] / 0.0006 / l2; }
        P[3 * q] = x; P[3 * q + 1] = y; P[3 * q + 2] = z;
        const g = grad(x, y, z), l = Math.hypot(...g) || 1; N[3 * q] = g[0] / l; N[3 * q + 1] = g[1] / l; N[3 * q + 2] = g[2] / l;
      }
      const idx = [], quad = (a, b, c, d) => {
        if (a < 0 || b < 0 || c < 0 || d < 0) return;
        const ax = P[3 * a], ay = P[3 * a + 1], az = P[3 * a + 2], ux = P[3 * b] - ax, uy = P[3 * b + 1] - ay, uz = P[3 * b + 2] - az, wx = P[3 * c] - ax, wy = P[3 * c + 1] - ay, wz = P[3 * c + 2] - az;
        const flip = (uy * wz - uz * wy) * N[3 * a] + (uz * wx - ux * wz) * N[3 * a + 1] + (ux * wy - uy * wx) * N[3 * a + 2] < 0;   // face outward
        if (flip) idx.push(a, c, b, a, d, c); else idx.push(a, b, c, a, c, d);
      };
      for (let k = 1; k < nz - 1; k++) for (let j = 1; j < ny - 1; j++) for (let i = 1; i < nx - 1; i++) {
        const s0 = f[id(i, j, k)] < 0;
        if (s0 !== (f[id(i + 1, j, k)] < 0)) quad(vix[cid(i, j - 1, k - 1)], vix[cid(i, j, k - 1)], vix[cid(i, j, k)], vix[cid(i, j - 1, k)]);
        if (s0 !== (f[id(i, j + 1, k)] < 0)) quad(vix[cid(i - 1, j, k - 1)], vix[cid(i, j, k - 1)], vix[cid(i, j, k)], vix[cid(i - 1, j, k)]);
        if (s0 !== (f[id(i, j, k + 1)] < 0)) quad(vix[cid(i - 1, j - 1, k)], vix[cid(i, j - 1, k)], vix[cid(i, j, k)], vix[cid(i - 1, j, k)]);
      }
      // weights: each part's share by how near it is (soft), a finger's root going with the finger past its knuckle,
      // the palm's rim past the knuckle line with the nearest fingers, the ball of the thumb with the thumb
      const si = [], sw = [], uv = [], bw = bones.indexOf(wr);
      for (let q = 0; q < nV; q++) {
        const x = P[3 * q], y = P[3 * q + 1], z = P[3 * q + 2], dp = palmD(x, y, z), cd = caps.map(c => capD(c, x, y, z));
        const dmin = Math.min(dp, ...cd.map(e => e[0])), mp = Math.exp(-(dp - dmin) / 0.003), mc = cd.map(e => Math.exp(-(e[0] - dmin) / 0.003)), tot = mp + mc.reduce((a, b) => a + b, 0);
        const w = new Map(), add = (b, v) => { if (v > 0) w.set(b, (w.get(b) || 0) + v); };
        caps.forEach((c, k) => add(c.bone, mc[k] / tot * sstep(-0.004, 0.012, cd[k][1])));
        const zone = 0.35 * sstep(0.02, 0, y - (-0.1 + 4 * x * x)) + 0.65 * sstep(0.002, -0.011, y - (-0.1 + 4 * x * x));
        F.forEach(fg => add(fg.b1, mp / tot * zone * Math.exp(-(((x - fg.x) / 0.015) ** 2))));
        add(T.t1, mp / tot * 0.6 * G2(x - s * 0.027, y + 0.038, 0.02, 0.03) * (z < 0 ? 1 : 0.5));
        let list = [...w.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3), sum = list.reduce((a, e) => a + e[1], 0);
        if (sum > 1) { list = list.map(([b, v]) => [b, v / sum]); sum = 1; }
        const all = [[wr, 1 - sum], ...list];
        for (let k = 0; k < 4; k++) { si.push(all[k] ? bones.indexOf(all[k][0]) : bw); sw.push(all[k] ? all[k][1] : 0); }
        uv.push((x + 0.4 * z) / TEX + 0.5, (y - 0.3 * z) / TEX + 0.6);   // the weave: one projection, offset so no tile edge crosses the hand
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4)); g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
      g.setIndex(idx); return g;
    }
    // name, MCP x (times s), MCP y, fan (times s), phalanx lengths (the last with the tip), radii [MCP, PIP, DIP, tip]
    const FING = [
      ['index', 0.0375, -0.098, 0.07, [0.044, 0.026, 0.024], [0.0148, 0.0134, 0.0124, 0.0116]],
      ['middle', 0.0123, -0.1045, 0.015, [0.048, 0.029, 0.025], [0.0153, 0.014, 0.0129, 0.012]],
      ['ring', -0.014, -0.1015, -0.04, [0.045, 0.028, 0.024], [0.0146, 0.0133, 0.0123, 0.0115]],
      ['little', -0.038, -0.0925, -0.1, [0.035, 0.022, 0.021], [0.013, 0.012, 0.011, 0.0104]],
    ];
    const HANDS = {};
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
        const tex = (() => { const cv = document.createElement('canvas'); cv.width = 220; cv.height = 150; const g = cv.getContext('2d');
          g.fillStyle = '#e9e6de'; g.fillRect(0, 0, 220, 150); g.fillStyle = '#0057b7'; g.fillRect(8, 8, 204, 67); g.fillStyle = '#ffd500'; g.fillRect(8, 75, 204, 67);
          g.strokeStyle = 'rgba(80,76,70,0.8)'; g.lineWidth = 2; g.setLineDash([6, 5]); g.strokeRect(4, 4, 212, 142);   // the stitched edge
          const t = new THREE.CanvasTexture(cv); t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t; })();
        f.add(mesh(wrapPlane(0.11, 0.075, r + 0.001), M({ map: tex, roughness: 0.85 }), 0, 0, 0));
      }
      if (s < 0) {   // the cuff checklist on the left forearm: a little book of cards on a strap
        const ck = joint(el, 0, -0.19, -(armR(s, EY - 0.19, Math.PI).base + 0.012)); ck.rotation.y = Math.PI;
        ck.add(mesh(rbox(0.085, 0.062, 0.018, 0.006), grey));
        for (let k = 0; k < 3; k++) ck.add(mesh(new THREE.BoxGeometry(0.075, 0.052, 0.002), white, 0, 0, 0.011 + k * 0.0025));
      }
      // the wrist disconnect: a dark ring with a coloured stripe (blue on the left, red on the right, as on real suits)
      el.add(at(band(0.069, 0.024, 0.009), 0, -0.293, 0));                                   // a slim wrist ring, the sleeve's own width
      el.add(at(ringY(0.0655, 0.0042, s < 0 ? connBlue : connRed), 0, -0.306, 0));
      // the gauntlet: a flared cuff, open below, with a rolled lip; the hand turns under it
      el.add(mesh(lathe([[0.052, -0.349], [0.056, -0.345], [0.066, -0.334], [0.072, -0.318], [0.068, -0.303], [0.058, -0.29]], 48), glove));
      el.add(at(ringY(0.052, 0.0035, glove), 0, -0.349, 0));
      // the glove (see phalanx, finger, gloveGeo): the wrist bone is the palm's base, every finger and the thumb have three bones
      const F = FING.map(([name, mx, my, fan, Lf, Rf]) => {
        const root = joint(wr, s * mx, my + 0.004, -0.002); root.rotation.z = s * fan;      // its spread
        const b1 = bone(root, 0, 0, 0), b2 = bone(b1, 0, -Lf[0], 0), b3 = bone(b2, 0, -Lf[1], 0);
        finger([b1, b2, b3], Lf, Rf);
        return { name, root, fan, b: [b1, b2, b3], b1, x: s * mx, y: my, L: Lf, R: Rf };
      });
      // the thumb: from inside the thenar pad, pointing down, out and forward, turned on its own axis so its pad faces
      // the fingers (opposition); bones: metacarpal (CMC), proximal (MCP), distal (IP)
      const troot = joint(wr, s * 0.028, -0.022, -0.008);
      const d = new THREE.Vector3(s * 0.5, -0.78, -0.38).normalize(), padDir = new THREE.Vector3(-s * 0.8, -0.1, -0.55).normalize();
      const yA = d.clone().negate(), zA = padDir.clone().negate().addScaledVector(yA, padDir.dot(yA)).normalize(), xA = new THREE.Vector3().crossVectors(yA, zA);
      troot.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xA, yA, zA));
      const TL = [0.042, 0.034, 0.032], t1 = bone(troot, 0, 0, 0), t2 = bone(t1, 0, -TL[0], 0), t3 = bone(t2, 0, -TL[1], 0);
      const TR = [0.022, 0.0158, 0.014, 0.0124];   // thick at the base: it grows out of the ball of the thumb
      finger([t1, t2, t3], TL, TR);
      { const m = new THREE.SkinnedMesh(gloveGeo(s, F, wr, { pos: troot.position, d, L: TL, R: TR, t1 }), glove); m.frustumCulled = false; wr.add(m); skinned.push(m); }
      // +abduction turns the thumb about its root's z: it must move away from the index finger on both hands
      const away = troot.position.clone().addScaledVector(d, 0.1).sub(new THREE.Vector3(s * 0.0335, -0.13, 0));
      HANDS[L] = { s, roots: F.map(f => f.root), fans: F.map(f => f.fan), fingers: F.map(f => f.b), thumb: [t1, t2, t3], sg: Math.sign(xA.dot(away)) || 1 };
      J['finger' + L] = HANDS[L].fingers; J['thumb' + L] = HANDS[L].thumb;
      F.forEach(f => f.b.forEach((b, k) => { J[f.name + (k + 1) + L] = b; }));
      HANDS[L].thumb.forEach((b, k) => { J['thumb' + (k + 1) + L] = b; });
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
    bootGeo.translate(0, -0.2, -0.05); bootGeo.rotateY(-Math.PI / 2); bootGeo.scale(1.12, 1.05, 1.05);
    // Each leg is one skinned half of the pants, from under the waist ring to inside the boot cuff. At the top its cross
    // section is half of the briefs (a D: the briefs' ellipse cut at the middle), lower down it becomes the round thigh;
    // the middle seam stays with the torso, so the two halves always meet. Bends: hip, knee (bellows, a pad in front),
    // ankle (high up the shin: the foot turns inside the boot).
    const briefP = [[0.08, -0.27], [0.13, -0.255], [0.162, -0.22], [0.182, -0.16], [0.19, -0.08], [0.183, 0.0], [0.173, 0.06], [0.16, 0.12]];
    const rb = y => { y = Math.max(y, -0.2); for (let i = 1; i < briefP.length; i++) if (y <= briefP[i][1]) { const [r0, y0] = briefP[i - 1], [r1, y1] = briefP[i]; return r0 + (r1 - r0) * (y - y0) / (y1 - y0); } return briefP[briefP.length - 1][0]; };
    const HY = -0.13, KY = -0.61, KB = 0.11, KR = 0.1, AY = -1.17;   // a short thigh: the suit sits low and sturdy
    const thighR = y => { const u = clamp01((HY - y) / 0.48); return (0.128 - 0.02 * u) * (1 + 0.06 * Math.sin(Math.PI * u)); };
    const shinR = (y, ph) => { const u = clamp01((KY - y) / 0.5); return (0.105 - 0.02 * u) * (1 + 0.1 * Math.sin(Math.PI * u)) * (1 + 0.06 * Math.max(0, Math.cos(ph))); };
    const legR = (s, y, ph) => {
      const dx = Math.sin(ph), dz = Math.cos(ph), cx = s * 0.105, cz = -0.035;
      // the distance from the thigh's centre to the edge of the briefs' half (the ellipse, or the middle plane x = 0)
      const A = 1.26 * rb(y), Bz = 0.9 * rb(y), qa = dx * dx / (A * A) + dz * dz / (Bz * Bz), qb = 2 * (cx * dx / (A * A) + cz * dz / (Bz * Bz)), qc = cx * cx / (A * A) + cz * cz / (Bz * Bz) - 1;
      let E = (-qb + Math.sqrt(Math.max(0, qb * qb - 4 * qa * qc))) / (2 * qa);
      if (s * dx < -1e-6) E = Math.min(E, 0.105 / -(s * dx));
      const m = sstep(-0.14, -0.36, y), d = y - KY;
      let r = E + ((thighR(y) + (shinR(y, ph) - thighR(y)) * sstep(KB, -KB, d)) * (1 + 0.13 * Math.exp(-((d / 0.085) ** 2))) - E) * m;   // a full knee
      if (s * dx < -1e-6) r = Math.min(r, (0.105 - 0.004 * m) / -(s * dx));   // the thighs press together, never through
      const pm = Math.abs(d) < KB ? sstep(0.3, 0.75, -Math.cos(ph)) * Math.exp(-((d / 0.08) ** 2)) : 0;   // the knee pad, -z
      const base = r * (1 + 0.1 * ridgeS(d, KB) * (1 - pm)) + KR * 0.3 * pm;
      return { r: base + fold(cx + base * dx, y, cz + base * dz, Math.max(bandEnv(d, KB), 1 - sstep(-0.05, -0.2, y))), base, pm, m };
    };
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const hp = bone(body, s * 0.105, HY, -0.035), kn = bone(hp, 0, KY - HY, 0.02), an = bone(kn, 0, AY - KY, -0.02);
      let leg = null;
      const hpH1 = helper(hp, 1 / 3), hpH2 = helper(hp, 2 / 3);
      const knH1 = helper(kn, 1 / 3, src => { if (leg) leg.morphTargetInfluences[0] = sstep(0, 2.2, -src.rotation.x); }), knH2 = helper(kn, 2 / 3);
      const anH = helper(an, 0.5);
      const rows = span([0.07, -0.1, 0.008], [-0.1, -0.3, 0.0025], [-0.3, KY + KB, 0.008], [KY + KB, KY - KB, 0.0025], [KY - KB, AY + 0.24, 0.008], [AY + 0.24, AY + 0.14, 0.004], [AY + 0.14, AY + 0.09, 0.008]).map(y => ({
        y, cx: s * 0.105, cz: -0.035, r: ph => legR(s, y, ph).r, col: ph => bendCol(y - KY, KB, legR(s, y, ph).pm),
        w: (ph, r) => {
          if (y > -0.1) return [[body, 1]];
          if (y > -0.3) {   // the hip: the middle seam is pinned to the torso until the leg is round
            const x = s * 0.105 + r * Math.sin(ph), m = legR(s, y, ph).m, p = sstep(0, 0.035, s * x) * (1 - m) + m;
            return spread([body, hpH1, hpH2, hp], cubic(clamp01((-0.1 - y) / 0.2) * p));
          }
          if (y > KY + KB) return [[hp, 1]];
          if (y > KY - KB) return spread([hp, knH1, knH2, kn], cubic((KY + KB - y) / (2 * KB)));
          if (y > AY + 0.24) return [[kn, 1]];
          if (y > AY + 0.14) return spread([kn, anH, an], quad((AY + 0.24 - y) / 0.1));
          return [[an, 1]];
        },
      }));
      leg = skinTube(rows, 56, (rw, ph, nx, ny, nz) => bendMorph(rw.y - KY, KB, KR, 1, Math.max(0, nz), Math.max(0, -nz)));
      proxy(hp, 0.25, 0.48, 0.25, -0.24); proxy(kn, 0.21, 0.5, 0.21, -0.27);
      pocket(hp, s * (legR(s, HY - 0.26, s * Math.PI / 2).base + 0.008), -0.26, 0, s * Math.PI / 2, s < 0 ? 0.1 : 0.12, 0.12, 0);   // thigh pockets (the right one wider)
      pocket(kn, s * (legR(s, KY - 0.2, s * Math.PI / 2).base + 0.008), -0.2, -0.02, s * Math.PI / 2, 0.075, 0.1, 0, 0.095);              // and a smaller one on each shin
      // the boot: the ankle pivot sits inside it, 0.127 above the sole
      an.add(mesh(lumpy(lathe([[0, -0.02], [0.094, -0.02], [0.1, 0.03], [0.092, 0.08]], 48), 0.004), fabric2, 0, 0.13, 0));   // a cloth cuff over the boot top, open above
      an.add(at(band(0.104, 0.03, 0.011), 0, 0.14, 0));
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
    const back = mesh(patch(0.085, 0.32), emblemMat, 0, 0.03, 0.137); pack.add(back);                                                // on the backpack flap

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
      hand('both', 'relaxed');   // every finger bone reset: a gesture never lingers into a scene that only calls pose(t)
    }

    // Hand shapes: per finger (index to little) [MCP, PIP, DIP] flexion (+x curls toward the palm), the spread (times
    // the rest fan), the thumb [CMC flex, CMC abduction (+ away from the index), MCP, IP].
    const fist4 = [[1.35, 1.55, 0.7], [1.4, 1.6, 0.7], [1.4, 1.6, 0.7], [1.35, 1.55, 0.7]], open4 = [0, 1, 2, 3].map(() => [0.02, 0.03, 0.02]);
    const SHAPES = {
      relaxed: { f: [[0.35, 0.5, 0.28], [0.45, 0.6, 0.32], [0.55, 0.7, 0.36], [0.68, 0.8, 0.42]], spread: 1, th: [0.2, 0.05, 0.2, 0.25] },
      open: { f: [[0.06, 0.12, 0.08], [0.05, 0.1, 0.07], [0.09, 0.14, 0.09], [0.15, 0.2, 0.12]], spread: 1.45, th: [-0.1, 0.4, 0.15, 0.22] },   // never ruler-straight
      fist: { f: fist4, spread: 0.2, th: [0.5, -0.1, 0.45, 0.45] },
      point: { f: [[0.05, 0.05, 0.03], ...fist4.slice(1)], spread: 0.5, th: [0.5, -0.1, 0.45, 0.45] },
      thumbsUp: { f: fist4, spread: 0.2, th: [-0.35, 0.35, -0.1, 0] },
      wave: { f: [[0.04, 0.08, 0.05], [0.03, 0.07, 0.05], [0.06, 0.1, 0.07], [0.1, 0.15, 0.09]], spread: 1.7, th: [-0.05, 0.45, 0.12, 0.18] },
      grip: { f: [0, 1, 2, 3].map(() => [0.9, 1.1, 0.6]), spread: 0.4, th: [0.45, 0, 0.35, 0.3] },
      ok: { f: [[0.95, 1.05, 0.65], [0.1, 0.15, 0.1], [0.18, 0.22, 0.12], [0.3, 0.32, 0.18]], spread: 1.1, th: [0.2, 0.2, 0.3, 0.4] },   // the thumb found by search: its tip meets the index tip
    };
    // a.hand(side 'L' | 'R' | 'both', shape name | {f, spread, th} | curl number, k): turns the fingers from where they
    // are toward the shape by k (so it layers after pose(t) and can blend between shapes over time)
    function hand(side = 'both', shape = 'relaxed', k = 1) {
      if (typeof shape === 'number') return handCurl(side, shape, 1, shape, k);
      const S = typeof shape === 'string' ? SHAPES[shape] : shape, to = (r, ax, v) => { r[ax] += (v - r[ax]) * k; };
      for (const L of side === 'both' ? ['L', 'R'] : [side]) {
        const H = HANDS[L];
        H.fingers.forEach((f, i) => {
          to(H.roots[i].rotation, 'z', H.s * H.fans[i] * S.spread);
          f.forEach((b, j) => { to(b.rotation, 'x', j === 1 ? Math.min(1.6, S.f[i][j]) : S.f[i][j]); to(b.rotation, 'y', 0); to(b.rotation, 'z', 0); });   // past 1.6 the middle joint pinches
        });
        const [t1, t2, t3] = H.thumb;
        to(t1.rotation, 'x', S.th[0]); to(t1.rotation, 'y', 0); to(t1.rotation, 'z', S.th[1] * H.sg);
        to(t2.rotation, 'x', S.th[2]); to(t3.rotation, 'x', S.th[3]);
      }
    }
    // a.handCurl(side, curl 0 (open) .. 1 (fist), spread, thumb curl, k)
    function handCurl(side = 'both', c = 0, spread = 1, tc = c, k = 1) {
      const p = Math.min(1.6, 0.03 + 1.55 * c), o = SHAPES.open.th, fi = SHAPES.fist.th;
      hand(side, { f: [0, 1, 2, 3].map(() => [0.02 + 1.35 * c, p, 0.6 * p]), spread, th: o.map((v, i) => v + (fi[i] - v) * tc) }, k);
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
      group, joints: J, materials: mats, pose, rim, light, aim, lights, ready, hand, handCurl, hands: HANDS, shapes: SHAPES, visor: VIS,
      setTint(r, g, b) { const c = new THREE.Color(r, g, b); for (const m of mats) m.color.copy(m.userData.base).multiply(c); },
      // opaque until it fades: a transparent material lets the parts behind show through
      setOpacity(x) { glowK = x; for (const g of glows) g.material.opacity = 0.85 * x; const tr = x < 0.999; for (const m of mats) { if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; } m.opacity = x; m.depthWrite = !tr; } },
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
