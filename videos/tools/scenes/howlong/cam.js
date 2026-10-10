// "How long would it take": a close look at each goal in turn -- the Moon, Mars, the Sun (the site's own bodies) and
// Proxima Centauri, which the site doesn't have: a red dwarf drawn here in its own little scene (a sphere with a
// boiling, spotted surface, darker at the limb, a soft glow; Alpha Centauri A and B shining behind it). Proxima is
// self-contained in buildProxima() so it can move to the site later. Times are in seconds of the video.
(() => {
  const smooth = window.__smooth, ease = window.__ease, lerp = window.__lerp, D = Math.PI / 180;
  // Segments: Proxima (hook), Moon, Mars, Sun, Proxima. Cuts through black at the boundaries (captions.py CUTS).
  const SEG = [[0, 4, 'proxima'], [4, 13, 'moon'], [13, 22, 'mars'], [22, 31, 'sun'], [31, 47.5, 'proxima']];
  let ready = false, PX = null;

  function buildProxima(THREE) {
    const scene = new THREE.Scene();
    const mat = new THREE.ShaderMaterial({
      uniforms: { time: { value: 0 } },
      vertexShader: `varying vec3 vN; varying vec3 vP; varying vec3 vV;
        void main() { vP = position; vN = normalize(normalMatrix * normal);
          vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
      fragmentShader: `uniform float time; varying vec3 vN; varying vec3 vP; varying vec3 vV;
        float h(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
        float n(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                     mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
        void main() {
          vec3 p = normalize(vP);
          float big = n(p * 3.0 + time * 0.03) * 0.6 + n(p * 7.0 - time * 0.04) * 0.4;           // slow large cells
          float mid = n(p * 18.0 + time * 0.08);
          float gr = n(p * 55.0 + time * 0.15) * 0.5 + n(p * 120.0 - time * 0.12) * 0.5;         // fine boiling
          float sp = n(p * 2.2 + 7.0) * 0.7 + n(p * 6.0 + 3.0) * 0.3;
          float spots = smoothstep(0.64, 0.78, sp) * 0.5 + smoothstep(0.74, 0.82, sp) * 0.3;     // starspots, darker cores
          float v = clamp(0.42 + 0.28 * (big - 0.5) * 2.0 + 0.18 * (mid - 0.5) * 2.0 + 0.30 * (gr - 0.5) * 2.0 - spots, 0.0, 1.2);
          float mu = max(dot(vN, vV), 0.0);
          float limb = 0.25 + 0.75 * pow(mu, 0.55);                                               // darker and redder at the edge
          vec3 c = mix(vec3(0.42, 0.05, 0.02), vec3(1.0, 0.56, 0.26), v) * limb;
          c = mix(c * vec3(1.0, 0.75, 0.6), c, mu) * 1.2;
          gl_FragColor = vec4(c, 1.0);
        }`,
    });
    const star = new THREE.Mesh(new THREE.SphereGeometry(1, 128, 96), mat);
    scene.add(star);
    // a soft red glow around it (a camera-facing sprite drawn from a canvas gradient)
    const glow = (rgb, size, a) => {
      const cv = document.createElement('canvas'); cv.width = cv.height = 256;
      const g = cv.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
      gr.addColorStop(0, `rgba(${rgb},${a})`); gr.addColorStop(0.25, `rgba(${rgb},${a * 0.35})`); gr.addColorStop(1, `rgba(${rgb},0)`);
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
      sp.scale.setScalar(size); return sp;
    };
    const halo = glow('255,80,35', 4.2, 0.6); halo.renderOrder = -1; scene.add(halo);
    // Alpha Centauri A (yellow-white) and B (orange), far behind: two bright points close together
    const A = glow('255,245,220', 9, 1.0), B = glow('255,200,140', 6, 0.9);
    A.position.set(-60, 38, -400); B.position.set(-52, 34, -400); scene.add(A, B);
    // background stars
    const pos = [], col = [];
    for (let i = 0; i < 4000; i++) {
      const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = 900, s = Math.sqrt(1 - u * u);
      pos.push(r * s * Math.cos(th), r * u, r * s * Math.sin(th));
      const b = Math.pow(Math.random(), 3) * 0.9 + 0.1, w = Math.random();
      col.push(b * (0.8 + 0.2 * w), b * 0.9, b * (1.0 - 0.15 * w));
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 1.6, sizeAttenuation: false, vertexColors: true })));
    const cam = new THREE.PerspectiveCamera(45, 720 / 1280, 0.01, 2000);
    return { scene, cam, mat, star };
  }

  window.__sceneSetup = async (r) => {
    const s = r.state;
    s.index = r.BODIES.indexOf(r.byId.earth); s.mode = 'focus'; s.flight = null;
    for (const x of r.BODIES) if (x.orbitLine) x.orbitLine.visible = false;
    PX = buildProxima(r.THREE);
    ready = true;
  };

  function seg(t) { for (const sg of SEG) if (t < sg[1]) return sg; return SEG[SEG.length - 1]; }

  // A slow push-in on a body, seen three-quarters lit: the camera sits between the Sun direction and the side.
  function bodyShot(r, id, k) {
    const V = r.THREE.Vector3, b = r.byId[id], C = b.world.clone(), R = b.radius;
    let dir;
    if (id === 'sun') dir = new V(0.35, 0.25, 1).normalize();
    else if (id === 'moon') {
      // between the Sun and the Earth side: the Earth is behind the camera, out of the frame
      const sun = C.clone().negate().normalize(), out = C.clone().sub(r.byId.earth.world).normalize();
      dir = sun.multiplyScalar(0.95).sub(out.multiplyScalar(0.4)).add(new V(0, 0.15, 0)).normalize();
    }
    else {
      const sun = C.clone().negate().normalize(), up = new V(0, 1, 0), side = new V().crossVectors(up, sun).normalize();
      dir = sun.clone().multiplyScalar(0.75).addScaledVector(side, 0.65).addScaledVector(up, 0.18).normalize();
    }
    const dist = lerp(id === 'sun' ? 4.2 : 5.0, id === 'sun' ? 3.2 : 3.9, ease(k));
    const pos = C.clone().addScaledVector(dir, dist * R);
    return { pos, look: C, near: Math.max(0.001, (dist - 1) * R * 0.3) };
  }

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, t = window.__vt() - (window.__t0 || 0);
    const [a, b, id] = seg(t), k = Math.min(1, Math.max(0, (t - a) / (b - a)));
    PX.on = id === 'proxima'; PX.t = t;
    if (PX.on) {
      // the hook: already close; the second time: a slow approach from farther out
      const dist = a === 0 ? lerp(4.6, 4.2, k) : lerp(12, 3.8, ease(Math.min(1, (t - a) / 9)));
      const az = lerp(-25, 15, k) * D;
      PX.cam.position.set(Math.sin(az) * dist, 0.35 * dist * 0.3, Math.cos(az) * dist);
      PX.cam.lookAt(0, 0, 0);
      PX.star.rotation.y = t * 0.02; PX.mat.uniforms.time.value = t;
      return;
    }
    // only the goal in view: the site draws the planets enlarged, so the others would crowd the background
    const T = r.byId[id];
    for (const x of r.BODIES) {
      x.group.visible = x === T || x === T.parent;
      x.tiltGroup.visible = x === T;
    }
    const { pos, look, near } = bodyShot(r, id, k);
    const cam = r.camera;
    cam.position.copy(pos); cam.up.set(0, 1, 0); cam.lookAt(look); r.controls.target.copy(look);
    if (Math.abs(cam.near - near) > near * 0.02) { cam.near = near; cam.updateProjectionMatrix(); }
  };

  window.__recRender = () => {
    const r = window.__rec;
    if (ready && PX.on) r.renderer.render(PX.scene, PX.cam);
    else r.renderer.render(r.scene, r.camera);
  };
})();
