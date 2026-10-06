// "What if instead of the Moon…": a night landscape with a planet hung where the Moon is — at the Moon's distance
// (384 400 km), so each shows at its true angular size: Pluto 0.35°, Moon 0.52°, Mercury 0.73°, Ganymede 0.79°, Mars 1.0°,
// Venus 1.8°, Earth 1.9°, Neptune 7.3°, Uranus 7.6°, Saturn 17.3° (rings 40°), Jupiter 20.8°. The site's Solar System is hidden; the scene builds its own sky objects
// from the site's maps. Camera: 45° vertical field, looking a little above the horizon.
(() => {
  const smooth = window.__smooth, D = Math.PI / 180;
  const DIST = 1000;                       // scene units to the "Moon" (only angles matter)
  const MOON_KM = 384400;
  // id, diameter km, map, shown from–to (s), ring
  // id, diameter km, map (null: plain colour), ring — from the smallest to the largest; timing as in captions.py
  const WORLDS = [
    ['miranda', 472, 'miranda.jpg'], ['enceladus', 504, 'enceladus.jpg'], ['ceres', 940, 'ceres.jpg'],
    ['charon', 1212, 'charon.jpg'], ['makemake', 1430, 'makemake.jpg'], ['rhea', 1527, 'rhea.jpg'],
    ['titania', 1578, 'titania.jpg'], ['eris', 2326, 'eris.jpg'], ['pluto', 2377, 'pluto.jpg'],
    ['triton', 2707, 'triton.jpg'], ['europa', 3122, 'europa.jpg'], ['io', 3643, 'io.jpg'],
    ['callisto', 4821, 'callisto.jpg'], ['mercury', 4879, 'mercury_2k.jpg'], ['titan', 5150, null],
    ['ganymede', 5268, 'ganymede.jpg'], ['mars', 6779, 'mars_2k.jpg'], ['venus', 12104, 'venus_atmosphere_2k.jpg'],
    ['earth', 12742, 'earth_day_2k.jpg'], ['neptune', 49244, 'neptune.jpg'], ['uranus', 50724, 'uranus.jpg'],
    ['saturn', 116460, 'saturn.jpg', true], ['jupiter', 139820, 'jupiter.jpg'],
  ];
  const START = 7.4, STEP = 6.0;
  const SUN_A = START + STEP * WORLDS.length, SUN_B = SUN_A + 11.0;
  const SHOW = [['moon', 3474, 'moon_2k.jpg', 0, START]];
  WORLDS.forEach(([id, km, file, ring], i) => SHOW.push([id, km, file, START + STEP * i, START + STEP * (i + 1), ring]));
  SHOW[SHOW.length - 1][4] = SUN_A + 0.6;                  // Jupiter stays while the Sun starts to grow
  SHOW.push(['moon', 3474, 'moon_2k.jpg', SUN_B, 999]);
  const FADE = 1.8;                        // long, overlapping dissolves between worlds
  let ready = false, items = [], keep = null, group = null, sun = null, dome = null;

  function hills(T) {
    // A dark ring of low hills all round, 600 units away, with a few tree tops near the middle of the view.
    const pos = [], R = 600, n = 720;
    const h = az => 0.9 + 1.4 * Math.sin(az * 3) * 0.5 + 0.9 * Math.sin(az * 8 + 1) * 0.5 + 0.5 * Math.sin(az * 23 + 2) * 0.5;
    for (let i = 0; i < n; i++) {
      const a0 = i / n * Math.PI * 2, a1 = (i + 1) / n * Math.PI * 2;
      const y0 = R * Math.tan(h(a0) * D), y1 = R * Math.tan(h(a1) * D);
      const p = (a, y) => [Math.sin(a) * R, y, -Math.cos(a) * R];
      pos.push(...p(a0, -400), ...p(a1, -400), ...p(a0, y0), ...p(a1, -400), ...p(a1, y1), ...p(a0, y0));
    }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    const m = new T.Mesh(g, new T.MeshBasicMaterial({ color: new T.Color(0x020307).convertSRGBToLinear(), side: T.DoubleSide, toneMapped: false, fog: false }));
    m.renderOrder = 5;
    return m;
  }
  function glowDome(T) {
    // Faint blue glow along the horizon, fading upwards (added light: the stars still show through).
    return new T.Mesh(new T.SphereGeometry(1800, 64, 32), new T.ShaderMaterial({
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: 'varying vec3 vP; void main(){ if (vP.y < 0.0) discard; float g = exp(-vP.y * 9.0) * 0.16; gl_FragColor = vec4(vec3(0.16, 0.24, 0.42) * g, 1.0); }',
      side: T.BackSide, transparent: true, depthWrite: false, blending: T.AdditiveBlending,
    }));
  }

  window.__sceneSetup = async (r) => {
    const T = r.THREE;
    keep = r.scene.children.find(o => o.isPoints && o.material.vertexColors);   // the starfield
    group = new T.Group(); r.scene.add(group);
    dome = glowDome(T);
    const hl = hills(T);
    // the hills draw after the Sun (both in the transparent pass), so they stay a black silhouette in front of it
    hl.material.transparent = true; hl.renderOrder = 10;
    group.add(dome, hl);
    sunLight.visible = false;
    const light = new T.DirectionalLight(0xfff4e6, 2.3);
    light.position.set(-0.9, 0.35, 0.25);   // from the left and a little behind: a waxing, mostly lit disc
    group.add(light, light.target);
    const loader = new T.TextureLoader();
    const load = f => new Promise(res => loader.load('textures/' + f, t => { t.encoding = T.sRGBEncoding; t.anisotropy = 8; res(t); }));
    const ringTex = await load('saturn_ring.png');
    for (const [id, km, file, a, b, ring] of SHOW) {
      const map = file ? await load(file) : null;
      const ang = 2 * Math.atan(km / 2 / MOON_KM);            // true angular diameter at the Moon's distance
      const rad = DIST * Math.tan(ang / 2);
      const node = new T.Group();
      // Titan: its orange haze hides the surface, so a plain colour is truer than the surface map
      const mat = new T.MeshStandardMaterial({ map, color: map ? 0xffffff : 0xd8a457, roughness: 1, metalness: 0, transparent: true });
      const sph = new T.Mesh(new T.SphereGeometry(rad, 96, 64), mat);
      sph.rotation.y = -Math.PI / 2;                          // the map's middle towards the viewer
      node.add(sph);
      const mats = [mat];
      if (id === 'earth') {
        const ct = await load('earth_clouds.png'); ct.encoding = T.LinearEncoding;
        const cm = new T.MeshStandardMaterial({ color: 0xffffff, alphaMap: ct, roughness: 1, metalness: 0, transparent: true, depthWrite: false });
        const cl = new T.Mesh(new T.SphereGeometry(rad * 1.01, 96, 64), cm);
        cl.rotation.y = -Math.PI / 2 + 0.6; node.add(cl); mats.push(cm);
      }
      if (ring) {
        const rm = ringMesh(rad * 1.24, rad * 2.27, ringTex, 0xffffff);
        rm.material.transparent = true;
        node.add(rm); mats.push(rm.material);
        node.rotation.x = 0.42; node.rotation.z = -0.18;      // rings open towards us, tilted
      }
      // Small things get a soft halo so they read on a phone; it fades away as the disc grows.
      let halo = null;
      if (ang < 2.5 * D) { halo = glowSprite('230,236,255', Math.max(rad * 9, 20), 0.35); node.add(halo); }
      // Centre a few degrees above the hills, so the disc (or Saturn's rings) clears the horizon.
      const elev = (Math.max(3.2, (ring ? 2.27 * 0.55 : 1) * ang / D / 2 + 3.4)) * D;
      node.position.set(Math.sin(4 * D) * Math.cos(elev) * DIST, Math.sin(elev) * DIST, -Math.cos(4 * D) * Math.cos(elev) * DIST);
      node.visible = false;
      group.add(node);
      items.push({ id, a, b, node, mats, halo, base: mats.map(m => m.opacity), rad, elev });
    }
    // The Sun: 400 times the Moon. At the Moon's distance it would be bigger than the whole sky, so it grows until it
    // covers all of the sky above the hills. Plain map, a little dimmed: bright, but no glare.
    const sm = new T.MeshBasicMaterial({ map: await load('sun.jpg'), color: 0xe6e0d6, transparent: true, depthTest: false, depthWrite: false, toneMapped: false });
    sun = new T.Mesh(new T.SphereGeometry(1, 128, 96), sm);
    sun.renderOrder = 1; sun.visible = false;
    group.add(sun);
    ready = true;
  };

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, T = r.THREE, t = window.__vt() - (window.__t0 || 0);
    // Only our sky: everything of the site but the stars stays hidden.
    for (const o of r.scene.children) if (o !== keep && o !== group && !o.isLight) o.visible = false;
    let wSum = 0, elSum = 0;
    for (const it of items) {
      const k = Math.min(smooth((t - it.a + FADE / 2) / FADE), 1 - smooth((t - it.b + FADE / 2) / FADE));
      it.node.visible = k > 0.002;
      it.mats.forEach(m => { m.opacity = k; });
      if (it.halo) it.halo.material.opacity = 0.35 * k;
      // each world turns very slowly while it is up
      if (it.node.visible) it.node.rotation.y = 0.03 * (t - it.a);
      // the view tilts up a little for the big ones so they sit well in the frame
      wSum += k; elSum += k * (it.rad > 100 ? 12.5 : 9);
    }
    // The Sun grows from Jupiter's size to over the whole sky (angular radius 10° → 75°), then gives way to the night.
    const ks = Math.min(smooth((t - SUN_A + 0.8) / 1.6), 1 - smooth((t - SUN_B + 1.5) / 3.0));
    sun.visible = ks > 0.002;
    if (sun.visible) {
      const g = smooth((t - SUN_A + 0.6) / 6.0);
      const angR = (10 + 65 * g) * D, el = (14 + 16 * g) * D;
      const d = DIST, R = d * Math.sin(angR);
      sun.scale.setScalar(R);
      sun.position.set(Math.sin(4 * D) * Math.cos(el) * d, Math.sin(el) * d, -Math.cos(4 * D) * Math.cos(el) * d);
      sun.rotation.y = 0.01 * (t - SUN_A);
      sun.material.opacity = ks;
      wSum += ks; elSum += ks * (12.5 + 5 * g);
    }
    dome.visible = ks < 0.98;
    const lookEl = (wSum > 0 ? elSum / wSum : 9) * D;
    const cam = r.camera;
    cam.position.set(0, 0, 0); cam.up.set(0, 1, 0);
    cam.lookAt(Math.sin(4 * D) * Math.cos(lookEl) * 10, Math.sin(lookEl) * 10, -Math.cos(4 * D) * Math.cos(lookEl) * 10);
    if (cam.near !== 0.5) { cam.near = 0.5; cam.updateProjectionMatrix(); }
  };
})();
