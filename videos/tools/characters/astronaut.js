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
// Joints are plain groups (a.joints.shoulderL, elbowL, wristL, hipL, kneeL, ankleL, … head, body).
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
    const cover = M({ color: 0xece8de, roughness: 0.92, metalness: 0, map: plainMap, bumpMap: plainBump, bumpScale: 0.04 });        // the cloth cover over the backpack
    const shell = M({ color: 0xeceae3, roughness: 0.6, metalness: 0.0 });          // hard parts
    const metal = M({ color: 0xc3c7cc, roughness: 0.28, metalness: 0.85 });          // bearings, valves
    const grey = M({ color: 0x6d7076, roughness: 0.6, metalness: 0.2 });
    const dark = M({ color: 0x26282c, roughness: 0.75, metalness: 0.1 });
    const visor = M({ color: 0xe0a640, roughness: 0.08, metalness: 1.0 });
    const lens = M({ color: 0x111316, roughness: 0.1, metalness: 0.6 });
    const blue = M({ color: 0x0057b7, roughness: 0.85 }), yellow = M({ color: 0xffd500, roughness: 0.85 });

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
    // a puffy limb segment hanging down from its joint: radius r0 → r1 over len, bulging in the middle, rounded ends
    function limb(len, r0, r1, bulge, ph = 0) {
      const p = [];
      for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; p.push([r0 * Math.sin(a), r0 * 0.45 * Math.cos(a)]); }
      for (let i = 1; i < 30; i++) {
        const u = i / 30, r = (r0 + (r1 - r0) * u) * (1 + bulge * Math.sin(Math.PI * u)) * (1 - 0.04 * Math.pow(Math.abs(Math.sin(u * 11 + ph)), 6) * Math.sin(Math.PI * u) + 0.012 * Math.sin(u * 29 + 2 * ph));
        p.push([r, -u * len]);
      }
      for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; p.push([r1 * Math.cos(a), -len - r1 * 0.45 * Math.sin(a)]); }
      return lumpy(lathe(p.reverse(), 64), r0 * 0.085);
    }
    // bellows at a bend: n soft ridges
    function bellows(len, r, n) {
      const p = [[1e-4, len / 2 + r * 0.3]];
      for (let i = 0; i <= 40; i++) { const u = i / 40; p.push([r * (0.93 + 0.1 * Math.cos(2 * Math.PI * n * u)), len / 2 - u * len]); }
      p.push([1e-4, -len / 2 - r * 0.3]);
      return lumpy(lathe(p.reverse(), 64), r * 0.08, 20);
    }
    let seed = 0;
    function lumpy(geo, amp, f = 14) {
      geo.computeVertexNormals();
      const p = geo.attributes.position, n = geo.attributes.normal, o = (seed += 3.7);
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const d = amp * ((vnoise(x * f + o, y * f * 2.2, z * f) - 0.5) * 1.4 + (vnoise(x * f * 2.6, y * f * 5 + o, z * f * 2.6) - 0.5) * 0.6);
        p.setXYZ(i, x + n.getX(i) * d, y + n.getY(i) * d, z + n.getZ(i) * d);
      }
      geo.computeVertexNormals(); return geo;
    }
    const shadowed = o => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });

    const group = new THREE.Group();
    const body = joint(group, 0, 0, 0);
    const J = { body };

    /* torso */
    // hard upper torso: a shell wider than deep, from the waist bearing to the neck ring
    const hut = mesh(lathe([[0, 0.1], [0.165, 0.1], [0.19, 0.17], [0.215, 0.27], [0.232, 0.38], [0.236, 0.46], [0.222, 0.53], [0.185, 0.585], [0.145, 0.615], [0, 0.625]]), shell);
    hut.scale.set(1.26, 1, 0.9); body.add(hut);
    // lower torso / briefs: soft fabric, the waist bearing on top
    const brief = mesh(lumpy(lathe([[0, -0.25], [0.1, -0.25], [0.15, -0.23], [0.178, -0.17], [0.19, -0.08], [0.192, 0.04], [0.178, 0.1], [0, 0.11]], 64), 0.008, 10), fabric);   // one piece down to the top of the thighs: the legs come out of it
    brief.scale.set(1.32, 1, 1.0); body.add(brief);
    const waist = at(ringY(0.183, 0.022, metal), 0, 0.105, 0); waist.scale.set(1.33, 0.97, 1); body.add(waist);
    const waist2 = at(ringY(0.18, 0.014, grey), 0, 0.075, 0); waist2.scale.set(1.32, 0.97, 1); body.add(waist2);
    // chest control box with two hoses to the backpack
    const dcm = mesh(rbox(0.3, 0.12, 0.11, 0.025), shell, 0, 0.33, -0.25); dcm.rotation.x = 0.2; body.add(dcm);
    for (const [x, y] of [[-0.08, 0.02], [0.02, 0.02], [0.1, 0.0]]) { const k = mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.02, 14), metal, x, 0.33 + y, -0.31); k.rotation.x = Math.PI / 2 + 0.2; body.add(k); }
    for (const s of [-1, 1]) {
      const c = new THREE.CatmullRomCurve3([new THREE.Vector3(s * 0.14, 0.31, -0.28), new THREE.Vector3(s * 0.27, 0.29, -0.22), new THREE.Vector3(s * 0.325, 0.3, -0.04), new THREE.Vector3(s * 0.3, 0.31, 0.12), new THREE.Vector3(s * 0.25, 0.32, 0.2)]);
      body.add(new THREE.Mesh(new THREE.TubeGeometry(c, 40, 0.016, 10, false), s < 0 ? grey : dark));
    }

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
    const head = joint(body, 0, 0.625, -0.01); J.head = head;
    head.add(at(ringY(0.148, 0.026, metal), 0, 0, 0));
    head.add(at(ringY(0.16, 0.012, grey), 0, -0.03, 0));
    const helmet = mesh(new THREE.SphereGeometry(0.188, 56, 40), shell, 0, 0.16, 0.0); helmet.scale.set(1, 1.03, 1.06); head.add(helmet);
    // the visor covers the front (-z) of the helmet: phi centred on 1.5π in three's sphere parametrisation
    const vis = mesh(new THREE.SphereGeometry(0.192, 56, 40, Math.PI * 1.13, Math.PI * 0.74, Math.PI * 0.2, Math.PI * 0.46), visor, 0, 0.16, 0.0);
    vis.scale.set(1, 1.03, 1.06); head.add(vis);
    const brow = mesh(new THREE.SphereGeometry(0.195, 56, 20, Math.PI * 1.1, Math.PI * 0.8, Math.PI * 0.16, Math.PI * 0.05), shell, 0, 0.16, 0); brow.scale.set(1, 1.03, 1.06); head.add(brow);
    for (const s of [-1, 1]) {
      const lamp = joint(head, s * 0.184, 0.19, -0.04); lamp.scale.setScalar(0.85);
      lamp.add(mesh(rbox(0.05, 0.06, 0.13, 0.015), shell));
      const ln = mesh(new THREE.CircleGeometry(0.019, 20), lens, 0, 0.004, -0.0661); ln.rotation.y = Math.PI; lamp.add(ln);
      lamp.add(mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.05, 8), grey, 0, -0.04, 0.03));
    }

    /* arms */
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const sh = joint(body, s * 0.31, 0.49, 0);
      const bulb = mesh(lumpy(new THREE.SphereGeometry(0.1, 40, 30), 0.006), fabric); bulb.scale.set(1, 1.05, 1.05); sh.add(bulb);
      sh.add(at(ringX(0.092, 0.02, metal), -s * 0.035, 0, 0));
      const upper = mesh(limb(0.27, 0.09, 0.08, 0.06, s), fabric, 0, -0.06, 0); sh.add(upper);
      sh.add(at(ringY(0.088, 0.006, grey), 0, -0.2, 0));                                     // a seam / restraint line
      if (s < 0) {   // the flag on the outside of the left upper arm
        const f = joint(sh, -0.094, -0.13, 0); f.rotation.y = -Math.PI / 2;
        f.add(mesh(new THREE.PlaneGeometry(0.075, 0.025), blue, 0, 0.0125, 0), mesh(new THREE.PlaneGeometry(0.075, 0.025), yellow, 0, -0.0125, 0));
      }
      const el = joint(sh, 0, -0.37, 0);
      el.add(mesh(bellows(0.1, 0.08, 3), fabric2));
      const epad = mesh(new THREE.SphereGeometry(0.082, 32, 20, Math.PI * 0.25, Math.PI * 0.5, Math.PI * 0.3, Math.PI * 0.4), fabric2, 0, -0.01, 0); epad.scale.set(1.08, 1.2, 1.12); el.add(epad);   // and over the back of the elbow
      el.add(mesh(limb(0.23, 0.078, 0.066, 0.05, 2 + s), fabric, 0, -0.055, 0));
      const wr = joint(el, 0, -0.33, 0);
      wr.add(at(ringY(0.07, 0.017, metal), 0, 0.012, 0));
      wr.add(mesh(new THREE.CylinderGeometry(0.072, 0.066, 0.055, 24), dark, 0, -0.02, 0));     // gauntlet cuff
      const hand = joint(wr, 0, -0.05, 0);
      hand.add(mesh(rbox(0.095, 0.1, 0.048, 0.022), dark, 0, -0.045, 0));                         // palm
      for (let i = 0; i < 4; i++) {
        const fg = joint(hand, (i - 1.5) * 0.023 * -s, -0.095, 0);
        fg.rotation.x = 0.35 + 0.1 * i;
        fg.add(mesh(new THREE.CapsuleGeometry(0.0115, 0.04 + (i === 1 || i === 2 ? 0.008 : 0), 6, 12), dark, 0, -0.03, 0));
      }
      const th = joint(hand, s * 0.05, -0.04, -0.01); th.rotation.set(0.3, 0, -s * 0.7);
      th.add(mesh(new THREE.CapsuleGeometry(0.013, 0.035, 6, 12), dark, 0, -0.03, 0));
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
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const hp = joint(body, s * 0.105, -0.13, -0.035);
      // thigh: full at the top (it starts inside the briefs), narrowing to the knee
      // the seat: cloth flaring from inside the briefs and narrowing into the thigh, so the leg grows out of the torso
      const seat = mesh(lumpy(lathe([[0, -0.24], [0.124, -0.24], [0.132, -0.17], [0.15, -0.09], [0.168, -0.02], [0.17, 0.04], [0.15, 0.09], [0, 0.1]], 64), 0.006, 10), fabric, -s * 0.02, 0, 0.01);
      seat.scale.set(1.0, 1, 1.05); hp.add(seat);
      hp.add(mesh(limb(0.37, 0.124, 0.096, 0.06, 3 * s), fabric, 0, -0.09, 0));
      hp.add(at(ringY(0.116, 0.006, grey), 0, -0.24, 0));                                     // a seam / restraint line
      const kn = joint(hp, 0, -0.5, 0);
      kn.add(mesh(bellows(0.11, 0.1, 3), fabric2));
      const pad = mesh(lumpy(new THREE.SphereGeometry(0.104, 40, 24, Math.PI * 1.25, Math.PI * 0.5, Math.PI * 0.3, Math.PI * 0.4), 0.004), fabric2, 0, -0.02, 0); pad.scale.set(1.08, 1.25, 1.12); kn.add(pad);   // a padded patch over the knee
      // shin with a calf: fuller just below the knee at the back, slimmer to the ankle
      const shin = mesh(limb(0.38, 0.098, 0.08, 0.1, 1 - s), fabric, 0, -0.06, 0.008); shin.scale.set(1, 1, 1.06); kn.add(shin);
      const an = joint(kn, 0, -0.5, 0);
      an.add(mesh(lumpy(lathe([[0, -0.02], [0.094, -0.02], [0.1, 0.03], [0.092, 0.08], [0, 0.085]], 48), 0.004), fabric2, 0, 0.02, 0));   // a cloth cuff over the boot top
      an.add(at(ringY(0.096, 0.015, metal), 0, 0.03, 0));
      an.add(mesh(bootGeo, shell, 0, 0.02, 0));
      an.add(mesh(rbox(0.175, 0.04, 0.34, 0.016), dark, 0, -0.2, -0.078));                      // sole
      for (let k = 0; k < 6; k++) an.add(mesh(new THREE.BoxGeometry(0.17, 0.01, 0.018), grey, 0, -0.222, 0.06 - k * 0.055));   // tread
      an.add(mesh(new THREE.BoxGeometry(0.185, 0.024, 0.07), grey, 0, -0.09, 0.02));               // strap
      J['hip' + L] = hp; J['knee' + L] = kn; J['ankle' + L] = an;
    }

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
    const back = mesh(patch(0.085, 0.35), emblemMat, 0, 0.03, 0.127); pack.add(back);                                                // on the backpack flap

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
      setOpacity(x) { const tr = x < 0.999; for (const m of mats) { if (m.transparent !== tr) { m.transparent = tr; m.needsUpdate = true; } m.opacity = x; m.depthWrite = !tr; } },
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
