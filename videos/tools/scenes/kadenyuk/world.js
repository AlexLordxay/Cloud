// The Earth (the site's textures) and the Space Shuttle above it. Two scenes, one view direction: the Earth in km
// (camera at its orbital position), the shuttle in metres (camera at the origin). window.render() -> a JPEG data url.
(() => {
  const W = innerWidth, H = innerHeight, R = 6371, D2R = Math.PI / 180;
  const rd = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  rd.setSize(W, H); rd.outputEncoding = THREE.sRGBEncoding; rd.autoClear = false;
  document.body.appendChild(rd.domElement);

  // a point on the globe the way SphereGeometry lays out an equirectangular map
  const geo = (lat, lon, r = R) => {
    const u = (lon + 180) / 360, v = (90 - lat) / 180;
    return new THREE.Vector3(-r * Math.cos(u * 2 * Math.PI) * Math.sin(v * Math.PI), r * Math.cos(v * Math.PI),
      r * Math.sin(u * 2 * Math.PI) * Math.sin(v * Math.PI));
  };

  // the view (window.view sets it): camera lat/lon/alt (km), pitch below the local horizontal and heading of the
  // look from north (degrees), the Sun's azimuth/elevation at that point; up/north/east are the local frame there
  let pos = new THREE.Vector3(), up = new THREE.Vector3(), north = new THREE.Vector3(), east = new THREE.Vector3();
  const sun = new THREE.Vector3();
  const FOV = 52;
  const camE = new THREE.PerspectiveCamera(FOV, W / H, 1, 40000);
  const camS = new THREE.PerspectiveCamera(FOV, W / H, 0.5, 2000);
  const frame = (lat, lon) => {
    const p = geo(lat, lon), u = p.clone().normalize(), n = geo(lat + 0.01, lon).sub(p).normalize();
    return [u, n, new THREE.Vector3().crossVectors(n, u)];
  };
  const setView = V => {
    pos = geo(V.lat, V.lon, R + V.alt); [up, north, east] = frame(V.lat, V.lon);
    const pi = V.pitch * D2R, hd = (V.heading || 0) * D2R;
    const hz = north.clone().multiplyScalar(Math.cos(hd)).addScaledVector(east, Math.sin(hd));
    const look = hz.clone().multiplyScalar(Math.cos(pi)).addScaledVector(up, Math.sin(pi));
    camE.position.copy(pos); camE.up.copy(V.pitch < -60 ? hz : up); camE.lookAt(pos.clone().add(look));
    camS.quaternion.copy(camE.quaternion);
    // the Sun from where it stands at a ground point (sunAt: [lat, lon], default under the camera)
    const [su, sn, se] = V.sunAt ? frame(V.sunAt[0], V.sunAt[1]) : [up, north, east];
    const az = V.sunAz * D2R, el = V.sunEl * D2R;
    sun.copy(su).multiplyScalar(Math.sin(el)).addScaledVector(sn, Math.cos(el) * Math.cos(az)).addScaledVector(se, Math.cos(el) * Math.sin(az)).normalize();
  };

  // ---- the Earth
  const sE = new THREE.Scene(), tl = new THREE.TextureLoader();
  const tex = (f, srgb) => { const t = tl.load('/tex/' + f, () => tex.n--); tex.n++; if (srgb) t.encoding = THREE.sRGBEncoding;
    t.anisotropy = 8; return t; };
  tex.n = 0;
  const earthMat = new THREE.ShaderMaterial({
    uniforms: { day: { value: tex('earth_day.jpg') }, night: { value: tex('earth_night.jpg') },
      spec: { value: tex('earth_specular.jpg') }, clouds: { value: tex('earth_clouds.png') },
      detail: { value: (() => { const t = tl.load('/work/patch.jpg', () => tex.n--); tex.n++; t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t; })() },
      pbox: { value: new THREE.Vector4(0, 0, 67.5, 67.5) }, cloudAmt: { value: 1 },
      sun: { value: sun }, cam: { value: new THREE.Vector3() } },
    vertexShader: `varying vec2 vUv; varying vec3 vN, vP;
      void main(){ vUv = uv; vN = normalize(position); vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
    fragmentShader: `uniform sampler2D day, night, spec, clouds, detail; uniform vec4 pbox; uniform float cloudAmt; uniform vec3 sun, cam; varying vec2 vUv; varying vec3 vN, vP;
      vec3 lin(vec3 c){ return pow(c, vec3(2.2)); }
      void main(){
        vec3 n = normalize(vN), v = normalize(cam - vP);
        float mu = dot(n, sun), lit = smoothstep(-0.08, 0.12, mu);
        vec3 d = lin(texture2D(day, vUv).rgb);
        // the detailed patch (lon/lat box pbox) over the base map
        vec2 ll = vec2(vUv.x * 360. - 180., vUv.y * 180. - 90.), pu = (ll - pbox.xy) / (pbox.zw - pbox.xy);
        if (pu.x > 0. && pu.x < 1. && pu.y > 0. && pu.y < 1.) d = lin(texture2D(detail, pu).rgb);
        float cl = texture2D(clouds, vUv).r * cloudAmt;
        d = mix(d, vec3(0.92), cl * 0.85);
        vec3 col = d * max(mu, 0.) * 1.15;
        float s = texture2D(spec, vUv).r * (1. - cl);
        vec3 h = normalize(sun + v);
        col += vec3(1., 0.95, 0.85) * s * pow(max(dot(n, h), 0.), 90.) * 0.9 * lit;
        // thin blue haze, thicker at grazing angles
        float graze = 1. - max(dot(n, v), 0.);
        col = mix(col, vec3(0.32, 0.55, 1.) * max(mu + 0.1, 0.) * 0.8, clamp(0.05 + pow(graze, 4.) * 0.7, 0., 0.85));
        col += lin(texture2D(night, vUv).rgb) * (1. - lit) * 0.8 * (1. - cl);
        gl_FragColor = vec4(pow(col, vec3(1./2.2)), 1.);
      }` });
  sE.add(new THREE.Mesh(new THREE.SphereGeometry(R, 512, 256), earthMat));
  // the limb glow: a slightly larger sphere seen from inside-out, bright at the edge
  const atm = new THREE.ShaderMaterial({
    uniforms: { sun: { value: sun }, cam: { value: new THREE.Vector3() } }, side: THREE.BackSide, transparent: true, depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: `varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.); }`,
    fragmentShader: `uniform vec3 sun, cam; varying vec3 vP;
      void main(){
        vec3 n = normalize(vP), v = normalize(vP - cam);
        float edge = pow(1. - abs(dot(n, v)), 14.);
        float day = smoothstep(-0.25, 0.3, dot(n, sun));
        gl_FragColor = vec4(vec3(0.3, 0.55, 1.) * edge * day * 1.3, 1.);
      }` });
  sE.add(new THREE.Mesh(new THREE.SphereGeometry(R + 30, 256, 128), atm));

  // ---- the shuttle
  const sS = new THREE.Scene();
  const sunL = new THREE.DirectionalLight(0xfff6ea, 3.2); sS.add(sunL);
  sS.add(new THREE.HemisphereLight(0x0a0f18, 0x5d7fb0, 0.9));   // dark sky above, blue Earth-shine from below
  sS.add(new THREE.AmbientLight(0xffffff, 0.08));
  const ship = new THREE.Group(); sS.add(ship);
  const gl = new THREE.GLTFLoader(), draco = new THREE.DRACOLoader();
  draco.setDecoderPath('/draco/'); gl.setDRACOLoader(draco);
  const parts = ['D', 'door_prt', 'door_stb'];   // eng/rcs are loose duplicates of what D has
  let left = parts.length;
  const raw = new THREE.Group();
  parts.forEach(n => gl.load('/model/' + n + '.glb', g => { g.scene.name = n; raw.add(g.scene); left--; },
    undefined, e => { console.log('glb ' + n + ' ' + e); left--; }));

  const ready = () => {
    // centre and scale to 37 m along the longest axis; log the box so the nose axis can be checked
    const box = new THREE.Box3().setFromObject(raw), size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
    console.log('[shuttle] size ' + size.toArray().map(x => x.toFixed(2)) + ' centre ' + c.toArray().map(x => x.toFixed(2)));
    raw.children.forEach(ch => { const b = new THREE.Box3().setFromObject(ch); console.log('[part] ' + ch.name + ' ' +
      b.min.toArray().map(x => x.toFixed(1)) + ' .. ' + b.max.toArray().map(x => x.toFixed(1))); });
    const k = 37 / Math.max(size.x, size.y, size.z);
    raw.position.copy(c).multiplyScalar(-k); raw.scale.setScalar(k);
    ship.add(raw);
    // the payload bay doors open, as in orbit: each swings about its hinge on the bay's outer edge (model units)
    [['door_prt', 1], ['door_stb', -1]].forEach(([n, sd]) => {
      const d = raw.getObjectByName(n), pv = new THREE.Group();
      pv.position.set(0, 107 * sd, 18); raw.add(pv); pv.add(d); d.position.set(0, -107 * sd, -18);
      pv.rotation.x = -sd * window.DOOR * D2R;
    });
    raw.traverse(o => { if (o.material) { (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => {
      if (m.map && !m.map.image) { m.map = null; m.color && m.color.set(0xf2f2ee); }   // the doors' textures are not in the repo
      if (m.map) { m.map.encoding = THREE.sRGBEncoding; m.map.anisotropy = 8; } m.needsUpdate = true; }); } });
    window.WORLD_READY = true;
  };
  const wait = () => (left || tex.n) ? setTimeout(wait, 100) : ready();
  wait();

  window.DOOR = 150;   // degrees the bay doors are swung open
  // one picture: V = the view (above) plus V.ship = {dist, down, side, heading, roll} or nothing (no shuttle).
  // Returns the JPEG and where V.mark ([lat, lon]) lands on the screen, in pixels
  window.render = V => {
    setView(V);
    earthMat.uniforms.cam.value.copy(pos); earthMat.uniforms.cloudAmt.value = V.clouds == null ? 1 : V.clouds; atm.uniforms.cam.value.copy(pos); sunL.position.copy(sun);
    const S = V.ship;
    ship.visible = !!S;
    if (S) {
      const f = new THREE.Vector3(0, 0, -1).applyQuaternion(camS.quaternion),
        u = new THREE.Vector3(0, 1, 0).applyQuaternion(camS.quaternion), r = new THREE.Vector3(1, 0, 0).applyQuaternion(camS.quaternion);
      ship.position.copy(f).multiplyScalar(S.dist).addScaledVector(u, S.down).addScaledVector(r, S.side);
      // the model: +x nose, +y port wing, +z the top (bay); nose along the heading, bay up, rolled towards the camera
      const nose = north.clone().multiplyScalar(Math.cos(S.heading * D2R)).addScaledVector(east, Math.sin(S.heading * D2R));
      ship.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(nose, new THREE.Vector3().crossVectors(up, nose), up));
      ship.rotateX(-S.roll * D2R);
    }
    camE.updateMatrixWorld();
    rd.clear(); rd.render(sE, camE); rd.clearDepth(); if (S) rd.render(sS, camS);
    let mark = null;
    if (V.mark) { const m = geo(V.mark[0], V.mark[1]).project(camE); mark = [(m.x + 1) / 2 * W, (1 - m.y) / 2 * H]; }
    return { url: rd.domElement.toDataURL('image/jpeg', 0.93), mark };
  };
})();
