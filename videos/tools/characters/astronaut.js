// The Nebozvid astronaut: a character built in code (three.js), so any video can use it (scene.json:
// "include": ["characters/astronaut.js"]). Modelled after real spacewalk suits: a hard upper torso, a big life-support
// backpack with rounded edges, puffy fabric arms and legs with bellows at the elbows and knees, bearings at the
// shoulders, waist and wrists, gloves with fingers, heavy boots, a helmet with side lamps and a gold visor, hoses to a
// control box on the chest, and a small Ukrainian flag on the left shoulder. The fabric has fine folds (a procedural
// bump in the shader); metal and the visor reflect an environment map; the figure shades itself (shadow map).
//
//   const a = window.__makeAstronaut(THREE);         // a.group: ~1.9 units tall, pelvis at the origin, facing -z
//   a.pose(t);                                        // the free-fall idle at time t (s): limbs drift slowly
//   a.setTint(r, g, b); a.setOpacity(x);              // colour and fade for the whole figure
//   a.rim.color.value.set(…)                          // rim light on the edges (light from behind the figure)
//   const env = window.__astronautEnv(THREE, renderer, { warm: dirVector });   // reflections: dark space, a warm glow
//   const key = a.keyLight(color, intensity);         // a shadow-casting light that follows the figure (a.aimKey(dir))
//
// Joints are plain groups (a.joints.shoulderL, elbowL, wristL, hipL, kneeL, ankleL, … head, body).
(() => {
  // value-noise folds for the fabric, and a bump that tilts the normal by the height's screen-space slope
  const FOLDS = `
    varying vec3 vObj;
    uniform float foldK;
    float fh(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
    float fn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(fh(i), fh(i + vec3(1,0,0)), f.x), mix(fh(i + vec3(0,1,0)), fh(i + vec3(1,1,0)), f.x), f.y),
                 mix(mix(fh(i + vec3(0,0,1)), fh(i + vec3(1,0,1)), f.x), mix(fh(i + vec3(0,1,1)), fh(i + vec3(1,1,1)), f.x), f.y), f.z); }
    float folds(vec3 p){
      // folds run round the limbs (the limb axis is local y): stretched noise, plus fine weave
      float a = fn(vec3(p.x * 9.0, p.y * 34.0, p.z * 9.0)) * 0.65 + fn(vec3(p.x * 18.0, p.y * 70.0, p.z * 18.0)) * 0.35;
      return a * a + 0.04 * fn(p * 400.0);
    }
    vec3 foldNormal(vec3 pos, vec3 n, float h){
      vec3 sx = dFdx(pos), sy = dFdy(pos); vec2 d = vec2(dFdx(h), dFdy(h)) * foldK;
      vec3 r1 = cross(sy, n), r2 = cross(n, sx); float det = dot(sx, r1);
      return normalize(abs(det) * n - sign(det) * (d.x * r1 + d.y * r2));
    }`;

  window.__makeAstronaut = (THREE) => {
    const mats = [];
    const rim = { color: { value: new THREE.Color(0, 0, 0) }, power: { value: 2.2 } };
    const M = (o, fold = 0) => {
      const m = new THREE.MeshStandardMaterial(Object.assign({ transparent: true }, o));
      m.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { rimColor: rim.color, rimPower: rim.power, foldK: { value: fold } });
        if (fold) {
          sh.vertexShader = 'varying vec3 vObj;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vObj = position;');
          sh.fragmentShader = FOLDS + sh.fragmentShader.replace('#include <normal_fragment_maps>',
            '#include <normal_fragment_maps>\n  float hgt = folds(vObj);\n  normal = foldNormal(-vViewPosition, normal, hgt);\n  diffuseColor.rgb *= 0.9 + 0.1 * hgt;');
        }
        sh.fragmentShader = 'uniform vec3 rimColor; uniform float rimPower;\n' + sh.fragmentShader.replace('#include <dithering_fragment>',
          '#include <dithering_fragment>\n  float fr = pow(1.0 - clamp(dot(normalize(vNormal), normalize(vViewPosition)), 0.0, 1.0), rimPower);\n  gl_FragColor.rgb += rimColor * diffuseColor.rgb * fr;');
      };
      m.userData.base = m.color.clone(); mats.push(m); return m;
    };
    const fabric = M({ color: 0xebe7dd, roughness: 0.93, metalness: 0 }, 1.0);
    const fabric2 = M({ color: 0xd9d5cb, roughness: 0.95, metalness: 0 }, 1.4);      // a shade darker: bellows, gaskets
    const cover = M({ color: 0xe6e2d8, roughness: 0.9, metalness: 0 }, 0.45);        // the cloth cover over the backpack
    const shell = M({ color: 0xeeebe4, roughness: 0.58, metalness: 0.0 });          // hard parts
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
        const u = i / 30, r = (r0 + (r1 - r0) * u) * (1 + bulge * Math.sin(Math.PI * u)) * (1 + 0.018 * Math.sin(u * 23 + ph) * Math.sin(Math.PI * u));
        p.push([r, -u * len]);
      }
      for (let i = 0; i <= 6; i++) { const a = i / 6 * Math.PI / 2; p.push([r1 * Math.cos(a), -len - r1 * 0.45 * Math.sin(a)]); }
      return lathe(p.reverse());
    }
    // bellows at a bend: n soft ridges
    function bellows(len, r, n) {
      const p = [[1e-4, len / 2 + r * 0.3]];
      for (let i = 0; i <= 40; i++) { const u = i / 40; p.push([r * (0.93 + 0.1 * Math.cos(2 * Math.PI * n * u)), len / 2 - u * len]); }
      p.push([1e-4, -len / 2 - r * 0.3]);
      return lathe(p.reverse());
    }
    const shadowed = o => o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });

    const group = new THREE.Group();
    const body = joint(group, 0, 0, 0);
    const J = { body };

    /* torso */
    // hard upper torso: a shell wider than deep, from the waist bearing to the neck ring
    const hut = mesh(lathe([[0, 0.1], [0.165, 0.1], [0.19, 0.17], [0.215, 0.27], [0.232, 0.38], [0.236, 0.46], [0.222, 0.53], [0.185, 0.585], [0.145, 0.615], [0, 0.625]].reverse()), shell);
    hut.scale.set(1.36, 1, 0.94); body.add(hut);
    // lower torso / briefs: soft fabric, the waist bearing on top
    const brief = mesh(lathe([[0, -0.2], [0.11, -0.2], [0.16, -0.15], [0.185, -0.05], [0.188, 0.04], [0.178, 0.1], [0, 0.11]].reverse()), fabric);
    brief.scale.set(1.3, 1, 0.98); body.add(brief);
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
    const pack = joint(body, 0, 0.36, 0.29);
    pack.add(mesh(rbox(0.56, 0.68, 0.24, 0.085), cover));
    pack.add(mesh(rbox(0.5, 0.15, 0.2, 0.05), shell, 0, 0.36, -0.01));                  // top cover, a little set apart
    pack.add(mesh(new THREE.BoxGeometry(0.52, 0.012, 0.21), grey, 0, 0.285, 0));        // the seam under it
    pack.add(mesh(rbox(0.42, 0.34, 0.03, 0.03), cover, 0, 0.02, 0.115));                 // a padded flap on the back
    for (const s of [-1, 1]) pack.add(mesh(new THREE.BoxGeometry(0.035, 0.6, 0.012), grey, s * 0.17, -0.02, 0.124));   // straps over it
        pack.add(mesh(rbox(0.1, 0.06, 0.02, 0.008), grey, 0, -0.24, 0.13));
    for (const s of [-1, 1]) {
      const h = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.011, 10, 24, Math.PI), grey);   // handles on the top edges
      h.position.set(s * 0.19, 0.44, 0.0); pack.add(h);
      pack.add(mesh(new THREE.CylinderGeometry(0.024, 0.024, 0.04, 16), metal, s * 0.2, -0.36, 0.0));    // valves underneath
      pack.add(mesh(new THREE.BoxGeometry(0.02, 0.5, 0.2), grey, s * 0.285, 0.0, 0.0));                  // side rails
    }

    /* neck ring, helmet with side lamps and the gold visor */
    const head = joint(body, 0, 0.625, -0.01); J.head = head;
    head.add(at(ringY(0.155, 0.03, metal), 0, 0, 0));
    head.add(at(ringY(0.16, 0.012, grey), 0, -0.03, 0));
    const helmet = mesh(new THREE.SphereGeometry(0.205, 56, 40), shell, 0, 0.16, 0.0); helmet.scale.set(1, 1.03, 1.06); head.add(helmet);
    // the visor covers the front (-z) of the helmet: phi centred on 1.5π in three's sphere parametrisation
    const vis = mesh(new THREE.SphereGeometry(0.209, 56, 40, Math.PI * 1.13, Math.PI * 0.74, Math.PI * 0.2, Math.PI * 0.46), visor, 0, 0.16, 0.0);
    vis.scale.set(1, 1.03, 1.06); head.add(vis);
    const brow = mesh(new THREE.SphereGeometry(0.212, 56, 20, Math.PI * 1.1, Math.PI * 0.8, Math.PI * 0.16, Math.PI * 0.05), shell, 0, 0.16, 0); brow.scale.set(1, 1.03, 1.06); head.add(brow);
    for (const s of [-1, 1]) {
      const lamp = joint(head, s * 0.2, 0.2, -0.04);
      lamp.add(mesh(rbox(0.05, 0.06, 0.13, 0.015), shell));
      const ln = mesh(new THREE.CircleGeometry(0.019, 20), lens, 0, 0.004, -0.0661); ln.rotation.y = Math.PI; lamp.add(ln);
      lamp.add(mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.05, 8), grey, 0, -0.04, 0.03));
    }

    /* arms */
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const sh = joint(body, s * 0.34, 0.49, 0);
      const bulb = mesh(new THREE.SphereGeometry(0.11, 32, 24), fabric); bulb.scale.set(1, 1.05, 1.05); sh.add(bulb);
      sh.add(at(ringX(0.1, 0.022, metal), -s * 0.035, 0, 0));
      const upper = mesh(limb(0.24, 0.1, 0.088, 0.07, s), fabric, 0, -0.06, 0); sh.add(upper);
      if (s < 0) {   // the flag on the outside of the left upper arm
        const f = joint(sh, -0.103, -0.13, 0); f.rotation.y = -Math.PI / 2;
        f.add(mesh(new THREE.PlaneGeometry(0.075, 0.025), blue, 0, 0.0125, 0), mesh(new THREE.PlaneGeometry(0.075, 0.025), yellow, 0, -0.0125, 0));
      }
      const el = joint(sh, 0, -0.34, 0);
      el.add(mesh(bellows(0.11, 0.088, 3), fabric2));
      el.add(mesh(limb(0.2, 0.086, 0.074, 0.05, 2 + s), fabric, 0, -0.06, 0));
      const wr = joint(el, 0, -0.3, 0);
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
    const bootShape = new THREE.Shape();
    [[0.065, 0.0], [-0.17, 0.0], [-0.215, 0.02], [-0.215, 0.055], [-0.17, 0.095], [-0.075, 0.13], [-0.07, 0.2], [0.075, 0.2], [0.08, 0.03]]
      .forEach(([z, y], i) => i ? bootShape.lineTo(z, y) : bootShape.moveTo(z, y));
    const bootGeo = new THREE.ExtrudeGeometry(bootShape, { depth: 0.1, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.022, bevelSegments: 5, curveSegments: 8 });
    bootGeo.translate(0, -0.2, -0.05); bootGeo.rotateY(-Math.PI / 2); bootGeo.scale(1.25, 1.15, 1.12); bootGeo.computeVertexNormals();
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const hp = joint(body, s * 0.115, -0.12, 0);
      hp.add(mesh(limb(0.34, 0.13, 0.108, 0.07, 3 * s), fabric, 0, -0.03, 0));
      const kn = joint(hp, 0, -0.44, 0);
      kn.add(mesh(bellows(0.13, 0.108, 3), fabric2));
      kn.add(mesh(limb(0.3, 0.106, 0.094, 0.06, 1 - s), fabric, 0, -0.07, 0));
      const an = joint(kn, 0, -0.42, 0);
      an.add(at(ringY(0.094, 0.018, metal), 0, 0.02, 0));
      an.add(mesh(bootGeo, shell, 0, 0.02, 0));
      an.add(mesh(rbox(0.19, 0.035, 0.35, 0.014), dark, 0, -0.215, -0.08));                      // sole
      an.add(mesh(new THREE.BoxGeometry(0.2, 0.025, 0.07), grey, 0, -0.1, 0.02));               // strap
      J['hip' + L] = hp; J['knee' + L] = kn; J['ankle' + L] = an;
    }

    shadowed(group);

    // The free-fall rest pose (arms afloat, knees bent), the two sides a little different, each joint drifting slowly.
    const w = (t, p, ph) => Math.sin(t * 2 * Math.PI / p + ph);
    function pose(t) {
      for (const s of [-1, 1]) {
        const L = s < 0 ? 'L' : 'R', ph = s < 0 ? 0 : 1.9, a = s < 0 ? 1 : -1;
        J['shoulder' + L].rotation.set(0.35 + 0.08 * a + 0.09 * w(t, 5.3, ph), 0.1 * s, s * (1.05 + 0.1 * a + 0.1 * w(t, 6.1, ph + 1)));
        J['elbow' + L].rotation.set(0.75 + 0.12 * w(t, 4.4, ph + 2), 0, 0);
        J['wrist' + L].rotation.set(0.2 + 0.12 * w(t, 3.7, ph), 0.3 * s, s * 0.15);
        J['hip' + L].rotation.set(0.38 + 0.12 * a + 0.08 * w(t, 6.7, ph + 0.5), 0, s * (0.14 + 0.04 * w(t, 7.3, ph)));
        J['knee' + L].rotation.set(-0.7 - 0.15 * a + 0.1 * w(t, 5.9, ph + 2.6), 0, 0);
        J['ankle' + L].rotation.set(0.3 + 0.05 * w(t, 4.9, ph), 0, 0);
      }
      J.head.rotation.set(-0.1 + 0.04 * w(t, 8.1, 0.3), 0.05 * w(t, 9.7, 1), 0);
      J.body.rotation.set(0.1 + 0.03 * w(t, 7.7, 0), 0, 0.03 * w(t, 11.3, 2));
    }
    pose(0);

    // a shadow-casting key light that keeps the figure inside its shadow camera
    let key = null;
    const keyDir = new THREE.Vector3(0, 0.6, -1).normalize();
    function keyLight(color, intensity) {
      key = new THREE.DirectionalLight(color, intensity);
      key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.01;
      Object.assign(key.shadow.camera, { left: -1.3, right: 1.3, top: 1.3, bottom: -1.3, near: 0.1, far: 10 });
      key.shadow.radius = 3;
      return key;
    }
    return {
      group, joints: J, materials: mats, pose, rim, keyLight,
      aimKey(dir) {
        if (dir) keyDir.copy(dir).normalize();
        if (!key) return;
        group.updateMatrixWorld();
        const c = group.getWorldPosition(new THREE.Vector3());
        key.position.copy(c).addScaledVector(keyDir, 4); key.target.position.copy(c); key.target.updateMatrixWorld();
      },
      setTint(r, g, b) { const c = new THREE.Color(r, g, b); for (const m of mats) m.color.copy(m.userData.base).multiply(c); },
      setOpacity(x) { for (const m of mats) { m.opacity = x; m.depthWrite = x > 0.99; } },
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
