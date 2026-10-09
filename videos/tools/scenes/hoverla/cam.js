// "What if over Hoverla instead of the Moon…": the author's photo of Hoverla from Mt Turkul (Carpathians) at dusk, with a
// world hung over the peak where the Moon would be -- at the Moon's distance, so at its true angular size. This scene
// draws only the worlds, on black; post.py lays them over the photo (added light, like the real Moon in a dusk sky),
// darkens the sky as the dusk deepens and brings out the stars. The camera matches the photo: ~53° vertical field
// (an iPhone's main camera), looking level; the peak is at the photo's column 629, row 920 of 1080×1920.
(() => {
  const smooth = window.__smooth, D = Math.PI / 180;
  const DIST = 1000;                       // scene units to the "Moon" (only angles matter)
  const MOON_KM = 384400;
  // id, diameter km, map, shown from–to (s), ring
  // id, diameter km, map (null: plain colour), ring — from the smallest to the largest; timing as in captions.py
  const WORLDS = [
    ['mars', 6779, 'mars_2k.jpg'], ['venus', 12104, 'venus_atmosphere_2k.jpg'], ['earth', 12742, 'earth_day_2k.jpg'],
    ['neptune', 49244, 'neptune.jpg'], ['saturn', 116460, 'saturn.jpg', true], ['jupiter', 139820, 'jupiter.jpg'],
  ];
  const START = 5.5, STEP = 5.0;
  const SUN_A = START + STEP * WORLDS.length, SUN_B = SUN_A + 7.5;
  // the photo's camera and the peak's direction in it
  const FOV = 53, ASPECT = 1080 / 1920, TH = Math.tan(FOV / 2 * D);
  const PEAK_AZ = Math.atan((629 / 540 - 1) * TH * ASPECT), PEAK_EL = Math.atan((1 - 920 / 960) * TH);
  const toDir = (az, el) => [Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)];
  const SHOW = [['moon', 3474, 'moon_2k.jpg', -2, START]];
  WORLDS.forEach(([id, km, file, ring], i) => SHOW.push([id, km, file, START + STEP * i, START + STEP * (i + 1), ring]));
  SHOW[SHOW.length - 1][4] = SUN_A + 0.8;                  // Jupiter stays while the Sun starts to grow
  SHOW.push(['moon', 3474, 'moon_2k.jpg', SUN_B, 999]);
  const FADE = 1.4;                        // long, overlapping dissolves between worlds
  let ready = false, items = [], group = null, sun = null;

  window.__sceneSetup = async (r) => {
    const T = r.THREE;
    group = new T.Group(); r.scene.add(group);
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
      // Centre over the peak, high enough that the disc (or Saturn's rings) clears it.
      const elev = PEAK_EL + (Math.max(2.4, (ring ? 2.27 * 0.5 : 1) * ang / D / 2 + 2.6)) * D;
      const [dx, dy, dz] = toDir(PEAK_AZ, elev);
      node.position.set(dx * DIST, dy * DIST, dz * DIST);
      node.visible = false;
      group.add(node);
      items.push({ id, a, b, node, mats, halo, base: mats.map(m => m.opacity), rad, elev });
    }
    // The Sun: 400 times the Moon. At the Moon's distance it would be bigger than the whole sky, so it grows until it
    // covers all of the sky above the hills. Plain map, a little dimmed: bright, but no glare.
    // Up close any map is hugely magnified, so the surface is drawn here: fine granulation over slow larger cells.
    const sm = new T.ShaderMaterial({
      uniforms: { opacity: { value: 0 }, time: { value: 0 } },
      // the pattern follows the direction on the sky, so the grain keeps its size however close the surface comes
      vertexShader: 'varying vec3 vP; void main(){ vP = (modelMatrix * vec4(position, 1.0)).xyz - cameraPosition; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `
        uniform float opacity, time; varying vec3 vP;
        float h(vec3 p){ return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
        float n(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(mix(h(i), h(i + vec3(1,0,0)), f.x), mix(h(i + vec3(0,1,0)), h(i + vec3(1,1,0)), f.x), f.y),
                     mix(mix(h(i + vec3(0,0,1)), h(i + vec3(1,0,1)), f.x), mix(h(i + vec3(0,1,1)), h(i + vec3(1,1,1)), f.x), f.y), f.z); }
        void main(){
          vec3 p = normalize(vP);
          float big = n(p * 9.0 + time * 0.02) * 0.6 + n(p * 19.0 - time * 0.03) * 0.4;
          float gr = n(p * 70.0 + time * 0.05) * 0.55 + n(p * 150.0 - time * 0.04) * 0.45;
          float v = clamp(0.25 + 0.45 * big + 0.45 * gr, 0.0, 1.0);
          vec3 c = mix(vec3(0.78, 0.30, 0.05), vec3(1.0, 0.78, 0.42), v);
          gl_FragColor = vec4(c * 0.92, opacity);
        }`,
      transparent: true, depthTest: false, depthWrite: false,
    });
    sun = new T.Mesh(new T.SphereGeometry(1, 128, 96), sm);
    sun.renderOrder = 1; sun.visible = false;
    group.add(sun);
    ready = true;
  };

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, T = r.THREE, t = window.__vt() - (window.__t0 || 0);
    // Only our sky: everything of the site but the stars stays hidden.
    for (const o of r.scene.children) if (o !== group && !o.isLight) o.visible = false;
        for (const it of items) {
      const k = Math.min(smooth((t - it.a + FADE / 2) / FADE), 1 - smooth((t - it.b + FADE / 2) / FADE));
      it.node.visible = k > 0.002;
      it.mats.forEach(m => { m.opacity = k; });
      if (it.halo) it.halo.material.opacity = 0.35 * k;
      // each world turns very slowly while it is up
      if (it.node.visible) it.node.rotation.y = 0.03 * (t - it.a);
      // the view tilts up a little for the big ones so they sit well in the frame

    }
    // The Sun grows from Jupiter's size to over the whole sky (angular radius 10° → 75°), then gives way to the night.
    const ks = Math.min(smooth((t - SUN_A + 0.8) / 1.6), 1 - smooth((t - SUN_B + 1.5) / 3.0));
    sun.visible = ks > 0.002;
    if (sun.visible) {
      const g = smooth((t - SUN_A + 0.6) / 6.0);
      const angR = (10 + 65 * g) * D, el = PEAK_EL + (12 + 10 * g) * D;
      const d = DIST, R = d * Math.sin(angR);
      sun.scale.setScalar(R);
      const [sx, sy, sz] = toDir(PEAK_AZ, el);
      sun.position.set(sx * d, sy * d, sz * d);
      sun.rotation.y = 0.01 * (t - SUN_A);
      sun.material.uniforms.opacity.value = ks; sun.material.uniforms.time.value = t;
    }
    // fixed, like the photo: level, straight ahead
    const cam = r.camera;
    cam.position.set(0, 0, 0); cam.up.set(0, 1, 0); cam.lookAt(0, 0, -10);
    if (cam.near !== 0.5 || cam.fov !== FOV) { cam.near = 0.5; cam.fov = FOV; cam.updateProjectionMatrix(); }
  };
})();
