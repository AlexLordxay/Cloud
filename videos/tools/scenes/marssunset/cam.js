// "Sunset on Mars is blue": one continuous time-lapse from Gale crater, looking west. The Sun (2/3 of its size seen
// from the Earth) sinks into the crater rim; the fine dust that makes the day sky butterscotch scatters blue light
// forward, so a blue glow sits round the Sun and lingers over the horizon long after it sets; the stars come out and
// the Earth shines as the evening star, the Moon a faint dot beside it. Times are in seconds of the video and must
// match captions.py.
(() => {
  const smooth = window.__smooth, lerp = window.__lerp, D = Math.PI / 180;
  const DIST = 1000, SUN_AZ = 0, EARTH = [7.5, 15.5], MOON_OFF = [0.32, -0.12];
  let ready = false, keep = null, root = null, U = null, sunCore, sunHalo, earth, moon, marker;

  // The Sun's elevation (degrees): slow while it sets (gone behind the rim at ~17.5 s), then faster through twilight.
  const sunEl = t => t < 20 ? 5 - 0.24 * t : 0.2 - 0.48 * (t - 20);
  const skyPos = (T, az, el, d = DIST) => new T.Vector3(Math.sin(az * D) * Math.cos(el * D) * d, Math.sin(el * D) * d, -Math.cos(az * D) * Math.cos(el * D) * d);

  // The sky colour in a direction, shared by the sky, the haze on the far ridges and the ground (display values).
  const SKY = `
    uniform vec3 b; uniform float el;
    vec3 skyCol(vec3 v, float sharp) {
      float h = max(v.y, 0.0), mu = dot(v, b);
      // day: butterscotch, browner and darker towards the zenith; dims as the Sun goes down
      vec3 base = mix(vec3(0.78, 0.54, 0.34), vec3(0.38, 0.25, 0.16), pow(h, 0.6));
      float baseK = 0.04 + 0.6 * smoothstep(-6.0, 6.0, el);
      // low Sun: a warm-grey band on the horizon, brightest under the Sun
      float band = exp(-h * 10.0) * (0.35 + 0.65 * pow(max(mu, 0.0), 3.0));
      vec3 c = base * baseK + vec3(0.55, 0.45, 0.40) * band * 0.22 * smoothstep(-9.0, 2.0, el);
      // the blue aureole: dust scatters blue forwards; wide and soft, then tighter and whiter at the Sun
      float m = max(mu, 0.0);
      float A = smoothstep(-15.0, -0.5, el) * (1.0 - 0.45 * smoothstep(3.0, 15.0, el));
      float low = 1.0 + 0.8 * exp(-h * 6.0) * (1.0 - smoothstep(-1.0, 3.0, el));   // after sunset it hugs the horizon
      c += (vec3(0.28, 0.45, 0.85) * pow(m, 8.0) * 0.03 + vec3(0.24, 0.50, 1.0) * pow(m, 30.0) * 0.5
          + vec3(0.65, 0.82, 1.0) * pow(m, 200.0) * 0.4 * sharp + vec3(0.95, 0.98, 1.0) * pow(m, 40000.0) * 1.2 * sharp) * A * low;
      return c;
    }`;
  const HASH = 'float hs(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }';

  function skyDome(T) {
    return new T.Mesh(new T.SphereGeometry(1800, 96, 48), new T.ShaderMaterial({
      uniforms: U,
      vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: SKY + HASH + `varying vec3 vP;
        void main(){ vec3 c = skyCol(normalize(vP), 1.0) + (hs(gl_FragCoord.xy) - 0.5) / 255.0;
          // alpha hides the stars behind a bright sky: out = sky + stars * (1 - a)
          float a = clamp(dot(c, vec3(0.3, 0.5, 0.2)) * 9.0, 0.0, 1.0);
          gl_FragColor = vec4(max(c, 0.0), a); }`,
      side: T.BackSide, transparent: true, depthWrite: false,
      blending: T.CustomBlending, blendSrc: T.OneFactor, blendDst: T.OneMinusSrcAlphaFactor,
    }));
  }

  // Solid ground: rocky sand (or a rock), dark against the light, lit a little by the sky, and fading into the
  // horizon haze with distance. `tex` adds fine grain and pebbles (the ground plane).
  function solid(T, rgb, hazeL, tex) {
    return new T.ShaderMaterial({
      uniforms: Object.assign({ col: { value: new T.Vector3(...rgb) }, L: { value: hazeL } }, U),
      vertexShader: 'varying vec3 vW; void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: SKY + HASH + `uniform vec3 col; uniform float L; varying vec3 vW;
        float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
          return mix(mix(hs(i), hs(i + vec2(1,0)), f.x), mix(hs(i + vec2(0,1)), hs(i + vec2(1,1)), f.x), f.y); }
        void main(){
          vec3 d = vW - cameraPosition; float dist = length(d); vec3 v = d / dist;
          float g = 1.0;
          ${tex ? 'g = 0.7 + 0.35 * n(vW.xz * 0.35) + 0.25 * n(vW.xz * 2.1) - 0.35 * smoothstep(0.72, 0.8, n(vW.xz * 0.9 + 3.0));' : ''}
          float light = 0.25 + 0.75 * smoothstep(-6.0, 10.0, el);
          vec3 c = col * g * light;
          vec3 hv = normalize(vec3(v.x, max(v.y, 0.0) * 0.2 + 0.01, v.z));
          float k = 1.0 - exp(-dist / L);
          gl_FragColor = vec4(mix(c, skyCol(hv, 0.0) * 0.9, k), 1.0);
        }`,
      transparent: true, depthWrite: true,
    });
  }

  // A ring of ground silhouettes: h(az) degrees above the horizon, R units away (as in the "what if" scene).
  function ridge(T, h, R, mat, n = 1200) {
    const pos = [];
    for (let i = 0; i < n; i++) {
      const a0 = (-180 + 360 * i / n) * D, a1 = (-180 + 360 * (i + 1) / n) * D;
      const y0 = R * Math.tan(h(a0 / D) * D), y1 = R * Math.tan(h(a1 / D) * D);
      const p = (a, y) => [Math.sin(a) * R, y, -Math.cos(a) * R];
      pos.push(...p(a0, -R * 0.2), ...p(a1, -R * 0.2), ...p(a0, y0), ...p(a1, -R * 0.2), ...p(a1, y1), ...p(a0, y0));
    }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    return new T.Mesh(g, mat);
  }

  // A thin circle that points at the Earth for a moment.
  function ring(T, size) {
    const cv = document.createElement('canvas'); cv.width = cv.height = 256;
    const g = cv.getContext('2d'); g.strokeStyle = 'rgba(255,255,255,1)'; g.lineWidth = 5;
    g.beginPath(); g.arc(128, 128, 112, 0, Math.PI * 2); g.stroke();
    const s = new T.Sprite(new T.SpriteMaterial({ map: new T.CanvasTexture(cv), transparent: true, opacity: 0, depthWrite: false }));
    s.scale.set(size, size, 1); return s;
  }

  window.__sceneSetup = async (r) => {
    const T = r.THREE;
    keep = r.scene.children.find(o => o.isPoints && o.material.vertexColors);   // the starfield
    root = new T.Group(); r.scene.add(root);
    sunLight.visible = false;
    U = { b: { value: new T.Vector3(0, 0, -1) }, el: { value: 5 } };

    const dome = skyDome(T); dome.renderOrder = 5;
    // the Sun: true angular size 0.35° (a small white disc) with a soft bluish-white bloom
    sunCore = glowSprite('255,255,252', 2 * DIST * Math.tan(0.175 * D) * 2.6, 1.0);
    sunHalo = glowSprite('215,230,255', 26, 0.3);
    for (const s of [sunCore, sunHalo]) s.renderOrder = 6;
    // the Earth (the evening star) and the Moon beside it
    earth = glowSprite('205,225,255', 9, 0); moon = glowSprite('235,232,225', 3.2, 0);
    marker = ring(T, 34);
    for (const s of [earth, moon, marker]) s.renderOrder = 7;
    earth.position.copy(skyPos(T, EARTH[0], EARTH[1]));
    moon.position.copy(skyPos(T, EARTH[0] + MOON_OFF[0], EARTH[1] + MOON_OFF[1]));
    marker.position.copy(earth.position);

    // Gale crater: its far rim low on the horizon (hazy), nearer hills, and rocky ground with scattered stones
    const far = ridge(T, az => 2.4 + 0.7 * Math.sin(az * 0.05 + 0.4) + 0.35 * Math.sin(az * 0.17 + 2) + 0.12 * Math.sin(az * 0.9) + 0.04 * Math.sin(az * 3.1), 1500, solid(T, [0.15, 0.10, 0.07], 2600));
    const mid = ridge(T, az => {
      const mesa = Math.max(0, 1 - Math.abs(az - 38) / 22);      // a flat-topped butte to the right
      return 0.35 + 0.45 * Math.max(0, Math.sin(az * 0.08 - 1.2)) + 0.25 * Math.sin(az * 0.23 + 1) + 0.06 * Math.sin(az * 1.7) + 1.6 * smooth(mesa * 4);
    }, 600, solid(T, [0.075, 0.05, 0.04], 1300));
    const ground = new T.Mesh(new T.CircleGeometry(590, 96), solid(T, [0.16, 0.095, 0.065], 1300, true));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -2;
    const rocks = new T.Group(), rockMat = solid(T, [0.085, 0.055, 0.042], 1300);
    let seed = 7;
    const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (let i = 0; i < 110; i++) {
      const az = -60 + rnd() * 120, d = 9 + Math.pow(rnd(), 1.6) * 150, s = (0.12 + Math.pow(rnd(), 3) * 0.7) * (1 + d / 35);
      const geo = new T.IcosahedronGeometry(1, 1), gp = geo.attributes.position;
      for (let j = 0; j < gp.count; j++) { const k = 0.75 + 0.5 * Math.abs(Math.sin(gp.getX(j) * 3.1 + gp.getY(j) * 5.3 + gp.getZ(j) * 2.7 + i)); gp.setXYZ(j, gp.getX(j) * k, gp.getY(j) * k, gp.getZ(j) * k); }
      geo.computeVertexNormals();
      const m = new T.Mesh(geo, rockMat);
      m.scale.set(s * (0.8 + rnd() * 0.8), s * (0.35 + rnd() * 0.4), s * (0.8 + rnd() * 0.6));
      m.rotation.set(rnd() * 3, rnd() * 3, rnd() * 3);
      m.position.set(Math.sin(az * D) * d, -2 + m.scale.y * 0.3, -Math.cos(az * D) * d);
      rocks.add(m);
    }
    for (const [o, k] of [[far, 10], [mid, 11], [ground, 12], [rocks, 13]]) { o.renderOrder = k; if (o.children) o.children.forEach(c => { c.renderOrder = k; }); }
    root.add(dome, sunCore, sunHalo, earth, moon, marker, far, mid, ground, rocks);
    ready = true;
  };

  window.__recCam = () => {
    if (!ready) return;
    const r = window.__rec, T = r.THREE, cam = r.camera, t = window.__vt() - (window.__t0 || 0);
    for (const o of r.scene.children) if (o !== keep && o !== root) o.visible = false;
    const el = sunEl(t), az = SUN_AZ - 0.08 * (5 - el);       // the Sun slides a little to the left as it sets
    const sp = skyPos(T, az, el);
    U.el.value = el; U.b.value.copy(sp).normalize();
    sunCore.position.copy(sp); sunHalo.position.copy(sp);
    // the Earth and the Moon come out as the sky darkens; the circle points at the Earth while it is named
    const dark = smooth((-el - 3.2) / 2.6);
    earth.material.opacity = 0.95 * dark; moon.material.opacity = 0.45 * dark;
    marker.material.opacity = 0.55 * Math.min(smooth((t - 28.6) / 0.8), 1 - smooth((t - 32.6) / 0.8));
    // camera: close on the Sun at first, then wider, then lifting to bring the Earth into the frame
    const fov = lerp(30, 48, smooth((t - 3) / 20));
    const lookEl = lerp(4.6, 9.5, smooth((t - 19) / 9)), lookAz = lerp(0, 2.5, smooth((t - 19) / 10));
    if (Math.abs(cam.fov - fov) > 1e-4 || cam.near !== 0.3) { cam.fov = fov; cam.near = 0.3; cam.updateProjectionMatrix(); }
    cam.position.set(0, 0, 0); cam.up.set(0, 1, 0);
    cam.lookAt(skyPos(T, lookAz, lookEl, 10));
  };
})();
