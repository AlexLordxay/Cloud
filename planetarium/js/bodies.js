// Небозвід — comets and building each body (meshes, rings, orbits).
// Plain scripts sharing one scope; index.html loads them in order.
"use strict";

/* ---------- Comet: coma and two tails ---------- */
function createCometFx(b) {
  const comaOuter = glowSprite("170,215,255", 1, 0.8), comaInner = glowSprite("255,248,230", 1, 0.9);
  b.group.add(comaOuter, comaInner);
  const pointScale = { value: 1 };
  // tail: length (and particle budget) relative to Halley; dust: how strong the dust tail is.
  const T = b.tail || 1, D = b.dust || 1;
  const makeTail = (n, color) => {
    const pos = new Float32Array(n * 3), alpha = new Float32Array(n), size = new Float32Array(n);
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("alpha", new THREE.BufferAttribute(alpha, 1));
    g.setAttribute("size", new THREE.BufferAttribute(size, 1));
    const m = new THREE.ShaderMaterial({
      uniforms: { color: { value: new THREE.Color(color) }, scale: pointScale },
      vertexShader: "attribute float alpha; attribute float size; uniform float scale; varying float vA; void main(){ vA = alpha; vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_PointSize = min(size * scale / -mv.z, 64.0); gl_Position = projectionMatrix * mv; }",
      fragmentShader: "uniform vec3 color; varying float vA; void main(){ vec2 c = gl_PointCoord - 0.5; float d = dot(c, c) * 4.0; if (d > 1.0) discard; float f = 1.0 - d; gl_FragColor = vec4(color, vA * f * f); }",
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    const pts = new THREE.Points(g, m);
    pts.frustumCulled = false;
    scene.add(pts);
    return { n, pos, alpha, size, g, vel: new Float32Array(n * 3), age: new Float32Array(n).fill(99), life: new Float32Array(n).fill(1), head: 0, acc: 0, alive: 0, idle: false, fresh: false, pts };
  };
  const ion = makeTail(Math.round(1500 * T), 0x6fa8ff), dust = makeTail(Math.round(1900 * T * D), 0xffe2a8);
  const v = new THREE.Vector3(), side = new THREE.Vector3(), up = new THREE.Vector3();

  function emit(t, count, fn) {
    t.acc += count;
    while (t.acc >= 1) {
      t.acc -= 1;
      const i = t.head; t.head = (t.head + 1) % t.n;
      t.fresh = true;
      fn(i);
    }
  }
  function step(t, dt, baseA, grow, s0) {
    // A tail with no live particles and nothing new: nothing to move or upload (most of the time, far from the Sun).
    if (!t.alive && !t.fresh && t.idle) return;
    t.fresh = false; t.pts.visible = true;
    let alive = 0;
    for (let i = 0; i < t.n; i++) {
      if (t.age[i] >= t.life[i]) { t.alpha[i] = 0; continue; }
      t.age[i] += dt;
      const k = i * 3;
      t.pos[k] += t.vel[k] * dt; t.pos[k + 1] += t.vel[k + 1] * dt; t.pos[k + 2] += t.vel[k + 2] * dt;
      const x = t.age[i] / t.life[i];
      t.alpha[i] = baseA * Math.pow(Math.max(0, 1 - x), 1.5) * Math.min(1, t.age[i] * 10);
      t.size[i] = s0 * (1 + x * grow);
      alive++;
    }
    t.idle = !alive && !t.alive;   // one last pass uploads the cleared alphas, then it rests (and is not drawn)
    if (t.idle) t.pts.visible = false;
    t.alive = alive;
    t.g.attributes.position.needsUpdate = true;
    t.g.attributes.alpha.needsUpdate = true;
    t.g.attributes.size.needsUpdate = true;
  }

  return {
    // act: 0..1 activity (grows near the Sun); anti: unit vector away from the Sun; motion: unit direction of travel.
    update(dt, act, anti, motion) {
      pointScale.value = innerHeight * renderer.getPixelRatio() / (2 * Math.tan(camera.fov * DEG / 2));
      comaOuter.scale.setScalar((0.4 + act * 5) * Math.sqrt(T));
      comaOuter.material.opacity = 0.06 + act * 0.55;
      comaInner.scale.setScalar((0.3 + act * 1.4) * Math.sqrt(T));
      comaInner.material.opacity = 0.2 + act * 0.7;
      side.crossVectors(anti, motion).normalize();
      up.crossVectors(side, anti).normalize();
      const p = b.world;
      // Ion tail: fast, straight, always pointing away from the Sun.
      const amount = eco ? 0.5 : 1;
      emit(ion, dt * 800 * T * act * amount, i => {
        const k = i * 3, sp = (14 + Math.random() * 8) * T, j = 0.35 * T;
        ion.pos[k] = p.x + (Math.random() - 0.5) * 0.15; ion.pos[k + 1] = p.y + (Math.random() - 0.5) * 0.15; ion.pos[k + 2] = p.z + (Math.random() - 0.5) * 0.15;
        v.copy(anti).multiplyScalar(sp).addScaledVector(side, (Math.random() - 0.5) * j).addScaledVector(up, (Math.random() - 0.5) * j);
        ion.vel[k] = v.x; ion.vel[k + 1] = v.y; ion.vel[k + 2] = v.z;
        ion.age[i] = 0; ion.life[i] = 1.2 + Math.random() * 0.7;
      });
      // Dust tail: slower, broader, lagging behind the orbit so it curves.
      emit(dust, dt * 420 * T * D * act * amount, i => {
        const k = i * 3, sp = 2.5 + Math.random() * 4;
        dust.pos[k] = p.x; dust.pos[k + 1] = p.y; dust.pos[k + 2] = p.z;
        v.copy(anti).multiplyScalar(sp).addScaledVector(motion, -1.2 - Math.random() * 2.2)
          .addScaledVector(side, (Math.random() - 0.5) * 1.1).addScaledVector(up, (Math.random() - 0.5) * 0.5).multiplyScalar(T);
        dust.vel[k] = v.x; dust.vel[k + 1] = v.y; dust.vel[k + 2] = v.z;
        dust.age[i] = 0; dust.life[i] = 3 + Math.random() * 1.8;
      });
      step(ion, dt, 0.16, 1.2, 0.28);
      step(dust, dt, 0.11, 2.5, 0.4);
    },
  };
}
const cometFxs = [];

const pickables = [];
let earthClouds = null, sunFx = null;

// Eccentric anomalies for drawing an orbit. Comets are seen up close, so they get many points: even steps in E
// (smooth far out) merged with even steps in true anomaly (smooth through the sharp turn at perihelion).
function orbitSamples(el, comet) {
  const N = comet ? Math.max(8000, Math.round(el.a * 60)) : 720, out = [];
  for (let k = 0; k <= N; k++) out.push(k / N * TAU);
  if (comet) {
    const q = Math.sqrt((1 - el.e) / (1 + el.e));
    for (let k = 1; k < 4000; k++) {
      const nu = -PI + k / 4000 * TAU, E = 2 * Math.atan(q * Math.tan(nu / 2));
      out.push(E < 0 ? E + TAU : E);
    }
    out.sort((x, y) => x - y);
  }
  return out;
}
// Position on an orbit: eccentric ellipse with the focus at the parent, in the plane's local XZ.
function orbitPoint(b, theta, out) {
  const e = b.e || 0, r = b.a * (1 - e * e) / (1 + e * Math.cos(theta));
  return out.set(Math.cos(theta) * r, 0, -Math.sin(theta) * r);
}

function buildBody(b, i, tex, jd) {
  b.index = i;
  b.world = new THREE.Vector3();
  b.dq = new THREE.Quaternion();
  b.au = 0; b.auVec = new THREE.Vector3();
  b.rot = ROT[b.id] || 0;
  b.phase = Math.random() * TAU;
  b.theta = b.phase;

  // Moons live in their planet's equatorial plane; everything else sits in the scene at its real heliocentric direction.
  b.plane = new THREE.Group();
  if (b.parent) {
    b.plane.rotation.z = (b.planeTilt != null ? b.planeTilt : b.parent.tilt || 0) * DEG;
    b.parent.group.add(b.plane);
  } else {
    scene.add(b.plane);
  }
  b.group = new THREE.Group();
  b.plane.add(b.group);
  b.tiltGroup = new THREE.Group();
  // Earth's axis points the real way (tilted towards ecliptic longitude 90°), so seasons match the date.
  if (b.id === "earth") b.tiltGroup.rotation.x = -b.tilt * DEG;
  else b.tiltGroup.rotation.z = (b.tilt || 0) * DEG;
  b.group.add(b.tiltGroup);

  const geo = new THREE.SphereGeometry(b.radius, b.radius > 1 ? 96 : 64, b.radius > 1 ? 64 : 48);
  let mat;
  if (b.id === "sun") {
    mat = new THREE.MeshBasicMaterial({ map: tex.sun });
    b.group.add(glowSprite("255,150,70", b.radius * 11, 0.22));
  } else if (b.id === "earth") {
    mat = earthMaterial(tex);
  } else {
    const map = tex[b.tex || b.id] || null;
    mat = new THREE.MeshStandardMaterial({ map, color: b.comet ? 0x6a655e : map ? 0xffffff : new THREE.Color(b.dot), roughness: 1, metalness: 0, bumpMap: b.bump ? map : null, bumpScale: b.bump || 0 });
  }
  b.mesh = new THREE.Mesh(geo, mat);
  if (b.shape) b.mesh.scale.set(b.shape[0], b.shape[1], b.shape[2]);
  b.mesh.userData.index = i;
  b.tiltGroup.add(b.mesh);
  if (b.id === "sun") {
    sunFx = createSunFx(b, tex);
    b.mesh.material = sunFx.material;
  }
  if (b.comet) cometFxs.push({ b, fx: createCometFx(b) });
  if (b.lobe) {
    // The smaller "head" of a two-lobed nucleus (67P's rubber-duck shape).
    const head = new THREE.Mesh(new THREE.SphereGeometry(b.radius * 0.7, 48, 32), b.mesh.material);
    head.position.set(b.radius * 1.2, b.radius * 0.2, 0);
    head.scale.set(1, 0.85, 0.9);
    b.mesh.add(head);
  }
  if (b.id === "moon") b.mesh.material = moonMaterial(tex);
  if (b.id === "io") ioFx = createIoFx(b);
  if (b.id === "venus") b.mesh.material = venusMaterial(tex);
  if (b.id === "titan") { b.mesh.material = titanMaterial(); b.tiltGroup.add(titanAtmosphere(b.radius)); }
  if (b.id === "mercury") b.mesh.material = mercuryMaterial(tex);
  if (["jupiter", "saturn", "neptune", "uranus"].includes(b.id)) b.mesh.material = giantMaterial(b, tex);
  pickables.push(b.mesh);

  if (b.id === "earth") b.tiltGroup.add(earthAtmosphere(b.radius * 1.045), earthAurora(b.radius * 1.025));
  else if (b.id === "venus") b.tiltGroup.add(venusAtmosphere(b.radius * 1.04));
  else if (b.id === "neptune") b.tiltGroup.add(hazeAtmosphere(b.radius * 1.04, [0.32, 0.55, 1.0], [0.3, 0.75, 0.9], 1.1));
  else if (b.id === "uranus") b.tiltGroup.add(hazeAtmosphere(b.radius * 1.04, [0.55, 0.88, 0.95], [0.45, 0.8, 0.85], 0.9));
  else if (b.id === "mars") {
    const weather = marsWeather(b.radius * 1.006);
    if (eco) weather.material.defines.ECO = 1;
    ecoMaterials.push(weather.material);
    b.tiltGroup.add(marsAtmosphere(b.radius * 1.03));
    b.mesh.add(weather);
  }
  else if (b.atmo) b.tiltGroup.add(atmosphere(b.radius * 1.045, b.atmo, b.id === "venus" ? 2.2 : 3.0, b.id === "venus" ? 0.9 : b.id === "titan" ? 1.4 : 1.2));
  if (b.id === "earth") {
    tex.earthClouds.wrapS = THREE.RepeatWrapping;
    tex.earthClouds.needsUpdate = true;
    // The cloud deck turns with the planet; its own drift happens in the shader.
    earthClouds = new THREE.Mesh(new THREE.SphereGeometry(b.radius * 1.012, 96, 64), earthCloudMaterial(tex));
    b.mesh.add(earthClouds);
  }
  if (b.rings === "saturn") {
    const rings = ringMesh(b.radius * 1.24, b.radius * 2.27, tex.saturnRing, 0xffffff);
    rings.material = saturnRingMaterial(tex);
    b.tiltGroup.add(rings);
  }
  if (b.rings === "uranus") b.tiltGroup.add(ringMesh(b.radius * 1.6, b.radius * 2.05, toTexture(ringTexture(uranusRing)), 0xffffff));
  if (b.ring) b.tiltGroup.add(ringMesh(b.radius * b.ring[0], b.radius * b.ring[1], toTexture(ringTexture(thinRing)), 0xffffff));

  const pts = [], v = new THREE.Vector3();
  if (b.parent) {
    for (let k = 0; k <= 360; k++) pts.push(orbitPoint(b, k / 360 * TAU, v).clone());
    b.baseOpacity = 0.14;
  } else if (b.id !== "sun") {
    const el = elementsAt(b.id, jd);
    for (const E of orbitSamples(el, b.comet)) pts.push(toScene(posFromE(el, E, v), new THREE.Vector3()));
    b.baseOpacity = b.comet ? 0.18 : b.dwarf ? 0.11 : 0.16;
  }
  if (pts.length) {
    b.orbitLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: b.comet ? 0x9fd0ff : b.dwarf ? 0xb7a6d8 : 0x9fb2d8, transparent: true, opacity: b.baseOpacity }));
    b.plane.add(b.orbitLine);
  }
}
function applyLateTexture(key, t) {
  for (const b of BODIES) {
    if ((b.tex || b.id) !== key || !b.mesh || b.id === "earth" || b.id === "sun") continue;
    const m = b.mesh.material;
    m.map = t; m.color.set(0xffffff);
    if (b.bump) m.bumpMap = t;
    m.needsUpdate = true;
  }
}
