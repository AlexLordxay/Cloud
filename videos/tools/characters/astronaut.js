// The Nebozvid astronaut: a small character built from three.js shapes, so any video can use it (scene.json:
// "include": ["characters/astronaut.js"]). A white suit after the real ones (hard torso, life-support backpack,
// bearings at the shoulders, waist and wrists, a gold visor), a little Ukrainian flag on the left shoulder.
//
//   const a = window.__makeAstronaut(THREE);   // a.group: ~1.8 units tall, pelvis at the origin, facing -z
//   a.pose(t);                                  // the floating idle at time t (s): limbs drift slowly, as in free fall
//   a.setTint(r, g, b); a.setOpacity(x);        // colour and fade for the whole figure
//   a.rim.color.value.set(…)                    // rim light on the edges (light from behind the figure)
//
// Joints are plain groups (a.joints.shoulderL, elbowL, hipL, kneeL, … , head, body) for scenes that want their own poses.
(() => {
  window.__makeAstronaut = (THREE) => {
    const mats = [];
    // a rim light: light from behind the figure (e.g. a glowing disc ahead of it) catching its edges
    const rim = { color: { value: new THREE.Color(0, 0, 0) }, power: { value: 2.0 } };
    const M = (o) => {
      const m = new THREE.MeshStandardMaterial(Object.assign({ transparent: true }, o));
      m.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { rimColor: rim.color, rimPower: rim.power });
        sh.fragmentShader = 'uniform vec3 rimColor; uniform float rimPower;\n' + sh.fragmentShader.replace('#include <dithering_fragment>',
          '#include <dithering_fragment>\n  float fr = pow(1.0 - clamp(dot(normalize(vNormal), normalize(vViewPosition)), 0.0, 1.0), rimPower);\n  gl_FragColor.rgb += rimColor * diffuseColor.rgb * fr;');
      };
      m.userData.base = m.color.clone(); mats.push(m); return m;
    };
    const suit = M({ color: 0xece8df, roughness: 0.9, metalness: 0 });
    const shell = M({ color: 0xf2f1ec, roughness: 0.38, metalness: 0.05 });
    const ring = M({ color: 0xb4b9bf, roughness: 0.4, metalness: 0.25 });
    const dark = M({ color: 0x34373d, roughness: 0.7, metalness: 0.1 });
    const visor = M({ color: 0xd8a446, roughness: 0.2, metalness: 0.45, emissive: 0x3a2508 });
    const blue = M({ color: 0x0057b7, roughness: 0.8 }), yellow = M({ color: 0xffd500, roughness: 0.8 });

    const mesh = (geo, mat, x = 0, y = 0, z = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); return m; };
    const cap = (r, len, mat) => new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 8, 20), mat);
    const torus = (R, r, mat) => { const m = new THREE.Mesh(new THREE.TorusGeometry(R, r, 10, 40), mat); m.rotation.x = Math.PI / 2; return m; };
    const at = (m, x, y, z) => { m.position.set(x, y, z); return m; };
    const joint = (parent, x, y, z) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };

    const group = new THREE.Group();
    const body = joint(group, 0, 0, 0);

    // pelvis, waist bearing, torso (hard upper torso)
    const pelvis = cap(0.16, 0.16, suit); pelvis.rotation.z = Math.PI / 2; pelvis.scale.set(1, 1, 0.85); body.add(pelvis);
    body.add(at(torus(0.185, 0.026, ring), 0, 0.12, 0));
    const torso = cap(0.22, 0.24, shell); torso.position.y = 0.36; torso.scale.set(1.3, 1, 0.95); body.add(torso);
    // a soft fabric skirt between the waist ring and the torso
    const belly = cap(0.18, 0.08, suit); belly.position.y = 0.19; belly.scale.set(1.15, 1, 0.9); body.add(belly);

    // life-support backpack on the back (+z): a rounded slab with an inset panel, a top cap and two valves
    const pack = new THREE.Group(); pack.position.set(0, 0.37, 0.27); body.add(pack);
    const slab = mesh(new THREE.BoxGeometry(0.5, 0.54, 0.19, 2, 2, 2), shell); pack.add(slab);
    const top = cap(0.095, 0.32, shell); top.rotation.z = Math.PI / 2; top.position.set(0, 0.27, 0); pack.add(top);
    const bot = cap(0.095, 0.32, shell); bot.rotation.z = Math.PI / 2; bot.position.set(0, -0.27, 0); pack.add(bot);
    for (const s of [-1, 1]) { const side = cap(0.095, 0.54, shell); side.position.set(s * 0.25, 0, 0); pack.add(side); }
    pack.add(mesh(new THREE.BoxGeometry(0.3, 0.2, 0.012), suit, 0, 0.08, 0.1));
    pack.add(mesh(new THREE.BoxGeometry(0.12, 0.05, 0.014), dark, -0.07, -0.08, 0.1));
    pack.add(mesh(new THREE.BoxGeometry(0.34, 0.03, 0.012), ring, 0, -0.19, 0.098));
    for (const s of [-1, 1]) { const v = mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.05, 16), ring, s * 0.17, 0.3, 0.02); pack.add(v); }

    // neck ring and helmet: white shell at the back, the gold visor in front
    const head = joint(body, 0, 0.62, 0);
    head.add(at(torus(0.15, 0.03, ring), 0, 0, 0));
    const helmet = mesh(new THREE.SphereGeometry(0.2, 40, 28), shell, 0, 0.15, 0.0); head.add(helmet);
    const vis = mesh(new THREE.SphereGeometry(0.203, 40, 28, Math.PI * 0.62, Math.PI * 0.76, Math.PI * 0.22, Math.PI * 0.5), visor, 0, 0.15, 0.0);
    head.add(vis);

    // arms: shoulder bearing, upper arm, elbow, forearm, wrist ring, glove
    const J = { body, head };
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const sh = joint(body, s * 0.3, 0.47, 0);
      sh.add(mesh(new THREE.SphereGeometry(0.1, 24, 16), suit));
      const brg = torus(0.085, 0.02, ring); brg.rotation.set(0, 0, Math.PI / 2); brg.position.x = s * 0.04; sh.add(brg);
      const up = cap(0.088, 0.18, suit); up.position.y = -0.16; sh.add(up);
      const el = joint(sh, 0, -0.32, 0);
      el.add(mesh(new THREE.SphereGeometry(0.084, 20, 14), suit));
      const fo = cap(0.08, 0.16, suit); fo.position.y = -0.14; el.add(fo);
      const wr = joint(el, 0, -0.29, 0);
      wr.add(torus(0.06, 0.016, ring));
      const glove = mesh(new THREE.SphereGeometry(0.06, 20, 14), suit, 0, -0.07, 0); glove.scale.set(0.9, 1.35, 0.7); wr.add(glove);
      const thumb = cap(0.02, 0.04, suit); thumb.position.set(-s * 0.045, -0.06, -0.02); thumb.rotation.z = s * 0.6; wr.add(thumb);
      wr.add(at(mesh(new THREE.CylinderGeometry(0.062, 0.058, 0.04, 20), dark), 0, -0.018, 0));
      if (s < 0) {   // the flag on the outside of the left upper arm
        const f = new THREE.Group(); f.position.set(-0.078, -0.1, 0); f.rotation.y = -Math.PI / 2; sh.add(f);
        f.add(mesh(new THREE.PlaneGeometry(0.075, 0.025), blue, 0, 0.0125, 0), mesh(new THREE.PlaneGeometry(0.075, 0.025), yellow, 0, -0.0125, 0));
      }
      J['shoulder' + L] = sh; J['elbow' + L] = el; J['wrist' + L] = wr;
    }

    // legs: hip, thigh, knee, shin, boot
    for (const s of [-1, 1]) {
      const L = s < 0 ? 'L' : 'R';
      const hp = joint(body, s * 0.1, -0.06, 0);
      const th = cap(0.108, 0.24, suit); th.position.y = -0.2; hp.add(th);
      const kn = joint(hp, 0, -0.42, 0);
      kn.add(mesh(new THREE.SphereGeometry(0.1, 20, 14), suit));
      const sn = cap(0.096, 0.22, suit); sn.position.y = -0.19; kn.add(sn);
      const an = joint(kn, 0, -0.38, 0);
      an.add(torus(0.078, 0.016, ring));
      const boot = cap(0.075, 0.12, shell); boot.rotation.x = Math.PI / 2; boot.position.set(0, -0.07, -0.05); boot.scale.set(1.05, 1, 0.85); an.add(boot);
      an.add(at(mesh(new THREE.BoxGeometry(0.15, 0.03, 0.27), dark), 0, -0.13, -0.05));
      J['hip' + L] = hp; J['knee' + L] = kn; J['ankle' + L] = an;
    }

    // a hose from the backpack round the right side to the chest
    const hose = new THREE.CatmullRomCurve3([new THREE.Vector3(0.22, 0.2, 0.2), new THREE.Vector3(0.33, 0.18, 0.05), new THREE.Vector3(0.27, 0.24, -0.16), new THREE.Vector3(0.12, 0.3, -0.2)]);
    body.add(new THREE.Mesh(new THREE.TubeGeometry(hose, 24, 0.018, 8, false), dark));

    group.traverse(o => { if (o.isMesh) { o.castShadow = false; o.renderOrder = 1; } });

    // The free-fall rest pose (arms afloat, knees bent), each joint drifting on its own slow cycle.
    const w = (t, p, ph) => Math.sin(t * 2 * Math.PI / p + ph);
    function pose(t) {
      for (const s of [-1, 1]) {
        const L = s < 0 ? 'L' : 'R', ph = s < 0 ? 0 : 1.9, a = s < 0 ? 1 : -1;   // a: the two sides a little different
        J['shoulder' + L].rotation.set(0.3 + 0.08 * a + 0.1 * w(t, 5.3, ph), 0, s * (1.2 + 0.1 * a + 0.12 * w(t, 6.1, ph + 1)));
        J['elbow' + L].rotation.set(0.7 + 0.14 * w(t, 4.4, ph + 2), 0, 0);
        J['wrist' + L].rotation.set(0.15 * w(t, 3.7, ph), 0, s * 0.1);
        J['hip' + L].rotation.set(0.35 + 0.12 * a + 0.1 * w(t, 6.7, ph + 0.5), 0, s * (0.22 + 0.05 * w(t, 7.3, ph)));
        J['knee' + L].rotation.set(-0.65 - 0.15 * a + 0.14 * w(t, 5.9, ph + 2.6), 0, 0);
        J['ankle' + L].rotation.set(0.25 + 0.06 * w(t, 4.9, ph), 0, 0);
      }
      J.head.rotation.set(-0.12 + 0.05 * w(t, 8.1, 0.3), 0.06 * w(t, 9.7, 1), 0);
      J.body.rotation.set(0.12 + 0.03 * w(t, 7.7, 0), 0, 0.03 * w(t, 11.3, 2));
    }
    pose(0);
    return {
      group, joints: J, materials: mats, pose, rim,
      setTint(r, g, b) { for (const m of mats) m.color.copy(m.userData.base).multiply(new THREE.Color(r, g, b)); },
      setOpacity(x) { for (const m of mats) { m.opacity = x; m.depthWrite = x > 0.99; } },
    };
  };
})();
